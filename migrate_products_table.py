
# migrate_products_table.py
"""
Скрипт для міграції таблиці products: видаляє стару таблицю (якщо існує) та створює нову з полем category_slug.
"""
import sqlite3

def migrate_products_table():
    conn = sqlite3.connect("shop.db")
    cur = conn.cursor()
    # Видалити стару таблицю, якщо існує
    cur.execute("DROP TABLE IF EXISTS products")
    # Створити нову таблицю з потрібними полями
    cur.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_slug TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL,
        description TEXT,
        image_url TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("Таблиця products успішно пересоздана з полем category_slug.")

if __name__ == "__main__":
    migrate_products_table()
