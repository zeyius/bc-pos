import sqlite3

DB_NAME = "pos.db"

MENU = [
    # Hot coffee
    ("Nespresso", 100, "Hot coffee"),
    ("Nespresso (caramel, noisette)", 120, "Hot coffee"),
    ("Espresso", 100, "Hot coffee"),
    ("Chocolate espresso", 150, "Hot coffee"),
    ("Americano", 150, "Hot coffee"),
    ("Cortado", 150, "Hot coffee"),
    ("Latte", 200, "Hot coffee"),
    ("Caramel latte", 250, "Hot coffee"),
    ("Cappuccino", 200, "Hot coffee"),
    ("Mochaccino", 250, "Hot coffee"),

    # Iced coffee
    ("Iced Americano", 150, "Iced coffee"),
    ("Iced coffee", 250, "Iced coffee"),
    ("Iced latte", 250, "Iced coffee"),

    # Non-Coffee
    ("Matcha latte", 500, "Non-Coffee"),
    ("Tea", 150, "Non-Coffee"),
    ("Lemon Tea", 200, "Non-Coffee"),
    ("Iced tea", 200, "Non-Coffee"),
    ("Iced lemon Tea", 250, "Non-Coffee"),
    ("Hot chocolate", 300, "Non-Coffee"),

    # Juices & Cocktails
    ("Orange juice", 250, "Juices & Cocktails"),
    ("Citron juice", 250, "Juices & Cocktails"),
    ("Banana juice", 250, "Juices & Cocktails"),
    ("Season fruits", 300, "Juices & Cocktails"),
    ("Cocktail", 350, "Juices & Cocktails"),
    ("Mojito", 300, "Juices & Cocktails"),
    ("Strawberry mojito", 400, "Juices & Cocktails"),

    # Milkshakes
    ("Chocolat", 350, "Milkshakes"),
    ("Chocolat Frappé", 450, "Milkshakes"),
    ("Cookies", 400, "Milkshakes"),
    ("Cookies Frappé", 500, "Milkshakes"),
    ("Caramel Frappé", 450, "Milkshakes"),
    ("Banana", 400, "Milkshakes"),
    ("Banana-Chocolat", 450, "Milkshakes"),
    ("Strawberry", 350, "Milkshakes"),

    # Sweets & Savory
    ("Croissant", 50, "Sweets & Savory"),
    ("Brownies", 150, "Sweets & Savory"),
    ("Cookies", 150, "Sweets & Savory"),
    ("Chocolate waffle", 300, "Sweets & Savory"),
    ("Banana-Chocolate waffle", 350, "Sweets & Savory"),
    ("Fruits waffle", 400, "Sweets & Savory"),
    ("Oreo waffle", 350, "Sweets & Savory"),
    ("Crêpes Chocolate", 300, "Sweets & Savory"),
    ("Crêpes Choco-Banana", 350, "Sweets & Savory"),
    ("Crêpes fruits", 400, "Sweets & Savory"),
    ("Pudding", 150, "Sweets & Savory"),
    ("Tiramisu", 300, "Sweets & Savory"),
    ("Croissant Brunch", 200, "Sweets & Savory"),
    ("Eggs & Toast", 250, "Sweets & Savory"),
]

def main():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")

    inserted = 0
    for name, price, category in MENU:
        # prevent duplicates
        exists = cur.execute(
            "SELECT 1 FROM products WHERE name = ?",
            (name,)
        ).fetchone()

        if not exists:
            cur.execute(
                "INSERT INTO products (name, price, category, is_active) VALUES (?, ?, ?, 1)",
                (name, price, category)
            )
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Seed completed. Inserted {inserted} products.")

if __name__ == "__main__":
    main()
