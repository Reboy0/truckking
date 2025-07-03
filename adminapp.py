from flask import Flask, render_template, request, redirect, url_for
from data_module import init_db, get_all_categories, add_category, get_all_products, add_product, add_product_image
import os
import uuid

admapp = Flask(__name__)
admapp.config['UPLOAD_FOLDER'] = 'images'

init_db()

@admapp.route('/admin')
def admin_home():
    return render_template('admin/home.html')

@admapp.route('/admin/categories')
def admin_categories():
    data = get_all_categories()
    return render_template('admin/categories.html', categories=data)

@admapp.route('/admin/categories/add', methods=['POST'])
def admin_add_category():
    name = request.form['name']
    description = request.form.get('description')
    add_category(name, description)
    return redirect(url_for('admin/categories'))

@admapp.route('/admin/products')
def admin_products():
    data = get_all_products()
    return render_template('admin/products.html', products=data)


@admapp.route('/admin/products/add', methods=['GET', 'POST'])
def admin_add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = int(request.form['price'])
        buyprice = int(request.form['buyprice'])
        description = request.form.get('description')
        category_id = int(request.form['category_id'])
        stock_quantity = int(request.form['stock_quantity'])

        # Додаємо товар у базу
        product_id = add_product(name, price, buyprice, description, category_id, stock_quantity)

        # Обробка зображення
        image = request.files['image']
        if image and image.filename != '':
            add_product_image(product_id, image)

        return redirect(url_for('admin_products'))

    categories = get_all_categories()
    return render_template('admin/add_product.html', categories=categories)


if __name__ == '__main__':
    admapp.run(debug=True)
