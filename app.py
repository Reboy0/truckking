import data_module as db
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # заміни на надійний ключ

# Ініціалізація бази даних при запуску
with app.app_context():
    db.init_db()
    db.init_sample_data()

def get_session_id():
    """Отримує або створює ID сесії для кошика"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

@app.route("/")
def mainlink():
    categories = db.get_all_categories()
    featured_products = db.get_all_products()[:8]
    return render_template("main.html", categories=categories, featured_products=featured_products)

@app.route("/products")
def products():
    category_id = request.args.get('category')
    search_query = request.args.get('search')
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)

    products = []
    categories = db.get_all_categories()

    if search_query:
        products = db.search_products(search_query)
    elif category_id:
        products = db.get_products_by_category(int(category_id))
    elif min_price and max_price:
        products = db.get_products_by_price_range(min_price, max_price)
    else:
        products = db.get_all_products()

    return render_template("products.html", 
                           products=products, 
                           categories=categories,
                           selected_category=int(category_id) if category_id else None)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product_data = db.get_product_with_images(product_id)
    if not product_data['product']:
        flash("Товар не знайдено", "error")
        return redirect(url_for('products'))

    return render_template("product_detail.html", 
                           product=product_data['product'], 
                           images=product_data['images'])

@app.route("/category/<int:category_id>")
def category_products(category_id):
    category = db.get_category_by_id(category_id)
    products = db.get_products_by_category(category_id)
    categories = db.get_all_categories()

    return render_template("category.html", 
                           category=category, 
                           products=products,
                           categories=categories)

@app.route("/search")
def search():
    query = request.args.get('q', '')
    products = db.search_products(query) if query else []
    categories = db.get_all_categories()

    return render_template("search_results.html", 
                           products=products, 
                           query=query,
                           categories=categories)

# --- Кошик ---
@app.route("/add_to_cart", methods=['POST'])
def add_to_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        session_id = get_session_id()
        db.add_to_cart(session_id, product_id, quantity)

        return jsonify({'success': True, 'message': 'Товар додано в кошик'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/remove_from_cart", methods=['POST'])
def remove_from_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')

        session_id = get_session_id()
        db.remove_from_cart(session_id, product_id)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/update_cart", methods=['POST'])
def update_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity')

        session_id = get_session_id()
        db.update_cart_quantity(session_id, product_id, quantity)

        cart_total = db.get_cart_total(session_id)
        cart_count = db.get_cart_count(session_id)

        return jsonify({
            'success': True,
            'cart_total': cart_total,
            'cart_count': cart_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/cart")
def cart():
    session_id = get_session_id()
    cart_items = db.get_cart_items(session_id)
    cart_total = db.get_cart_total(session_id)

    return render_template("cart.html", 
                           cart_items=cart_items, 
                           cart_total=cart_total)

@app.route("/cart_count")
def cart_count():
    session_id = get_session_id()
    count = db.get_cart_count(session_id)
    return jsonify({'count': count})

# --- Замовлення ---
@app.route("/checkout")
def checkout():
    session_id = get_session_id()
    cart_items = db.get_cart_items(session_id)
    cart_total = db.get_cart_total(session_id)

    if not cart_items:
        flash("Ваш кошик порожній", "warning")
        return redirect(url_for('cart'))

    return render_template("checkout.html", 
                           cart_items=cart_items, 
                           cart_total=cart_total)

@app.route("/place_order", methods=['POST'])
def place_order():
    try:
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        customer_phone = request.form.get('customer_phone')
        delivery_address = request.form.get('delivery_address')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes', '')

        session_id = get_session_id()
        cart_items = db.get_cart_items(session_id)

        if not cart_items:
            flash("Ваш кошик порожній", "error")
            return redirect(url_for('cart'))

        order_id = db.create_order(
            session_id=session_id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            payment_method=payment_method,
            notes=notes
        )

        db.clear_cart(session_id)

        flash(f"Замовлення №{order_id} успішно оформлено!", "success")
        return redirect(url_for('order_success', order_id=order_id))

    except Exception as e:
        flash(f"Помилка при оформленні замовлення: {str(e)}", "error")
        return redirect(url_for('checkout'))

@app.route("/order_success/<int:order_id>")
def order_success(order_id):
    order = db.get_order_by_id(order_id)
    if not order:
        flash("Замовлення не знайдено", "error")
        return redirect(url_for('mainlink'))

    return render_template("order_success.html", order=order)

@app.route("/my_orders")
def my_orders():
    session_id = get_session_id()
    orders = db.get_orders_by_session(session_id)
    return render_template("my_orders.html", orders=orders)

@app.context_processor
def inject_categories():
    return dict(categories=db.get_all_categories())

@app.context_processor
def inject_cart_count():
    session_id = get_session_id()
    cart_count = db.get_cart_count(session_id)
    return dict(cart_count=cart_count)

if __name__ == "__main__":
    app.run(debug=True)
