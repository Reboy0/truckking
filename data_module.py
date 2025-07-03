import sqlite3
import os
import shutil
import uuid
from werkzeug.utils import secure_filename

DB_NAME = 'shop.db'
IMAGE_FOLDER = 'images'

def connect():
    return sqlite3.connect(DB_NAME)

def init_db():
    with connect() as conn:
        cur = conn.cursor()
        # Таблиця категорій (оновлена структура)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                slug TEXT UNIQUE NOT NULL,
                parent_slug TEXT,
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
                category_slug TEXT,
                stock_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_slug) REFERENCES categories(slug)
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
        # Таблиця характеристик товарів
        cur.execute('''
            CREATE TABLE IF NOT EXISTS product_attributes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                name TEXT NOT NULL,
                value TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)
# --- Характеристики товару ---
def add_product_attribute(product_id, name, value):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO product_attributes (product_id, name, value) VALUES (?, ?, ?)', (product_id, name, value))
        conn.commit()

def get_product_attributes(product_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT name, value FROM product_attributes WHERE product_id = ?', (product_id,))
        return cur.fetchall()

# Функції для категорій
def add_category(name, slug, parent_slug=None, description=None):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO categories (name, slug, parent_slug, description) VALUES (?, ?, ?, ?)', (name, slug, parent_slug, description))
        conn.commit()
        return cur.lastrowid

def get_all_categories():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM categories')
        return cur.fetchall()

def get_category_by_slug(slug):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM categories WHERE slug = ?', (slug,))
        return cur.fetchone()

def get_subcategories(parent_slug):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM categories WHERE parent_slug = ?', (parent_slug,))
        return cur.fetchall()

def get_all_categories_tree():
    # Повертає дерево категорій у вигляді вкладених dict
    def build_tree(categories, parent_slug=None):
        tree = []
        for cat in [c for c in categories if c[3] == parent_slug]:
            node = {
                'id': cat[0],
                'name': cat[1],
                'slug': cat[2],
                'parent_slug': cat[3],
                'description': cat[4],
                'children': build_tree(categories, cat[2])
            }
            tree.append(node)
        return tree
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM categories')
        categories = cur.fetchall()
    return build_tree(categories)

# --- Додаткові функції для роботи з категоріями через slug ---
def get_category_id_by_slug(slug):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id FROM categories WHERE slug = ?', (slug,))
        row = cur.fetchone()
        return row[0] if row else None

def get_products_by_category_slug(category_slug):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_slug = c.slug 
                       WHERE p.category_slug = ?''', (category_slug,))
        products = cur.fetchall()
    return add_image_url_to_products(products)

# --- Масове додавання категорій з ієрархією (для ініціалізації) ---
def bulk_add_categories_tree(categories_tree):
    """
    categories_tree: список dict з ключами name, slug, parent_slug, description, children (рекурсивно)
    """
    def add_node(node, parent_slug=None):
        add_category(node['name'], node['slug'], parent_slug, node.get('description'))
        for child in node.get('children', []):
            add_node(child, node['slug'])
    for cat in categories_tree:
        add_node(cat)

# --- Генератор slug ---
def slugify(text):
    import re
    text = text.lower()
    text = re.sub(r'[^a-zа-я0-9]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

# --- Приклад структури категорій для ініціалізації ---
def get_default_categories_tree():
    return [
        {
            'name': 'Двигун та комплектуючі',
            'slug': 'dvygun',
            'description': '',
            'children': [
                {'name': 'Двигуни в зборі', 'slug': 'dvyguny-v-zbori'},
                {'name': 'Блоки циліндрів', 'slug': 'bloky-cylindriv'},
                {'name': 'Головки блока', 'slug': 'holovky-bloka'},
                {'name': 'Поршні, кільця, вкладиші', 'slug': 'porshni-kiltsya-vkladyshi'},
                {'name': 'Турбіни, інтеркулери', 'slug': 'turbiny-interkulery'},
                {'name': 'Паливні системи (насоси, форсунки)', 'slug': 'palyvni-systemy'},
                {'name': 'Масляні та паливні фільтри', 'slug': 'maslyani-ta-palyvni-filtry'},
                {'name': 'Прокладки, ущільнення', 'slug': 'prokladky-ushchilnennia'},
            ]
        },
        {
            'name': 'Трансмісія',
            'slug': 'transmisiya',
            'children': [
                {'name': 'Коробки передач (механічні, автоматичні)', 'slug': 'korobky-peredach'},
                {'name': 'Зчеплення (диски, кошики, вижимні підшипники)', 'slug': 'zcheplennia'},
                {'name': 'Карданні вали', 'slug': 'kardanni-valy'},
                {'name': 'Мости та редуктори', 'slug': 'mosty-ta-reduktory'},
                {'name': 'Піввісі', 'slug': 'pivvisi'},
            ]
        },
        {
            'name': 'Ходова частина',
            'slug': 'khodova',
            'children': [
                {'name': 'Амортизатори', 'slug': 'amortyzatory'},
                {'name': 'Пружини, ресори', 'slug': 'pruzhyny-resory'},
                {'name': 'Важелі, сайлентблоки', 'slug': 'vazheli-sailentbloki'},
                {'name': 'Стабілізатори', 'slug': 'stabilizatory'},
                {'name': 'Підшипники коліс', 'slug': 'pidshypnyky-kolis'},
            ]
        },
        {
            'name': 'Гальмівна система',
            'slug': 'halmivna-systema',
            'children': [
                {'name': 'Гальмівні колодки, диски, барабани', 'slug': 'halmivni-kolodky'},
                {'name': 'Гальмівні супорти', 'slug': 'halmivni-suporty'},
                {'name': 'Пневмогальмівні системи', 'slug': 'pnevmohalmivni-systemy'},
                {'name': 'Гальмівні шланги, трубки', 'slug': 'halmivni-shlangy-trubky'},
                {'name': 'ABS, EBS системи', 'slug': 'abs-ebs-systemy'},
            ]
        },
        {
            'name': 'Системи охолодження та опалення',
            'slug': 'okholodzhennia-opalennia',
            'children': [
                {'name': 'Радіатори', 'slug': 'radiatory'},
                {'name': 'Термостати', 'slug': 'termostaty'},
                {'name': 'Вентилятори', 'slug': 'ventyliatory'},
                {'name': 'Печі, обігрівачі', 'slug': 'pechi-obigrivachi'},
                {'name': 'Інтеркулери', 'slug': 'interkulery'},
                {'name': 'Помпи охолодження', 'slug': 'pompy-okholodzhennia'},
            ]
        },
        {
            'name': 'Електрика та електроніка',
            'slug': 'elektryka-elektronika',
            'children': [
                {'name': 'Генератори, стартери', 'slug': 'henaratory-startery'},
                {'name': 'Акумулятори', 'slug': 'akumulyatory'},
                {'name': 'Датчики (ABS, тиску, температури)', 'slug': 'datchyky'},
                {'name': 'ЕБУ (електронні блоки управління)', 'slug': 'ebu'},
                {'name': 'Світло (фари, лампи, підсвітка)', 'slug': 'svitlo'},
                {'name': 'Реле, запобіжники, проводка', 'slug': 'rele-zapobizhnyky-provodka'},
            ]
        },
        {
            'name': 'Кузовні запчастини',
            'slug': 'kuzovni-zapchastyny',
            'children': [
                {'name': 'Бампери', 'slug': 'bampery'},
                {'name': 'Крила, двері, капоти', 'slug': 'kryla-dveri-kapoty'},
                {'name': 'Дзеркала', 'slug': 'dzerkala'},
                {'name': 'Скло', 'slug': 'sklo'},
                {'name': 'Фари, поворотники, ліхтарі', 'slug': 'fary-povorotnyky-lihtari'},
            ]
        },
        {
            'name': 'Витратні матеріали та інструменти',
            'slug': 'vytratni-materialy',
            'children': [
                {'name': 'Масла, технічні рідини', 'slug': 'masla-tekhnichni-ridyny'},
                {'name': 'Фільтри (масляні, паливні, повітряні)', 'slug': 'filtry'},
                {'name': 'Ущільнювачі, прокладки', 'slug': 'ushchilnyuvachi-prokladky'},
                {'name': 'Герметики, клеї', 'slug': 'hermetyky-klei'},
                {'name': 'Інструмент (ключі, знімачі)', 'slug': 'instrument'},
            ]
        },
        {
            'name': 'Пневматика та гідравліка',
            'slug': 'pnevmatyka-hidravlika',
            'children': [
                {'name': 'Пневмоподушки', 'slug': 'pnevmopodushky'},
                {'name': 'Компресори', 'slug': 'kompresory'},
                {'name': 'Пневматичні клапани', 'slug': 'pnevmatychni-klapany'},
                {'name': 'Гідравлічні насоси, циліндри', 'slug': 'hidravlichni-nasosy-tsylindry'},
            ]
        },
        {
            'name': 'Система вихлопу',
            'slug': 'vykhlop',
            'children': [
                {'name': 'Глушники', 'slug': 'hlushnyky'},
                {'name': 'Каталізатори', 'slug': 'katalizatory'},
                {'name': 'Сажеві фільтри (DPF)', 'slug': 'sazhevi-filtry'},
                {'name': 'Труби, хомути, ущільнення', 'slug': 'truby-khomuty-ushchilnennia'},
            ]
        },
        {
            'name': 'Кабіна та інтер’єр',
            'slug': 'kabina-interier',
            'children': [
                {'name': 'Сидіння', 'slug': 'sydinnia'},
                {'name': 'Панелі приладів', 'slug': 'paneli-pryladiv'},
                {'name': 'Педалі', 'slug': 'pedali'},
                {'name': 'Ремені безпеки', 'slug': 'remeni-bezpeky'},
                {'name': 'Ручки, перемикачі', 'slug': 'ruchky-peremikachi'},
            ]
        },
        {
            'name': 'Навігація та обладнання',
            'slug': 'navigatsiya-obladnannya',
            'children': [
                {'name': 'GPS-навігатори', 'slug': 'gps-navigator'},
                {'name': 'Тахографи', 'slug': 'tahografy'},
                {'name': 'Відеореєстратори', 'slug': 'videreyestratory'},
                {'name': 'Камери заднього огляду', 'slug': 'kamery-zadnoho-ohlyadu'},
            ]
        },
        {
            'name': 'Спеціалізовані запчастини для тягачів і напівпричепів',
            'slug': 'spetszapchastyny-tyagachiv-napivprychepiv',
            'children': [
                {'name': 'Зчіпні пристрої (седельні механізми)', 'slug': 'zchipni-prystroyi'},
                {'name': 'Опори, домкрати', 'slug': 'opory-domkraty'},
                {'name': 'Блоки АБС для причепів', 'slug': 'bloki-abs-prychepiv'},
                {'name': 'Осі напівпричепів', 'slug': 'osi-napivprychepiv'},
                {'name': 'Системи освітлення для причепів', 'slug': 'svitlo-prychepiv'},
            ]
        },
        {
            'name': 'Аксесуари та додаткове обладнання',
            'slug': 'aksesuary',
            'children': [
                {'name': 'Дефлектори, чохли, накладки', 'slug': 'deflektory-chokhly-nakladky'},
                {'name': 'Хромовані елементи', 'slug': 'khromovani-elementy'},
                {'name': 'Підігріви сидінь, підлокітники', 'slug': 'pidihryvy-sydin-pidlokytnyky'},
            ]
        },
    ]
# Функції для продуктів
def add_product(name, price, buyprice, description=None, category_slug=None, stock_quantity=0):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''INSERT INTO products (name, price, buyprice, description, category_slug, stock_quantity) 
                       VALUES (?, ?, ?, ?, ?, ?)''', 
                   (name, price, buyprice, description, category_slug, stock_quantity))
        conn.commit()
        return cur.lastrowid

def add_image_url_to_products(products):
    # products: list of tuples (як fetchall)
    # Повертає список dict з image_url
    result = []
    with connect() as conn:
        cur = conn.cursor()
        for prod in products:
            product_id = prod[0]
            cur.execute('SELECT image_path FROM product_images WHERE product_id = ? LIMIT 1', (product_id,))
            img = cur.fetchone()
            if img and img[0]:
                if img[0].startswith('images/'):
                    image_url = f"/{img[0]}"
                else:
                    image_url = f"/images/{os.path.basename(img[0])}"
            else:
                image_url = '/static/images/products/default.png'
            prod_dict = {
                'id': prod[0],
                'name': prod[1],
                'price': prod[2],
                'buyprice': prod[3],  # Ціна закупки повертається у всіх продуктах
                'description': str(prod[4]) if prod[4] is not None else '',
                'category_slug': prod[5],
                'stock_quantity': prod[6],
                'created_at': prod[7],
                'category_name': prod[8] if len(prod) > 8 else None,
                'image_url': image_url
            }
            result.append(prod_dict)
    return result

def get_all_products():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_slug = c.slug''')
        products = cur.fetchall()
    return add_image_url_to_products(products)

def get_products_by_category(category_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_slug = c.slug 
                       WHERE p.category_slug = ?''', (category_id,))
        products = cur.fetchall()
    return add_image_url_to_products(products)

def search_products(query):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_slug = c.slug 
                       WHERE p.name LIKE ? OR p.description LIKE ?''', 
                   (f'%{query}%', f'%{query}%'))
        products = cur.fetchall()
    return add_image_url_to_products(products)

def get_products_by_price_range(min_price, max_price):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_slug = c.slug 
                       WHERE p.price BETWEEN ? AND ?''', (min_price, max_price))
        products = cur.fetchall()
    return add_image_url_to_products(products)


def save_product_image(image_file):
    """Зберігає файл у папку images, повертає ім'я файлу."""
    if not image_file or image_file.filename == '':
        return None
    filename = secure_filename(image_file.filename)
    save_path = os.path.join(IMAGE_FOLDER, filename)
    image_file.save(save_path)
    return filename

def add_product_with_image(name, price, buyprice, description, category_id, stock_quantity, image_file):
    product_id = add_product(name, price, buyprice, description, category_id, stock_quantity)
    filename = save_product_image(image_file)
    if filename:
        with connect() as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO product_images (product_id, image_path) VALUES (?, ?)', (product_id, filename))
            conn.commit()
    return product_id

def add_product_image(product_id, image_file):
    filename = save_product_image(image_file)
    if filename:
        with connect() as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO product_images (product_id, image_path) VALUES (?, ?)', (product_id, filename))
            conn.commit()
def get_product_with_images(product_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT p.*, c.name as category_name 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_slug = c.slug 
                       WHERE p.id = ?''', (product_id,))
        prod = cur.fetchone()
        if not prod:
            return {'product': None, 'images': []}
        # Отримати всі фото
        cur.execute('SELECT image_path FROM product_images WHERE product_id = ?', (product_id,))
        images = cur.fetchall()
        image_urls = []
        for img in images:
            if img and img[0]:
                if img[0].startswith('/images/'):
                    image_urls.append(img[0])
                elif img[0].startswith('images/'):
                    image_urls.append('/' + img[0])
                else:
                    image_urls.append(f"/images/{os.path.basename(img[0])}")
        product_dict = {
            'id': prod[0],
            'name': prod[1],
            'price': prod[2],
            'buyprice': prod[3],
            'description': prod[4],
            'category_slug': prod[5],
            'stock_quantity': prod[6],
            'created_at': prod[7],
            'category_name': prod[8] if len(prod) > 8 else None,
            'image_url': image_urls[0] if image_urls else '/static/images/products/default.png'
        }
        attributes = get_product_attributes(product_id)
        # Якщо всі характеристики мають name == "Текст", то показуємо просто список текстів
        if attributes and all(a[0] == "Текст" for a in attributes):
            attributes = [a[1] for a in attributes]
        return {
            'product': product_dict,
            'images': [{'image_url': url} for url in image_urls],
            'attributes': attributes
        }

def get_product_images(product_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('SELECT image_path FROM product_images WHERE product_id = ?', (product_id,))
        images = cur.fetchall()
        return [img[0] for img in images]

# Функції для кошика
def add_to_cart(session_id, product_id, quantity=1):
    print(f"DB add_to_cart: session_id={session_id}, product_id={product_id}, quantity={quantity}")
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
    print(f"DB get_cart_items: session_id={session_id}")
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.description,
                   (c.quantity * p.price) as total_price,
                   (
                       SELECT image_path FROM product_images pi WHERE pi.product_id = p.id LIMIT 1
                   ) as image_url
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.session_id = ?
            ORDER BY c.created_at DESC
        ''', (session_id,))
        rows = cur.fetchall()
        print(f"DB get_cart_items: found {len(rows)} items")
        return [
            {
                'cart_id': row[0],
                'id': row[1],
                'quantity': row[2],
                'name': row[3],
                'price': row[4],
                'description': row[5],
                'total_price': row[6],
                # Формуємо абсолютний шлях до фото для шаблону
                'image_url': (f"/{row[7]}" if row[7] else None)
            }
            for row in rows
        ]

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
        total_amount = sum(item['total_price'] for item in cart_items)
        # Створюємо замовлення
        cur.execute('''
            INSERT INTO orders (session_id, customer_name, customer_email, customer_phone,
                              delivery_address, payment_method, notes, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (session_id, customer_name, customer_email, customer_phone,
              delivery_address, payment_method, notes, total_amount))
        order_id = cur.lastrowid
        # Додаємо товари до замовлення
        for item in cart_items:
            cur.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, 
                                       product_price, quantity, total_price)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (order_id, item['id'], item['name'], item['price'], item['quantity'], item['total_price']))
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

def update_category(slug, name=None, parent_slug=None, description=None):
    with connect() as conn:
        cur = conn.cursor()
        fields = []
        values = []
        if name is not None:
            fields.append('name = ?')
            values.append(name)
        if parent_slug is not None:
            fields.append('parent_slug = ?')
            values.append(parent_slug)
        if description is not None:
            fields.append('description = ?')
            values.append(description)
        if not fields:
            return
        values.append(slug)
        cur.execute(f'UPDATE categories SET {", ".join(fields)} WHERE slug = ?', values)
        conn.commit()

def delete_category(slug):
    with connect() as conn:
        cur = conn.cursor()
        # Видаляємо підкатегорії рекурсивно
        cur.execute('SELECT slug FROM categories WHERE parent_slug = ?', (slug,))
        children = cur.fetchall()
        for child in children:
            delete_category(child[0])
        # Видаляємо саму категорію
        cur.execute('DELETE FROM categories WHERE slug = ?', (slug,))
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