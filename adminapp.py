from flask import Flask, render_template, request, redirect, url_for
from data_module import (
    init_db, get_all_categories, add_category, get_all_products, add_product, add_product_image,
    get_all_categories_tree, get_category_by_slug, update_category, delete_category
)
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
    tree = get_all_categories_tree()
    return render_template('admin/categories.html', categories=data, tree=tree)

@admapp.route('/admin/categories/add', methods=['POST'])
def admin_add_category():
    name = request.form['name']
    slug = request.form['slug']
    parent_slug = request.form.get('parent_slug') or None
    description = request.form.get('description')
    add_category(name, slug, parent_slug, description)
    return redirect(url_for('admin_categories'))

@admapp.route('/admin/categories/delete/<slug>', methods=['POST'])
def admin_delete_category(slug):
    delete_category(slug)
    return redirect(url_for('admin_categories'))

@admapp.route('/admin/categories/edit/<slug>', methods=['GET', 'POST'])
def admin_edit_category(slug):
    cat = get_category_by_slug(slug)
    if request.method == 'POST':
        name = request.form['name']
        parent_slug = request.form.get('parent_slug') or None
        description = request.form.get('description')
        update_category(slug, name=name, parent_slug=parent_slug, description=description)
        return redirect(url_for('admin_categories'))
    all_cats = get_all_categories()
    return render_template('admin/edit_category.html', category=cat, categories=all_cats)

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

        # Додаємо характеристики (кожен рядок — окрема характеристика, просто текст)
        attributes_text = request.form.get('attributes', '').strip()
        if attributes_text:
            for line in attributes_text.splitlines():
                line = line.strip()
                if line:
                    # Зберігаємо як характеристика з назвою "Текст" і значенням — увесь рядок
                    from data_module import add_product_attribute
                    add_product_attribute(product_id, "Текст", line)

        return redirect(url_for('admin_products'))

    categories = get_all_categories()
    return render_template('admin/add_product.html', categories=categories)


if __name__ == '__main__':
    admapp.run(debug=True)
