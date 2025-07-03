
# Оновлений скрипт для ініціалізації категорій і тестових товарів під нову структуру (slug, характеристики)
import data_module
import random

def is_leaf_category(cat, all_cats):
    # leaf якщо немає підкатегорій
    return not any(c[3] == cat[2] for c in all_cats)

def main():
    # Додаємо дерево категорій
    categories_tree = data_module.get_default_categories_tree()
    data_module.bulk_add_categories_tree(categories_tree)
    print("Категорії додано!")

    # Додаємо по 3 товари у кожну leaf-категорію (slug)
    categories = data_module.get_all_categories()
    product_names = [
        "Тестовий товар {i} для {cat}",
        "Оригінал {cat}",
        "Преміум {cat}"
    ]
    for cat in categories:
        cat_id, cat_name, cat_slug, parent_slug, *_ = cat
        if not is_leaf_category(cat, categories):
            continue
        for i in range(3):
            name = product_names[i].format(i=i+1, cat=cat_name)
            price = random.randint(500, 5000)
            buyprice = max(1, price - random.randint(100, 400))
            description = f"Опис для {name}"
            stock = random.randint(5, 30)
            product_id = data_module.add_product(name, price, buyprice, description, cat_slug, stock)
            # Додаємо характеристики для тесту
            data_module.add_product_attribute(product_id, "Виробник", random.choice(["Bosch", "MANN", "Febi", "Sachs"]))
            data_module.add_product_attribute(product_id, "Гарантія", random.choice(["6 міс.", "12 міс.", "Без гарантії"]))
    print("Тестові товари та характеристики додано!")

if __name__ == "__main__":
    main()
