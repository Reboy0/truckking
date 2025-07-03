import sqlite3
import os
import shutil
import uuid
DB_NAME = 'shop.db'
IMAGE_FOLDER = 'images'

def connect():
    return sqlite3.connect(DB_NAME)

def init_db():
    with connect() as conn:
        cur = conn.cursor()
        
        # Таблиця категорій
        cur.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            )
        ''')
        
        # Таблиця продуктів
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                buyprice INTEGER NOT NULL,
                description TEXT,
                category_id INTEGER,
                stock_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        # Таблиця зображень продуктів
        cur.execute('''
            CREATE TABLE IF NOT EXISTS product_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                image_path TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')

        # Таблиця кошика
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')
        
        # Таблиця замовлень
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                delivery_address TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                notes TEXT,
                status TEXT DEFAULT 'new',
                total_amount INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблиця елементів замовлень
        cur.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                product_price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_price INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')

        conn.commit()
    
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)

# Функції для категорій
def add_category(name, description=None):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO categories (name, description) VALUES (?, ?)', (name, description))
        conn.commit()
        return cur.lastrowid

def get_all_categories():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM categories')
        return cur.fetchall()

def get_category_by_id(category_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
        return cur.fetchone()

# Функції для продуктів
def add_product(name, price, buyprice, description=None, category_id=None, stock_quantity=0):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''INSERT INTO products (name, price, buyprice, description, category_id, stock_quantity) 
                       VALUES (?, ?, ?, ?, ?, ?)''', 
                   (name, price, buyprice, description, category_id, stock_quantity))
        conn.commit()
        return cur.lastrowid

def get_all_products():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_id = c.id''')
        return cur.fetchall()

def get_products_by_category(category_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.category_id = ?''', (category_id,))
        return cur.fetchall()

def search_products(query):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.name LIKE ? OR p.description LIKE ?''', 
                   (f'%{query}%', f'%{query}%'))
        return cur.fetchall()

def get_products_by_price_range(min_price, max_price):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.price BETWEEN ? AND ?''', (min_price, max_price))
        return cur.fetchall()


def add_product_image(product_id, image_file):
    # Генеруємо унікальне ім’я файла
    filename = f"{uuid.uuid4().hex}_{image_file.filename}"
    dest_path = os.path.join(IMAGE_FOLDER, filename)

    # Створюємо папку images, якщо не існує
    os.makedirs(IMAGE_FOLDER, exist_ok=True)

    # Зберігаємо файл
    image_file.save(dest_path)

    # Додаємо шлях до БД
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO product_images (product_id, image_path) VALUES (?, ?)', (product_id, dest_path))
        conn.commit()
def get_product_with_images(product_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.id = ?''', (product_id,))
        product = cur.fetchone()

        cur.execute('SELECT image_path FROM product_images WHERE product_id = ?', (product_id,))
        images = cur.fetchall()

        return {
            "product": product,
            "images": [img[0] for img in images]
        }

def get_product_images(product_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT image_path FROM product_images WHERE product_id = ?', (product_id,))
        images = cur.fetchall()
        return [img[0] for img in images]

# Функції для кошика
def add_to_cart(session_id, product_id, quantity=1):
    with connect() as conn:
        cur = conn.cursor()
        # Перевіряємо чи товар вже є в кошику
        cur.execute('SELECT id, quantity FROM cart WHERE session_id = ? AND product_id = ?', 
                   (session_id, product_id))
        existing = cur.fetchone()
        
        if existing:
            # Якщо товар вже є, збільшуємо кількість
            new_quantity = existing[1] + quantity
            cur.execute('UPDATE cart SET quantity = ? WHERE id = ?', (new_quantity, existing[0]))
        else:
            # Додаємо новий товар в кошик
            cur.execute('INSERT INTO cart (session_id, product_id, quantity) VALUES (?, ?, ?)', 
                       (session_id, product_id, quantity))
        conn.commit()

def get_cart_items(session_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.description,
                   (c.quantity * p.price) as total_price
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.session_id = ?
            ORDER BY c.created_at DESC
        ''', (session_id,))
        return cur.fetchall()

def update_cart_quantity(session_id, product_id, quantity):
    with connect() as conn:
        cur = conn.cursor()
        if quantity <= 0:
            cur.execute('DELETE FROM cart WHERE session_id = ? AND product_id = ?', 
                       (session_id, product_id))
        else:
            cur.execute('UPDATE cart SET quantity = ? WHERE session_id = ? AND product_id = ?', 
                       (quantity, session_id, product_id))
        conn.commit()

def remove_from_cart(session_id, product_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM cart WHERE session_id = ? AND product_id = ?', 
                   (session_id, product_id))
        conn.commit()

def get_cart_count(session_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT SUM(quantity) FROM cart WHERE session_id = ?', (session_id,))
        result = cur.fetchone()
        return result[0] if result[0] else 0

def get_cart_total(session_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT SUM(c.quantity * p.price)
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.session_id = ?
        ''', (session_id,))
        result = cur.fetchone()
        return result[0] if result[0] else 0

def clear_cart(session_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM cart WHERE session_id = ?', (session_id,))
        conn.commit()

# Функції для замовлень
def create_order(session_id, customer_name, customer_email, customer_phone, 
                delivery_address, payment_method, notes=''):
    with connect() as conn:
        cur = conn.cursor()
        
        # Спочатку отримуємо товари з кошика
        cart_items = get_cart_items(session_id)
        if not cart_items:
            raise ValueError("Кошик порожній")
        
        # Розраховуємо загальну суму
        total_amount = sum(item[6] for item in cart_items)  # item[6] - це total_price
        
        # Створюємо замовлення
        cur.execute('''
            INSERT INTO orders (session_id, customer_name, customer_email, customer_phone,
                              delivery_address, payment_method, notes, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, customer_name, customer_email, customer_phone,
              delivery_address, payment_method, notes, total_amount))
        
        order_id = cur.lastrowid
        
        # Додаємо товари до замовлення
        for item in cart_items:
            cur.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, 
                                       product_price, quantity, total_price)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, item[1], item[3], item[4], item[2], item[6]))
        
        conn.commit()
        return order_id

def get_order_by_id(order_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cur.fetchone()
        
        if order:
            # Отримуємо товари замовлення
            cur.execute('''
                SELECT * FROM order_items WHERE order_id = ?
            ''', (order_id,))
            items = cur.fetchall()
            
            return {
                'order': order,
                'items': items
            }
        return None

def get_orders_by_session(session_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM orders 
            WHERE session_id = ? 
            ORDER BY created_at DESC
        ''', (session_id,))
        return cur.fetchall()

def update_order_status(order_id, status):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()

# Функція для ініціалізації тестових даних
"""def init_sample_data():
    # Додаємо категорії
    #categories = [
        ("Деталі двигуна", "Запчастини для двигунів вантажних автомобілів"),
        ("Гальмівна система", "Гальмівні колодки, диски, барабани"),
        ("Підвіска", "Амортизатори, пружини, стійки"),
        ("Трансмісія", "Зчеплення, КПП, диференціали"),
        ("Електрика", "Генератори, стартери, акумулятори"),
        ("Кузовні деталі", "Бампери, фари, дзеркала")
    ]
    
    with connect() as conn:
        cur = conn.cursor()
        for name, desc in categories:
            cur.execute('INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)', (name, desc))
        
        # Додаємо тестові продукти для вантажних авто
        products = [
            ("Фільтр масляний MANN W950", 450, 350, "Масляний фільтр для двигунів MAN, Mercedes", 1, 25),
            ("Гальмівні колодки BPW", 2800, 2200, "Колодки для осей BPW", 2, 12),
            ("Амортизатор SAF передній", 3500, 2800, "Передній амортизатор для причепів SAF", 3, 8),
            ("Диск зчеплення Volvo", 5200, 4200, "Диск зчеплення для Volvo FH/FM", 4, 6),
            ("Генератор 24V Mercedes", 8500, 7000, "Генератор для Mercedes Actros", 5, 4),
            ("Фара передня MAN TGX", 4200, 3400, "Передня фара для MAN TGX", 6, 10),
            ("Повітряний фільтр Scania", 680, 520, "Повітряний фільтр для Scania R-серії", 1, 15),
            ("Гальмівний барабан DAF", 3200, 2600, "Задній гальмівний барабан DAF XF", 2, 7)
        ]
        
        for name, price, buyprice, desc, cat_id, stock in products:
            cur.execute('''INSERT OR IGNORE INTO products 
                          (name, price, buyprice, description, category_id, stock_quantity) 
                          VALUES (?, ?, ?, ?, ?, ?)''', 
                       (name, price, buyprice, desc, cat_id, stock))
        
        conn.commit()"""