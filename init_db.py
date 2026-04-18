import sqlite3
import hashlib

DB_NAME = "pos.db"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL,
            role TEXT NOT NULL
        );
    """)

    # PRODUCTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            image TEXT,
            is_active INTEGER DEFAULT 1
        );
    """)

    # SALES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            subtotal REAL NOT NULL,
            total REAL NOT NULL,
            is_void INTEGER DEFAULT 0,
            business_day_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # SALE ITEMS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    # DAY CLOSURES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS day_closures (
            date TEXT PRIMARY KEY,
            closed_at TEXT NOT NULL,
            closed_by INTEGER NOT NULL,
            FOREIGN KEY (closed_by) REFERENCES users(id)
        );
    """)

    # BUSINESS DAYS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            opened_by INTEGER,
            closed_by INTEGER,
            status TEXT NOT NULL DEFAULT 'open'
        );
    """)

    conn.commit()

    # Create default admin if not exists
    cursor.execute("SELECT 1 FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        password_hash = hash_password("admin123")
        cursor.execute("""
            INSERT INTO users (username, hash, role)
            VALUES (?, ?, ?)
        """, ("admin", password_hash, "admin"))
        conn.commit()
        print("Default admin created (username: admin / password: admin123)")

    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
