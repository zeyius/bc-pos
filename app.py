from flask import Flask, render_template, request, redirect, Response, session, url_for, jsonify
import hashlib
import sqlite3
from datetime import datetime
import uuid
import csv
import io

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "pos.db"


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(stored_hash, password):
    return stored_hash == hash_password(password)


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_or_create_business_day(conn, user_id=None):
    today = datetime.now().date().isoformat()

    current = conn.execute("""
        SELECT id
        FROM business_days
        WHERE date = ? AND status = 'open'
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    if current:
        return current["id"]

    conn.execute("""
        INSERT INTO business_days (date, opened_at, opened_by, status)
        VALUES (?, ?, ?, 'open')
    """, (today, datetime.now().isoformat(), user_id))
    conn.commit()

    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
@login_required
def dashboard():
    today = datetime.now().date().isoformat()
    conn = get_db()

    # --- Current OPEN business day (session) ---
    current_day = conn.execute("""
        SELECT id
        FROM business_days
        WHERE date = ? AND status = 'open'
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    current_day_id = current_day["id"] if current_day else None

    # --- Determine day status from business_days only ---
    latest_day = conn.execute("""
        SELECT status, closed_at
        FROM business_days
        WHERE date = ?
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    is_closed = bool(latest_day and latest_day["status"] == "closed" and not current_day_id)

    closed_time = None
    if latest_day and latest_day["status"] == "closed" and latest_day["closed_at"]:
        closed_time = str(latest_day["closed_at"])[11:16]  # HH:MM

    # --- Dashboard totals (CURRENT business day only) ---
    if is_closed or not current_day_id:
        total_today = 0
        count_today = 0
        my_total = 0
        my_count = 0
        recent_sales = []
    else:
        sales_today = conn.execute("""
            SELECT total
            FROM sales
            WHERE business_day_id = ?
              AND is_void = 0
        """, (current_day_id,)).fetchall()

        total_today = sum(s["total"] for s in sales_today)
        count_today = len(sales_today)

        my_sales = conn.execute("""
            SELECT total
            FROM sales
            WHERE business_day_id = ?
              AND is_void = 0
              AND user_id = ?
        """, (current_day_id, session.get("user_id"))).fetchall()

        my_total = sum(s["total"] for s in my_sales)
        my_count = len(my_sales)

        recent_sales = conn.execute("""
            SELECT
                s.id,
                s.receipt_no,
                s.created_at,
                strftime('%H:%M', s.created_at) AS time_str,
                s.total,
                COALESCE(SUM(si.qty), 0) AS items_count
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.id
            WHERE s.is_void = 0
              AND s.business_day_id = ?
            GROUP BY s.id
            ORDER BY datetime(s.created_at) DESC
            LIMIT 4
        """, (current_day_id,)).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_today=total_today,
        count_today=count_today,
        my_total=my_total,
        my_count=my_count,
        recent_sales=recent_sales,
        is_closed=is_closed,
        closed_time=closed_time,
        username=session.get("username")
    )


@app.route("/sale/<int:sale_id>")
@login_required
def sale_detail(sale_id):
    conn = get_db()

    sale = conn.execute("""
        SELECT *
        FROM sales
        WHERE id = ?
    """, (sale_id,)).fetchone()

    if sale is None:
        conn.close()
        return redirect(url_for("dashboard"))

    items = conn.execute("""
        SELECT si.product_name AS name, si.qty, si.line_total
        FROM sale_items si
        WHERE si.sale_id = ?
    """, (sale_id,)).fetchall()

    conn.close()
    return render_template("sale_detail.html", sale=sale, items=items)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and verify_password(user["hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["username"] = user["username"]
            return redirect("/")
        return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/products")
@login_required
def products():
    conn = get_db()
    products_rows = conn.execute(
        "SELECT * FROM products WHERE is_active = 1"
    ).fetchall()
    conn.close()
    return render_template("products.html", products=products_rows)


@app.route("/add_product", methods=["POST"])
@login_required
def add_product():
    if session.get("role") != "admin":
        return "Unauthorized"

    name = request.form.get("name")
    price = request.form.get("price")
    category = request.form.get("category")

    conn = get_db()
    conn.execute("""
        INSERT INTO products (name, price, category)
        VALUES (?, ?, ?)
    """, (name, price, category))
    conn.commit()
    conn.close()

    return redirect("/products")


@app.route("/new_sale", methods=["GET", "POST"])
@login_required
def new_sale():
    conn = get_db()
    today = datetime.now().date().isoformat()

    day = conn.execute("""
        SELECT status
        FROM business_days
        WHERE date = ?
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    if day and day["status"] == "closed":
        conn.close()
        return "Day is closed. No more sales allowed."

    if request.method == "POST":
        product_ids = request.form.getlist("product_id")
        quantities = request.form.getlist("quantity")

        subtotal = 0
        receipt_no = str(uuid.uuid4())[:8]
        created_at = datetime.now().isoformat()

        business_day_id = get_or_create_business_day(conn, session.get("user_id"))

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sales (receipt_no, user_id, created_at, subtotal, total, business_day_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (receipt_no, session["user_id"], created_at, 0, 0, business_day_id))
        sale_id = cursor.lastrowid

        for pid, qty in zip(product_ids, quantities):
            if int(qty) > 0:
                product = conn.execute(
                    "SELECT name, price FROM products WHERE id = ?", (pid,)
                ).fetchone()
                if not product:
                    continue

                product_name = product["name"]
                unit_price = float(product["price"])
                line_total = unit_price * int(qty)
                subtotal += line_total

                cursor.execute("""
                    INSERT INTO sale_items (sale_id, product_id, product_name, qty, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sale_id, pid, product_name, qty, unit_price, line_total))

        cursor.execute("""
            UPDATE sales SET subtotal = ?, total = ?
            WHERE id = ?
        """, (subtotal, subtotal, sale_id))

        conn.commit()
        conn.close()
        return redirect("/")

    products_rows = conn.execute(
        "SELECT * FROM products WHERE is_active = 1"
    ).fetchall()
    conn.close()

    return render_template("new_sale.html", products=products_rows)


@app.route("/void_receipt/<receipt_no>", methods=["POST"])
@login_required
def void_receipt(receipt_no):
    # We no longer have receipts/receipt_items tables.
    # Void the SALE by receipt_no.
    conn = get_db()

    conn.execute("""
        UPDATE sales
        SET is_void = 1
        WHERE receipt_no = ?
    """, (receipt_no,))
    conn.commit()

    sale = conn.execute("""
        SELECT id
        FROM sales
        WHERE receipt_no = ?
    """, (receipt_no,)).fetchone()

    conn.close()

    if sale:
        return redirect(f"/sale/{sale['id']}")
    return redirect("/receipts")


@app.route("/receipts")
@login_required
def receipts_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT s.id, s.receipt_no, s.created_at, s.total, s.is_void, u.username AS cashier_username
        FROM sales s
        LEFT JOIN users u ON u.id = s.user_id
        ORDER BY datetime(s.created_at) DESC
        LIMIT 200
    """).fetchall()
    conn.close()
    return render_template("receipts.html", receipts=rows)


@app.route("/process_sale", methods=["POST"])
@login_required
def process_sale():
    conn = get_db()

    # block if day closed (business_days only)
    today = datetime.now().date().isoformat()

    day = conn.execute("""
        SELECT status
        FROM business_days
        WHERE date = ?
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    if day and day["status"] == "closed":
        conn.close()
        return jsonify({"success": False, "error": "Day is closed"}), 400

    cart = request.get_json() or {}

    subtotal = 0
    receipt_no = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()

    business_day_id = get_or_create_business_day(conn, session.get("user_id"))

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sales (receipt_no, user_id, created_at, subtotal, total, business_day_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (receipt_no, session["user_id"], created_at, 0, 0, business_day_id))
    sale_id = cur.lastrowid

    for pid, item in cart.items():
        qty = int(item.get("qty", 0))
        if qty <= 0:
            continue

        product = conn.execute(
            "SELECT name, price FROM products WHERE id = ?",
            (int(pid),)
        ).fetchone()

        if not product:
            continue

        product_name = product["name"]
        unit_price = float(product["price"])
        line_total = qty * unit_price
        subtotal += line_total

        cur.execute("""
            INSERT INTO sale_items (sale_id, product_id, product_name, qty, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sale_id, int(pid), product_name, qty, unit_price, line_total))

    cur.execute("""
        UPDATE sales SET subtotal = ?, total = ?
        WHERE id = ?
    """, (subtotal, subtotal, sale_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "receipt_no": receipt_no})


@app.route("/receipt/<receipt_no>")
@login_required
def view_receipt(receipt_no):
    # We no longer have receipts tables.
    # Redirect to the sale detail (snapshot is in sale_items.product_name).
    conn = get_db()
    sale = conn.execute("""
        SELECT id
        FROM sales
        WHERE receipt_no = ?
    """, (receipt_no,)).fetchone()
    conn.close()

    if not sale:
        return "Receipt not found", 404

    return redirect(f"/sale/{sale['id']}")


@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html", role=session.get("role"))


@app.route("/daily_report")
@login_required
def daily_report():
    today = datetime.now().date().isoformat()
    conn = get_db()

    current_bd = conn.execute("""
        SELECT id
        FROM business_days
        WHERE date = ? AND status = 'open'
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    current_day_id = current_bd["id"] if current_bd else None

    sales = []
    total = 0

    if current_day_id:
        sales = conn.execute("""
            SELECT *
            FROM sales
            WHERE business_day_id = ?
              AND is_void = 0
            ORDER BY datetime(created_at) DESC
        """, (current_day_id,)).fetchall()

        total = sum(row["total"] for row in sales)

    count = len(sales)

    detailed_sales = []
    for sale in sales:
        items = conn.execute("""
            SELECT si.product_name AS name, si.qty, si.line_total
            FROM sale_items si
            WHERE si.sale_id = ?
        """, (sale["id"],)).fetchall()

        detailed_sales.append({
            "sale": sale,
            "items": items
        })

    conn.close()

    return render_template(
        "daily_report.html",
        total=total,
        count=count,
        detailed_sales=detailed_sales
    )


@app.route("/monthly_overview")
@login_required
def monthly_overview():
    if session.get("role") == "staff":
        return redirect("/reports")
    conn = get_db()

    months = conn.execute("""
        SELECT
            strftime('%m-%Y', created_at) AS month_label,
            strftime('%Y-%m', created_at) AS month_key,
            SUM(total) AS total
        FROM sales
        WHERE is_void = 0
        GROUP BY month_key
        ORDER BY month_key DESC
    """).fetchall()

    conn.close()
    return render_template("monthly_overview.html", months=months)


@app.route("/monthly_report")
@login_required
def monthly_report():
    if session.get("role") == "staff":
        return redirect("/reports")
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")

    conn = get_db()

    sales = conn.execute("""
        SELECT DATE(created_at) as day, SUM(total) as total
        FROM sales
        WHERE strftime('%Y-%m', created_at) = ?
          AND is_void = 0
        GROUP BY day
        ORDER BY day DESC
    """, (month,)).fetchall()

    month_total = sum(row["total"] for row in sales) if sales else 0

    conn.close()

    return render_template(
        "monthly_report.html",
        sales=sales,
        month=month,
        month_total=month_total
    )


@app.route("/close_day", methods=["POST"])
@login_required
def close_day():
    today = datetime.now().date().isoformat()
    conn = get_db()

    # If the latest business day for today is already closed, go to report
    latest = conn.execute("""
        SELECT id, status
        FROM business_days
        WHERE date = ?
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    if latest and latest["status"] == "closed":
        conn.close()
        return redirect("/daily_report")

    # Close the current OPEN business day (if any)
    current_bd = conn.execute("""
        SELECT id
        FROM business_days
        WHERE date = ? AND status = 'open'
        ORDER BY id DESC
        LIMIT 1
    """, (today,)).fetchone()

    if current_bd:
        conn.execute("""
            UPDATE business_days
            SET status = 'closed', closed_at = ?, closed_by = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), session["user_id"], current_bd["id"]))

    conn.commit()
    conn.close()
    return redirect("/daily_report")


# ---- Reopen Day separate credentials (change these) ----
REOPEN_USERNAME = "reopen"
REOPEN_PASSWORD = "reopen123"


@app.route("/reopen_day", methods=["GET", "POST"])
@login_required
def reopen_day():
    today = datetime.now().date().isoformat()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username != REOPEN_USERNAME or password != REOPEN_PASSWORD:
            return render_template("reopen_day.html", error="Invalid reopen credentials.")

        conn = get_db()

        # Start a NEW business day session (so dashboard/daily report reset immediately)
        conn.execute("""
            INSERT INTO business_days (date, opened_at, opened_by, status)
            VALUES (?, ?, ?, 'open')
        """, (today, datetime.now().isoformat(), session.get("user_id")))

        conn.commit()
        conn.close()
        return redirect("/")

    return render_template("reopen_day.html", error=None)

@app.route("/edit_product/<int:product_id>", methods=["POST"])
@login_required
def edit_product(product_id):
    if session.get("role") != "admin":
        return "Unauthorized", 403

    name = (request.form.get("name") or "").strip()
    price = request.form.get("price")

    if not name:
        return "Name required", 400

    try:
        price_val = float(price)
        if price_val < 0:
            return "Invalid price", 400
    except (TypeError, ValueError):
        return "Invalid price", 400

    conn = get_db()
    conn.execute("""
        UPDATE products
        SET name = ?, price = ?
        WHERE id = ?
    """, (name, price_val, product_id))
    conn.commit()
    conn.close()

    return redirect("/products")

@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    if session.get("role") != "admin":
        return "Unauthorized"

    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect("/products")


@app.route("/export_monthly_csv")
@login_required
def export_monthly_csv():
    if session.get("role") == "staff":
        return redirect("/reports")
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")

    conn = get_db()
    rows = conn.execute("""
        SELECT DATE(created_at) as day, SUM(total) as total
        FROM sales
        WHERE strftime('%Y-%m', created_at) = ?
          AND is_void = 0
        GROUP BY day
        ORDER BY day ASC
    """, (month,)).fetchall()
    conn.close()

    month_total = sum(r["total"] for r in rows) if rows else 0

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([f"Monthly Report - {month}"])
    writer.writerow([])
    writer.writerow(["Day", "Amount (DA)"])

    for r in rows:
        writer.writerow([r["day"], r["total"]])

    writer.writerow([])
    writer.writerow(["TOTAL", month_total])

    csv_data = output.getvalue()
    output.close()

    filename = f"monthly_report_{month}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/spendings", methods=["GET", "POST"])
@login_required
def spendings():
    conn = get_db()
    user_id = session.get("user_id")
    role = session.get("role")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price")
        note = request.form.get("note", "").strip()

        if name and price:
            conn.execute("""
                INSERT INTO spendings (user_id, name, price, note, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, name, float(price), note, datetime.now().isoformat()))
            conn.commit()

        conn.close()
        return redirect("/spendings")

    if role == "admin":
        rows = conn.execute("""
            SELECT sp.*, u.username
            FROM spendings sp
            JOIN users u ON u.id = sp.user_id
            ORDER BY datetime(sp.created_at) DESC
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT sp.*, u.username
            FROM spendings sp
            JOIN users u ON u.id = sp.user_id
            WHERE sp.user_id = ?
            ORDER BY datetime(sp.created_at) DESC
        """, (user_id,)).fetchall()

    conn.close()
    return render_template("spendings.html", rows=rows, role=role)


@app.route("/delete_spending/<int:spending_id>", methods=["POST"])
@login_required
def delete_spending(spending_id):
    conn = get_db()
    # only allow deleting your own, unless admin
    if session.get("role") == "admin":
        conn.execute("DELETE FROM spendings WHERE id = ?", (spending_id,))
    else:
        conn.execute("DELETE FROM spendings WHERE id = ? AND user_id = ?",
                     (spending_id, session.get("user_id")))
    conn.commit()
    conn.close()
    return redirect("/spendings")


if __name__ == "__main__":
    app.run(debug=True)
    