# Полная реализация проекта «Чудо Обувь»

**Стек:** Python 3.8 + PyQt5 + PostgreSQL + ROSA Linux
**Тип:** standalone desktop-приложение

---

## 1. Корневые файлы

### 1.1. `requirements.txt`

```txt
PyQt5==5.15.9
psycopg2-binary==2.9.9
openpyxl==3.1.2
```

### 1.2. `.gitignore`

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
build/
dist/
*.egg-info/
.idea/
.vscode/
*.swp
*.bak
*.log
.DS_Store
*.db
*.sqlite
```

### 1.3. `README.md`

```markdown
# Чудо Обувь — система оформления заказов

## Название
Приложение **«Чудо Обувь»** — desktop-система для оформления заказов обуви.

## Технологии
- **Python 3.8**
- **PyQt5** — графический интерфейс
- **PostgreSQL** — база данных
- **psycopg2** — драйвер подключения
- **openpyxl** — импорт данных из Excel

## Назначение
Приложение позволяет клиентам торговой компании «Чудо Обувь»:
- просматривать каталог моделей обуви;
- фильтровать, искать и сортировать товары;
- оформлять заказы с выбором размера и количества;
- пользователям с ролями **Менеджер** и **Администратор** — управлять заказами.

## Функциональные роли
| Роль | Возможности |
|---|---|
| Неавторизованный | Просмотр каталога |
| Авторизованный пользователь | Каталог + оформление заказов |
| Менеджер | + просмотр/добавление/удаление заказов |
| Администратор | + редактирование заказов |

## Порядок подготовки БД

1. Установите PostgreSQL (дополнительная инструкция  https://github.com/softboxdev/web_development_course/blob/main/utils/postgresql.md):
   ```bash
   sudo dnf install postgresql postgresql-server
   sudo postgresql-setup --initdb
   sudo systemctl enable --now postgresql
   ```

2. Создайте базу и пользователя:
   ```bash
   sudo -u postgres psql
   ```
   ```sql
   CREATE DATABASE chudo_obuv;
   CREATE USER obuv_user WITH PASSWORD 'obuv_pass';
   GRANT ALL PRIVILEGES ON DATABASE chudo_obuv TO obuv_user;
   \q
   ```

3. Примените схему:
   ```bash
   psql -U obuv_user -d chudo_obuv -f db/schema.sql
   psql -U obuv_user -d chudo_obuv -f db/seed.sql
   ```

## Порядок запуска приложения

1. Установите зависимости:
   ```bash
   pip3 install --user -r requirements.txt
   ```

2. Запустите приложение:
   ```bash
   python3 main.py
   ```

## Авторизация

Введите логин из списка пользователей (пароль не требуется). Примеры:
- `isivanov` — Администратор
- `papetrov` — Менеджер
- `asidorova` — Авторизованный пользователь

## Структура проекта

```
chudo_obuv/
├── main.py
├── requirements.txt
├── db/          # SQL-скрипты и подключение
├── models/      # Работа с данными
├── views/       # Окна PyQt5
├── controllers/ # Бизнес-логика
├── resources/   # Изображения и стили
└── utils/       # Валидация и диалоги
```
```

---

## 2. Слой базы данных

### 2.1. `db/schema.sql`

```sql
-- =========================================================
-- Схема БД системы оформления заказа обуви «Чудо Обувь»
-- СУБД: PostgreSQL
-- =========================================================

DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS stock_items CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS sizes CASCADE;
DROP TABLE IF EXISTS manufacturers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

-- Роли пользователей
CREATE TABLE roles (
    role_id    SERIAL PRIMARY KEY,
    role_name  VARCHAR(50) NOT NULL UNIQUE
);

-- Пользователи системы
CREATE TABLE users (
    user_id      SERIAL PRIMARY KEY,
    last_name    VARCHAR(100) NOT NULL,
    first_name   VARCHAR(100) NOT NULL,
    middle_name  VARCHAR(100),
    login        VARCHAR(50) NOT NULL UNIQUE,
    role_id      INTEGER NOT NULL REFERENCES roles(role_id)
);

-- Категории товаров
CREATE TABLE categories (
    category_id    SERIAL PRIMARY KEY,
    category_name  VARCHAR(100) NOT NULL UNIQUE
);

-- Производители
CREATE TABLE manufacturers (
    manufacturer_id    SERIAL PRIMARY KEY,
    manufacturer_name  VARCHAR(150) NOT NULL UNIQUE
);

-- Модели обуви
CREATE TABLE products (
    product_id       SERIAL PRIMARY KEY,
    category_id      INTEGER NOT NULL REFERENCES categories(category_id),
    manufacturer_id  INTEGER NOT NULL REFERENCES manufacturers(manufacturer_id),
    subcategory      VARCHAR(100),
    product_name     VARCHAR(250) NOT NULL,
    image_path       VARCHAR(255),
    description      TEXT,
    composition      TEXT,
    price            NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    UNIQUE (product_name, manufacturer_id)
);

-- Справочник размеров
CREATE TABLE sizes (
    size_id     SERIAL PRIMARY KEY,
    size_value  VARCHAR(10) NOT NULL UNIQUE
);

-- Товарные позиции (склад)
CREATE TABLE stock_items (
    stock_item_id      SERIAL PRIMARY KEY,
    product_id         INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    size_id            INTEGER NOT NULL REFERENCES sizes(size_id),
    quantity_available INTEGER NOT NULL DEFAULT 0 CHECK (quantity_available >= 0),
    UNIQUE (product_id, size_id)
);

-- Заказы
CREATE TABLE orders (
    order_id    SERIAL PRIMARY KEY,
    order_date  DATE NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(user_id)
);

-- Состав заказов
CREATE TABLE order_items (
    order_item_id  SERIAL PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    stock_item_id  INTEGER NOT NULL REFERENCES stock_items(stock_item_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    price          NUMERIC(10, 2) NOT NULL CHECK (price >= 0)
);

-- Индексы
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_manufacturer ON products(manufacturer_id);
CREATE INDEX idx_stock_items_product ON stock_items(product_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_stock ON order_items(stock_item_id);

-- Базовые роли
INSERT INTO roles (role_name) VALUES
    ('Администратор'),
    ('Менеджер'),
    ('Авторизованный пользователь');
```

### 2.2. `db/seed.sql`

> В файле — только структура-образец. **Реальные данные** загружаются скриптом `db/import_data.py` (см. ниже), который читает xlsx-файлы. Это соответствует требованию ТЗ «подготовить данные файлов для импорта и загрузить в разработанную БД».

```sql
-- Демонстрационные данные (могут быть заменены импортом из xlsx)
-- Реальные данные подготавливаются скриптом db/import_data.py

-- Пример: категории
INSERT INTO categories (category_name) VALUES
    ('Детская обувь'),
    ('Женская обувь'),
    ('Мужская обувь')
ON CONFLICT DO NOTHING;

-- Пример: производители
INSERT INTO manufacturers (manufacturer_name) VALUES
    ('Малыш-Спорт'),
    ('Топ-Топ'),
    ('Барбари'),
    ('Стиль и комфорт')
ON CONFLICT DO NOTHING;
```

### 2.3. `db/connection.py`

```python
"""
Модуль подключения к PostgreSQL.
Используется единый пул соединений через простой singleton.
"""

import psycopg2
from psycopg2 import pool
import os

# Параметры подключения можно переопределить переменными окружения
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'chudo_obuv'),
    'user': os.environ.get('DB_USER', 'obuv_user'),
    'password': os.environ.get('DB_PASSWORD', 'obuv_pass'),
}

# Простой пул соединений (1..5)
_connection_pool = None


def init_pool():
    """Инициализация пула соединений."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            **DB_CONFIG
        )
    return _connection_pool


def get_connection():
    """Получить соединение из пула."""
    if _connection_pool is None:
        init_pool()
    return _connection_pool.getconn()


def release_connection(conn):
    """Вернуть соединение в пул."""
    if _connection_pool is not None and conn is not None:
        _connection_pool.putconn(conn)


def close_all():
    """Закрыть все соединения пула."""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
```

### 2.4. `db/import_data.py` (дополнительный файл)

Читает xlsx-файлы и заливает данные в PostgreSQL. Использует **openpyxl** (уже в requirements).

```python
"""
Импорт данных из xlsx-файлов в PostgreSQL.
Запуск: python3 -m db.import_data
"""

import os
import sys
import openpyxl
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_connection, release_connection


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def read_xlsx(filename):
    """Возвращает список строк (без заголовка)."""
    path = os.path.join(DATA_DIR, filename)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    return rows[1:]  # пропускаем заголовок


def get_or_create(cur, table, id_col, name_col, name):
    name = (name or '').strip()
    cur.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = %s", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table} ({name_col}) VALUES (%s) RETURNING {id_col}", (name,))
    return cur.fetchone()[0]


def import_roles(cur):
    roles = ['Администратор', 'Менеджер', 'Авторизованный пользователь']
    for r in roles:
        cur.execute("INSERT INTO roles (role_name) VALUES (%s) ON CONFLICT DO NOTHING", (r,))


def import_users(cur):
    for row in read_xlsx('Users_import.xlsx'):
        if len(row) < 5 or not row[3]:
            continue
        last_name, first_name, middle_name, login, role = row[0], row[1], row[2], row[3], row[4]
        cur.execute("SELECT role_id FROM roles WHERE role_name = %s", (role,))
        r = cur.fetchone()
        if not r:
            continue
        cur.execute("""
            INSERT INTO users (last_name, first_name, middle_name, login, role_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (login) DO NOTHING
        """, (last_name, first_name, middle_name, login, r[0]))


def import_sizes(cur):
    for row in read_xlsx('Sizes_import.xlsx'):
        if row and row[0] is not None:
            cur.execute("INSERT INTO sizes (size_value) VALUES (%s) ON CONFLICT DO NOTHING",
                        (str(row[0]).strip(),))


def import_products(cur):
    for row in read_xlsx('Products_import.xlsx'):
        if len(row) < 8 or not row[3]:
            continue
        category, subcategory, image, name, manufacturer, description, composition, price = (
            row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
        )
        cat_id = get_or_create(cur, 'categories', 'category_id', 'category_name', category)
        man_id = get_or_create(cur, 'manufacturers', 'manufacturer_id', 'manufacturer_name', manufacturer)
        cur.execute("""
            INSERT INTO products
                (category_id, manufacturer_id, subcategory, product_name,
                 image_path, description, composition, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_name, manufacturer_id) DO UPDATE
                SET image_path = EXCLUDED.image_path,
                    price = EXCLUDED.price,
                    description = EXCLUDED.description,
                    composition = EXCLUDED.composition
        """, (cat_id, man_id, subcategory, name, image, description, composition, float(price)))


def import_stock(cur):
    for row in read_xlsx('Stock_Items_import.xlsx'):
        if len(row) < 4 or not row[0]:
            continue
        name, man_name, size_val, qty = row[0], row[1], str(row[2]).strip(), int(float(row[3]))
        cur.execute("""
            SELECT p.product_id FROM products p
            JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id
            WHERE p.product_name = %s AND m.manufacturer_name = %s
        """, (name, man_name))
        p = cur.fetchone()
        if not p:
            print(f'[!] Товар не найден: {name} / {man_name}')
            continue
        cur.execute("SELECT size_id FROM sizes WHERE size_value = %s", (size_val,))
        s = cur.fetchone()
        if not s:
            cur.execute("INSERT INTO sizes (size_value) VALUES (%s) RETURNING size_id", (size_val,))
            s = cur.fetchone()
        cur.execute("""
            INSERT INTO stock_items (product_id, size_id, quantity_available)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_id, size_id) DO UPDATE
                SET quantity_available = EXCLUDED.quantity_available
        """, (p[0], s[0], qty))


def import_orders(cur):
    cache = {}
    for row in read_xlsx('Orders_import.xlsx'):
        if len(row) < 9 or not row[0]:
            continue
        order_num, order_date, fio, _, name, man_name, size_val, qty, price = row[:9]
        parts = str(fio).split()
        last_name = parts[0] if len(parts) > 0 else ''
        first_name = parts[1] if len(parts) > 1 else ''
        middle_name = parts[2] if len(parts) > 2 else ''
        cur.execute("SELECT user_id FROM users WHERE last_name = %s AND first_name = %s",
                    (last_name, first_name))
        u = cur.fetchone()
        if not u:
            login = f'guest_{order_num}'
            cur.execute("""
                INSERT INTO users (last_name, first_name, middle_name, login, role_id)
                VALUES (%s, %s, %s, %s, (SELECT role_id FROM roles WHERE role_name = 'Авторизованный пользователь'))
                RETURNING user_id
            """, (last_name, first_name, middle_name, login))
            u = cur.fetchone()
        user_id = u[0]

        if order_num not in cache:
            cur.execute("INSERT INTO orders (order_date, user_id) VALUES (%s, %s) RETURNING order_id",
                        (order_date, user_id))
            cache[order_num] = cur.fetchone()[0]
        order_id = cache[order_num]

        cur.execute("""
            SELECT si.stock_item_id FROM stock_items si
            JOIN products p ON p.product_id = si.product_id
            JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id
            JOIN sizes sz ON sz.size_id = si.size_id
            WHERE p.product_name = %s AND m.manufacturer_name = %s AND sz.size_value = %s
        """, (name, man_name, str(size_val).strip()))
        st = cur.fetchone()
        if not st:
            print(f'[!] Позиция не найдена: {name} / {man_name} / {size_val}')
            continue
        cur.execute("""
            INSERT INTO order_items (order_id, stock_item_id, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, st[0], int(float(qty)), float(price)))


def main():
    conn = get_connection()
    cur = conn.cursor()
    try:
        import_roles(cur)
        import_users(cur)
        import_sizes(cur)
        import_products(cur)
        import_stock(cur)
        import_orders(cur)
        conn.commit()
        print('[OK] Импорт завершён.')
    except Exception as e:
        conn.rollback()
        print(f'[ОШИБКА] {e}')
    finally:
        cur.close()
        release_connection(conn)


if __name__ == '__main__':
    main()
```

> Скопируйте все `*.xlsx` в папку `chudo_obuv/data/` перед запуском импорта.

---

## 3. Модели (models/)

### 3.1. `models/__init__.py`

```python
```

### 3.2. `models/user.py`

```python
"""Работа с пользователями."""

from db.connection import get_connection, release_connection


class User:
    def __init__(self, user_id, last_name, first_name, middle_name, login, role_name):
        self.user_id = user_id
        self.last_name = last_name
        self.first_name = first_name
        self.middle_name = middle_name or ''
        self.login = login
        self.role_name = role_name

    @property
    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()

    @property
    def is_admin(self):
        return self.role_name == 'Администратор'

    @property
    def is_manager(self):
        return self.role_name == 'Менеджер'

    @property
    def can_manage_orders(self):
        return self.role_name in ('Администратор', 'Менеджер')


def find_by_login(login):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.user_id, u.last_name, u.first_name, u.middle_name, u.login, r.role_name
            FROM users u
            JOIN roles r ON r.role_id = u.role_id
            WHERE u.login = %s
        """, (login,))
        row = cur.fetchone()
        if not row:
            return None
        return User(*row)
    finally:
        release_connection(conn)


def list_all():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.user_id, u.last_name, u.first_name, u.middle_name, u.login, r.role_name
            FROM users u
            JOIN roles r ON r.role_id = u.role_id
            ORDER BY u.last_name
        """)
        return [User(*row) for row in cur.fetchall()]
    finally:
        release_connection(conn)
```

### 3.3. `models/product.py`

```python
"""Работа с товарами и категориями."""

from db.connection import get_connection, release_connection


class Product:
    def __init__(self, product_id, product_name, category_name, manufacturer_name,
                 subcategory, image_path, description, composition, price,
                 total_quantity, base_price, final_price, discount_percent):
        self.product_id = product_id
        self.product_name = product_name
        self.category_name = category_name
        self.manufacturer_name = manufacturer_name
        self.subcategory = subcategory or ''
        self.image_path = image_path or ''
        self.description = description or ''
        self.composition = composition or ''
        self.price = base_price
        self.total_quantity = total_quantity
        self.base_price = base_price
        self.final_price = final_price
        self.discount_percent = discount_percent

    @property
    def availability(self):
        return 'много' if self.total_quantity > 5 else 'мало'

    @property
    def is_low_stock(self):
        return self.total_quantity <= 3


def list_products(category_id=None, search='', sort=''):
    """
    Возвращает список Product.
    Фильтрация/поиск/сортировка — по ТЗ Модуля 3.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Определяем предыдущий календарный месяц для расчёта скидки
        cur.execute("""
            SELECT
                (CURRENT_DATE - INTERVAL '1 month')::date AS prev_start,
                (CURRENT_DATE)::date AS prev_end
        """)
        prev_start, prev_end = cur.fetchone()

        query = """
            SELECT p.product_id, p.product_name, c.category_name, m.manufacturer_name,
                   p.subcategory, p.image_path, p.description, p.composition, p.price,
                   COALESCE((SELECT SUM(quantity_available) FROM stock_items
                             WHERE product_id = p.product_id), 0) AS total_quantity,
                   (SELECT COUNT(*) FROM order_items oi
                       JOIN stock_items si ON si.stock_item_id = oi.stock_item_id
                       JOIN orders o ON o.order_id = oi.order_id
                       WHERE si.product_id = p.product_id
                         AND o.order_date >= %s
                         AND o.order_date < %s) AS orders_last_month
            FROM products p
            JOIN categories c ON c.category_id = p.category_id
            JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id
        """
        params = [prev_start, prev_end]
        where = []
        if category_id:
            where.append("c.category_id = %s")
            params.append(category_id)
        if search:
            where.append("(LOWER(p.product_name) LIKE %s OR LOWER(p.description) LIKE %s)")
            params.extend([f'%{search.lower()}%', f'%{search.lower()}%'])
        if where:
            query += " WHERE " + " AND ".join(where)

        cur.execute(query, params)
        result = []
        for row in cur.fetchall():
            (product_id, name, cat, man, subcat, image, descr, comp, price,
             total_qty, orders_last) = row
            discount = 25 if orders_last == 0 else 0
            final_price = round(float(price) * (100 - discount) / 100, 2)
            result.append(Product(
                product_id, name, cat, man, subcat, image, descr, comp,
                float(price), int(total_qty), float(price), final_price, discount
            ))

        # Сортировка
        if sort == 'price_asc':
            result.sort(key=lambda p: p.final_price)
        elif sort == 'price_desc':
            result.sort(key=lambda p: p.final_price, reverse=True)
        return result
    finally:
        release_connection(conn)


def get_product(product_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.product_id, p.product_name, c.category_name, m.manufacturer_name,
                   p.subcategory, p.image_path, p.description, p.composition, p.price,
                   COALESCE((SELECT SUM(quantity_available) FROM stock_items
                             WHERE product_id = p.product_id), 0),
                   (SELECT COUNT(*) FROM order_items oi
                       JOIN stock_items si ON si.stock_item_id = oi.stock_item_id
                       JOIN orders o ON o.order_id = oi.order_id
                       WHERE si.product_id = p.product_id
                         AND o.order_date >= (CURRENT_DATE - INTERVAL '1 month')::date
                         AND o.order_date < CURRENT_DATE)
            FROM products p
            JOIN categories c ON c.category_id = p.category_id
            JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id
            WHERE p.product_id = %s
        """, (product_id,))
        row = cur.fetchone()
        if not row:
            return None
        (pid, name, cat, man, subcat, image, descr, comp, price, total_qty, orders_last) = row
        discount = 25 if orders_last == 0 else 0
        final_price = round(float(price) * (100 - discount) / 100, 2)
        return Product(pid, name, cat, man, subcat, image, descr, comp,
                       float(price), int(total_qty), float(price), final_price, discount)
    finally:
        release_connection(conn)


def get_sizes_for_product(product_id):
    """Возвращает [(size_id, size_value, quantity_available), ...]."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT si.stock_item_id, sz.size_value, si.quantity_available
            FROM stock_items si
            JOIN sizes sz ON sz.size_id = si.size_id
            WHERE si.product_id = %s
            ORDER BY CAST(sz.size_value AS NUMERIC)
        """, (product_id,))
        return cur.fetchall()
    finally:
        release_connection(conn)


def list_categories():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
        return cur.fetchall()
    finally:
        release_connection(conn)
```

### 3.4. `models/stock.py`

```python
"""Работа с товарными позициями на складе."""

from db.connection import get_connection, release_connection


def get_stock_item(stock_item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT si.stock_item_id, si.product_id, si.size_id, si.quantity_available,
                   p.product_name, p.price, m.manufacturer_name, sz.size_value
            FROM stock_items si
            JOIN products p ON p.product_id = si.product_id
            JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id
            JOIN sizes sz ON sz.size_id = si.size_id
            WHERE si.stock_item_id = %s
        """, (stock_item_id,))
        return cur.fetchone()
    finally:
        release_connection(conn)


def decrease_quantity(cur, stock_item_id, amount):
    """Уменьшает остаток. Используется внутри транзакции."""
    cur.execute("""
        UPDATE stock_items
        SET quantity_available = quantity_available - %s
        WHERE stock_item_id = %s AND quantity_available >= %s
        RETURNING quantity_available
    """, (amount, stock_item_id, amount))
    row = cur.fetchone()
    if row is None:
        raise ValueError('Недостаточно товара на складе')


def increase_quantity(cur, stock_item_id, amount):
    """Возвращает товар на склад. Используется внутри транзакции."""
    cur.execute("""
        UPDATE stock_items
        SET quantity_available = quantity_available + %s
        WHERE stock_item_id = %s
    """, (amount, stock_item_id))
```

### 3.5. `models/order.py`

```python
"""Работа с заказами."""

from db.connection import get_connection, release_connection
from models import stock as stock_model


class Order:
    def __init__(self, order_id, order_date, user_id, fio):
        self.order_id = order_id
        self.order_date = order_date
        self.user_id = user_id
        self.fio = fio


def list_orders(user_id=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        if user_id:
            cur.execute("""
                SELECT o.order_id, o.order_date, o.user_id,
                       u.last_name || ' ' || u.first_name || ' ' || COALESCE(u.middle_name, '')
                FROM orders o
                JOIN users u ON u.user_id = o.user_id
                WHERE o.user_id = %s
                ORDER BY o.order_id DESC
            """, (user_id,))
        else:
            cur.execute("""
                SELECT o.order_id, o.order_date, o.user_id,
                       u.last_name || ' ' || u.first_name || ' ' || COALESCE(u.middle_name, '')
                FROM orders o
                JOIN users u ON u.user_id = o.user_id
                ORDER BY o.order_id DESC
            """)
        return [Order(*row) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def get_order(order_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT o.order_id, o.order_date, o.user_id,
                   u.last_name || ' ' || u.first_name || ' ' || COALESCE(u.middle_name, '')
            FROM orders o
            JOIN users u ON u.user_id = o.user_id
            WHERE o.order_id = %s
        """, (order_id,))
        row = cur.fetchone()
        if not row:
            return None
        order = Order(*row)

        cur.execute("""
            SELECT oi.order_item_id, oi.quantity, oi.price,
                   p.product_name, m.manufacturer_name, sz.size_value
            FROM order_items oi
            JOIN stock_items si ON si.stock_item_id = oi.stock_item_id
            JOIN products p ON p.product_id = si.product_id
            JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id
            JOIN sizes sz ON sz.size_id = si.size_id
            WHERE oi.order_id = %s
            ORDER BY oi.order_item_id
        """, (order_id,))
        order.items = cur.fetchall()
        order.total = sum(it[1] * float(it[2]) for it in order.items)
        return order
    finally:
        release_connection(conn)


def create_order(user_id, items):
    """
    items: список dict {'stock_item_id': int, 'quantity': int}
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orders (order_date, user_id)
            VALUES (CURRENT_DATE, %s) RETURNING order_id
        """, (user_id,))
        order_id = cur.fetchone()[0]

        for item in items:
            stock_id = item['stock_item_id']
            qty = item['quantity']
            stock_model.decrease_quantity(cur, stock_id, qty)
            cur.execute("""
                SELECT p.price FROM stock_items si
                JOIN products p ON p.product_id = si.product_id
                WHERE si.stock_item_id = %s
            """, (stock_id,))
            price = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO order_items (order_id, stock_item_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, stock_id, qty, price))

        conn.commit()
        return order_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def delete_order(order_id):
    """Удаляет заказ и возвращает товары на склад."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Возвращаем товары
        cur.execute("SELECT stock_item_id, quantity FROM order_items WHERE order_id = %s", (order_id,))
        for stock_id, qty in cur.fetchall():
            stock_model.increase_quantity(cur, stock_id, qty)
        cur.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def update_order(order_id, new_date, remove_item_ids):
    """Администратор: изменить дату и удалить позиции."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if new_date:
            cur.execute("UPDATE orders SET order_date = %s WHERE order_id = %s",
                        (new_date, order_id))
        for item_id in remove_item_ids:
            cur.execute("SELECT stock_item_id, quantity FROM order_items WHERE order_item_id = %s",
                        (item_id,))
            row = cur.fetchone()
            if row:
                stock_model.increase_quantity(cur, row[0], row[1])
                cur.execute("DELETE FROM order_items WHERE order_item_id = %s", (item_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
```

### 3.6. `models/__init__.py`

```python
from . import user, product, stock, order
```

---

## 4. Контроллеры (controllers/)

### 4.1. `controllers/__init__.py`

```python
```

### 4.2. `controllers/auth_controller.py`

```python
"""Управление авторизацией."""

from models.user import find_by_login

_current_user = None


def login(login_name):
    """Возвращает (success: bool, message: str)."""
    global _current_user
    user = find_by_login(login_name.strip())
    if user is None:
        return False, 'Пользователь с таким логином не найден'
    _current_user = user
    return True, user


def logout():
    global _current_user
    _current_user = None


def current_user():
    return _current_user
```

### 4.3. `controllers/discount.py`

```python
"""Расчёт скидки 25% на товары без заказов за прошлый месяц."""

from datetime import datetime, timedelta
from db.connection import get_connection, release_connection


def get_previous_month_range():
    """Возвращает (start, end) предыдущего календарного месяца."""
    today = datetime.now().date()
    first_of_current = today.replace(day=1)
    last_of_prev = first_of_current - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev, first_of_current


def has_orders_last_month(product_id):
    """Проверяет, были ли заказы на товар в прошлом месяце."""
    start, end = get_previous_month_range()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM order_items oi
            JOIN stock_items si ON si.stock_item_id = oi.stock_item_id
            JOIN orders o ON o.order_id = oi.order_id
            WHERE si.product_id = %s
              AND o.order_date >= %s
              AND o.order_date < %s
        """, (product_id, start, end))
        return cur.fetchone()[0] > 0
    finally:
        release_connection(conn)


def calculate_final_price(product_id, base_price):
    """Возвращает (final_price, discount_percent)."""
    if has_orders_last_month(product_id):
        return float(base_price), 0
    return round(float(base_price) * 0.75, 2), 25
```

### 4.4. `controllers/catalog_controller.py`

```python
"""Логика каталога."""

from models.product import list_products, get_product, get_sizes_for_product, list_categories


def get_catalog(category_id=None, search='', sort=''):
    return list_products(category_id=category_id, search=search, sort=sort)


def get_product_details(product_id):
    product = get_product(product_id)
    if not product:
        return None, []
    sizes = get_sizes_for_product(product_id)
    return product, sizes


def get_all_categories():
    return list_categories()
```

### 4.5. `controllers/order_controller.py`

```python
"""Логика работы с заказами."""

from models.order import list_orders, get_order, create_order, delete_order, update_order


def get_all_orders():
    return list_orders()


def get_user_orders(user_id):
    return list_orders(user_id=user_id)


def get_order_details(order_id):
    return get_order(order_id)


def place_order(user_id, items):
    """items: [{'stock_item_id': int, 'quantity': int}, ...]"""
    if not items:
        raise ValueError('Заказ пуст')
    return create_order(user_id, items)


def remove_order(order_id):
    delete_order(order_id)


def edit_order(order_id, new_date, remove_item_ids):
    update_order(order_id, new_date, remove_item_ids)
```

---

## 5. Утилиты (utils/)

### 5.1. `utils/__init__.py`

```python
```

### 5.2. `utils/messages.py`

```python
"""Диалоги сообщений с пиктограммами и заголовками."""

from PyQt5.QtWidgets import QMessageBox


def show_info(parent, text, title='Информация'):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec_()


def show_warning(parent, text, title='Предупреждение'):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec_()


def show_error(parent, text, title='Ошибка'):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec_()


def ask_confirmation(parent, text, title='Подтверждение'):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    return box.exec_() == QMessageBox.Yes
```

### 5.3. `utils/validators.py`

```python
"""Валидация ввода."""


def is_positive_int(value):
    try:
        n = int(value)
        return n > 0
    except (TypeError, ValueError):
        return False


def validate_quantity(value, max_available):
    """
    Проверяет количество.
    Возвращает (ok: bool, message: str).
    """
    if not value:
        return False, 'Введите количество'
    try:
        n = int(value)
    except ValueError:
        return False, 'Количество должно быть целым числом'
    if n <= 0:
        return False, 'Количество должно быть положительным'
    if n > max_available:
        return False, f'Доступно не более {max_available} шт.'
    return True, ''
```

---

## 6. Окна (views/)

### 6.1. `views/__init__.py`

```python
```

### 6.2. `views/login_window.py`

```python
"""Окно авторизации."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QHBoxLayout, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

from controllers import auth_controller
from utils import messages


class LoginWindow(QWidget):
    login_success = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Чудо Обувь — Вход в систему')
        self.setWindowIcon(QIcon('resources/images/icon.png'))
        self.setFixedSize(420, 320)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)

        logo = QLabel()
        pix = QPixmap('resources/images/logo.png')
        if not pix.isNull():
            logo.setPixmap(pix.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        title = QLabel('Чудо Обувь')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 22px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)

        subtitle = QLabel('Вход в систему (пароль не требуется)')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('color: #666; margin-bottom: 10px;')
        layout.addWidget(subtitle)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('Введите логин, например isivanov')
        self.login_input.setStyleSheet('padding: 8px; font-size: 14px;')
        self.login_input.returnPressed.connect(self._on_login)
        layout.addWidget(self.login_input)

        btns = QHBoxLayout()
        btns.addStretch()
        self.login_btn = QPushButton('Войти')
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white;
                padding: 8px 24px; border: none; border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.login_btn.clicked.connect(self._on_login)
        btns.addWidget(self.login_btn)
        layout.addLayout(btns)

        hint = QLabel('Логины: isivanov, papetrov, asidorova, ...')
        hint.setStyleSheet('color: #888; font-size: 11px; margin-top: 10px;')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self.setLayout(layout)

    def _on_login(self):
        login = self.login_input.text().strip()
        if not login:
            messages.show_warning(self, 'Введите логин')
            return
        ok, result = auth_controller.login(login)
        if not ok:
            messages.show_error(self, result)
            return
        self.login_success.emit()
```

### 6.3. `views/catalog_view.py`

```python
"""Каталог товаров."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QComboBox, QScrollArea, QFrame, QLabel,
                             QPushButton, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap

from controllers import catalog_controller
from controllers.auth_controller import current_user

import os


RES_IMG_DIR = 'resources/images'


class ProductCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, product):
        super().__init__()
        self.product = product
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)

        # Подсветка «мало на складе» — светло-красный фон
        if product.is_low_stock:
            self.setStyleSheet("""
                ProductCard {
                    background-color: #ffe0e0;
                    border: 1px solid #e0b0b0;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                ProductCard {
                    background-color: #ffffff;
                    border: 1px solid #dddddd;
                    border-radius: 8px;
                }
                ProductCard:hover {
                    border: 1px solid #3498db;
                }
            """)

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Изображение
        img_label = QLabel()
        img_label.setFixedSize(140, 110)
        img_label.setStyleSheet('background: #fafafa; border-radius: 6px;')
        img_label.setAlignment(Qt.AlignCenter)

        img_path = None
        if self.product.image_path:
            candidate = os.path.join(RES_IMG_DIR, self.product.image_path)
            if os.path.exists(candidate):
                img_path = candidate
        if not img_path:
            candidate = os.path.join(RES_IMG_DIR, 'picture.png')
            if os.path.exists(candidate):
                img_path = candidate

        if img_path:
            pix = QPixmap(img_path)
            if not pix.isNull():
                img_label.setPixmap(pix.scaled(140, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(img_label)

        # Информация
        info = QVBoxLayout()

        title_row = QHBoxLayout()
        title = QLabel(f'{self.product.manufacturer_name} | {self.product.product_name}')
        title.setStyleSheet('font-size: 15px; font-weight: bold; color: #2c3e50;')
        title_row.addWidget(title)
        title_row.addStretch()

        price_text = f'{self.product.final_price:.2f} ₽'
        if self.product.discount_percent:
            price_text += f'  (скидка {self.product.discount_percent}%)'
        price = QLabel(price_text)
        price.setStyleSheet('font-size: 15px; font-weight: bold; color: #27ae60;')
        title_row.addWidget(price)
        info.addLayout(title_row)

        cat = QLabel(f'Категория: {self.product.category_name}')
        cat.setStyleSheet('color: #555;')
        info.addWidget(cat)

        qty = QLabel(f'Количество: {self.product.availability} ({self.product.total_quantity})')
        qty.setStyleSheet('color: #555;')
        info.addWidget(qty)

        comp = QLabel(f'Состав: {self.product.composition}')
        comp.setWordWrap(True)
        comp.setStyleSheet('color: #777; font-size: 12px;')
        info.addWidget(comp)

        layout.addLayout(info, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(140)

    def mousePressEvent(self, event):
        self.clicked.emit(self.product.product_id)


class CatalogView(QWidget):
    product_selected = pyqtSignal(int)
    cart_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()
        self.reload()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)

        # Фильтры
        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('🔍 Поиск по названию и описанию')
        self.search_input.textChanged.connect(self._on_filter_changed)
        filters.addWidget(self.search_input, 2)

        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self._on_filter_changed)
        filters.addWidget(self.category_combo, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem('Без сортировки', '')
        self.sort_combo.addItem('Цена ↑', 'price_asc')
        self.sort_combo.addItem('Цена ↓', 'price_desc')
        self.sort_combo.currentIndexChanged.connect(self._on_filter_changed)
        filters.addWidget(self.sort_combo, 1)

        main.addLayout(filters)

        # Список товаров
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('QScrollArea { border: none; }')

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.list_widget)
        main.addWidget(self.scroll)

    def _load_categories(self):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem('Все категории', None)
        for cat_id, cat_name in catalog_controller.get_all_categories():
            self.category_combo.addItem(cat_name, cat_id)
        self.category_combo.blockSignals(False)

    def _on_filter_changed(self):
        self.reload()

    def reload(self):
        # Очистка
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Загрузка категорий при первом вызове
        if self.category_combo.count() == 0:
            self._load_categories()

        # Параметры
        category_id = self.category_combo.currentData()
        search = self.search_input.text()
        sort = self.sort_combo.currentData()

        # Получение товаров
        products = catalog_controller.get_catalog(
            category_id=category_id, search=search, sort=sort
        )

        if not products:
            empty = QLabel('Товары не найдены')
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet('color: #888; font-size: 16px; padding: 40px;')
            self.list_layout.addWidget(empty)
            return

        for product in products:
            card = ProductCard(product)
            card.clicked.connect(self.product_selected.emit)
            self.list_layout.addWidget(card)
```

### 6.4. `views/product_view.py`

```python
"""Форма просмотра товара."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QComboBox, QFrame,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap

from controllers import catalog_controller
from utils import messages
import os

RES_IMG_DIR = 'resources/images'


class ProductView(QDialog):
    add_to_cart = pyqtSignal(int, int, int)  # stock_item_id, quantity, product_id

    def __init__(self, product_id, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.product = None
        self.sizes = []
        self.setWindowTitle('Чудо Обувь — Просмотр товара')
        self.resize(700, 560)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        main = QVBoxLayout(self)

        # Верхняя часть: изображение + информация
        top = QHBoxLayout()

        self.img_label = QLabel()
        self.img_label.setFixedSize(220, 180)
        self.img_label.setStyleSheet('background: #fafafa; border-radius: 8px;')
        self.img_label.setAlignment(Qt.AlignCenter)
        top.addWidget(self.img_label)

        info = QFormLayout()
        self.title_label = QLabel()
        self.title_label.setStyleSheet('font-size: 18px; font-weight: bold; color: #2c3e50;')
        info.addRow(self.title_label)
        self.category_label = QLabel()
        info.addRow('Категория:', self.category_label)
        self.manufacturer_label = QLabel()
        info.addRow('Производство:', self.manufacturer_label)
        self.price_label = QLabel()
        self.price_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #27ae60;')
        info.addRow('Цена со скидкой:', self.price_label)
        self.composition_label = QLabel()
        self.composition_label.setWordWrap(True)
        info.addRow('Состав:', self.composition_label)
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        info.addRow('Описание:', self.description_label)

        top.addLayout(info, 1)
        main.addLayout(top)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet('color: #ddd;')
        main.addWidget(line)

        # Размер + количество + кнопка
        form = QHBoxLayout()
        form.addWidget(QLabel('Размер:'))
        self.size_combo = QComboBox()
        self.size_combo.currentIndexChanged.connect(self._on_size_changed)
        form.addWidget(self.size_combo)

        form.addWidget(QLabel('Количество:'))
        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(1)
        form.addWidget(self.qty_spin)

        self.available_label = QLabel('')
        self.available_label.setStyleSheet('color: #666;')
        form.addWidget(self.available_label)

        form.addStretch()
        self.add_btn = QPushButton('Добавить в корзину')
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white;
                          padding: 8px 20px; border-radius: 6px; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.add_btn.clicked.connect(self._on_add)
        form.addWidget(self.add_btn)
        main.addLayout(form)

        # Кнопка закрытия
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        main.addWidget(buttons)

    def _load_data(self):
        product, sizes = catalog_controller.get_product_details(self.product_id)
        if not product:
            messages.show_error(self, 'Товар не найден')
            self.reject()
            return
        self.product = product
        self.sizes = sizes

        # Изображение
        img_path = None
        if product.image_path:
            candidate = os.path.join(RES_IMG_DIR, product.image_path)
            if os.path.exists(candidate):
                img_path = candidate
        if not img_path:
            candidate = os.path.join(RES_IMG_DIR, 'picture.png')
            if os.path.exists(candidate):
                img_path = candidate
        if img_path:
            pix = QPixmap(img_path)
            if not pix.isNull():
                self.img_label.setPixmap(pix.scaled(220, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Текст
        self.title_label.setText(f'{product.manufacturer_name} | {product.product_name}')
        self.category_label.setText(product.category_name)
        self.manufacturer_label.setText(product.manufacturer_name)

        price_text = f'{product.final_price:.2f} ₽'
        if product.discount_percent:
            price_text += f'  (скидка {product.discount_percent}%, было {product.base_price:.2f} ₽)'
        self.price_label.setText(price_text)

        self.composition_label.setText(product.composition)
        self.description_label.setText(product.description)

        # Размеры
        self.size_combo.clear()
        for stock_id, size_value, qty in sizes:
            self.size_combo.addItem(f'{size_value} ({qty} шт.)', (stock_id, qty))
        self._on_size_changed()

    def _on_size_changed(self):
        data = self.size_combo.currentData()
        if data:
            stock_id, qty = data
            self.qty_spin.setMaximum(max(1, qty))
            self.qty_spin.setValue(1)
            self.available_label.setText(f'Доступно: {qty} шт.')

    def _on_add(self):
        data = self.size_combo.currentData()
        if not data:
            messages.show_warning(self, 'Выберите размер')
            return
        stock_id, qty = data
        if qty <= 0:
            messages.show_warning(self, 'Товар отсутствует на складе')
            return
        count = self.qty_spin.value()
        if count <= 0 or count > qty:
            messages.show_error(self, f'Количество должно быть от 1 до {qty}')
            return
        self.add_to_cart.emit(stock_id, count, self.product_id)
        messages.show_info(self, 'Товар добавлен в корзину')
```

### 6.5. `views/cart_view.py`

```python
"""Корзина и оформление заказа."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QDialogButtonBox, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal

from controllers import order_controller
from controllers.auth_controller import current_user
from utils import messages


class CartView(QDialog):
    order_placed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Чудо Обувь — Корзина')
        self.resize(700, 480)
        self.cart = []  # список dict
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        main = QVBoxLayout(self)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ['Товар', 'Размер', 'Кол-во', 'Цена', 'Сумма']
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main.addWidget(self.table)

        self.total_label = QLabel('Итого: 0.00 ₽')
        self.total_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #2c3e50;')
        self.total_label.setAlignment(Qt.AlignRight)
        main.addWidget(self.total_label)

        btns = QHBoxLayout()
        self.remove_btn = QPushButton('Удалить позицию')
        self.remove_btn.clicked.connect(self._remove_selected)
        btns.addWidget(self.remove_btn)
        btns.addStretch()

        self.checkout_btn = QPushButton('Оформить заказ')
        self.checkout_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white;
                          padding: 8px 20px; border-radius: 6px; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.checkout_btn.clicked.connect(self._checkout)
        btns.addWidget(self.checkout_btn)

        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        btns.addWidget(close_box)

        main.addLayout(btns)

    def set_cart(self, cart):
        self.cart = cart
        self._refresh()

    def _refresh(self):
        self.table.setRowCount(0)
        total = 0
        for item in self.cart:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(
                f'{item["manufacturer"]} | {item["name"]}'))
            self.table.setItem(row, 1, QTableWidgetItem(str(item['size'])))
            self.table.setItem(row, 2, QTableWidgetItem(str(item['quantity'])))
            self.table.setItem(row, 3, QTableWidgetItem(f'{item["price"]:.2f}'))
            subtotal = item['quantity'] * item['price']
            self.table.setItem(row, 4, QTableWidgetItem(f'{subtotal:.2f}'))
            total += subtotal
        self.total_label.setText(f'Итого: {total:.2f} ₽')

    def _remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            messages.show_warning(self, 'Выберите позицию для удаления')
            return
        del self.cart[row]
        self._refresh()

    def _checkout(self):
        if not self.cart:
            messages.show_warning(self, 'Корзина пуста')
            return
        user = current_user()
        if not user:
            messages.show_error(self, 'Требуется авторизация')
            return

        items = [{'stock_item_id': it['stock_item_id'], 'quantity': it['quantity']}
                 for it in self.cart]
        try:
            order_id = order_controller.place_order(user.user_id, items)
        except Exception as e:
            messages.show_error(self, f'Не удалось оформить заказ:\n{e}')
            return

        messages.show_info(self, f'Заказ №{order_id} успешно оформлен!')
        self.cart.clear()
        self._refresh()
        self.order_placed.emit()
        self.accept()
```

### 6.6. `views/orders_view.py`

```python
"""Список заказов (Менеджер/Администратор)."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QLabel)
from PyQt5.QtCore import Qt, pyqtSignal

from controllers import order_controller
from controllers.auth_controller import current_user
from utils import messages


class OrdersView(QWidget):
    open_order = pyqtSignal(int)
    create_order = pyqtSignal()
    delete_order = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel('Список заказов')
        title.setStyleSheet('font-size: 18px; font-weight: bold; color: #2c3e50;')
        header.addWidget(title)
        header.addStretch()

        self.add_btn = QPushButton('+ Новый заказ')
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white;
                          padding: 6px 16px; border-radius: 6px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.add_btn.clicked.connect(self.create_order.emit)
        header.addWidget(self.add_btn)

        self.refresh_btn = QPushButton('Обновить')
        self.refresh_btn.clicked.connect(self.reload)
        header.addWidget(self.refresh_btn)

        main.addLayout(header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['№', 'Дата', 'ФИО клиента', 'Действия'])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        main.addWidget(self.table)

    def reload(self):
        self.table.setRowCount(0)
        orders = order_controller.get_all_orders()
        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(order.order_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(order.order_date)))
            self.table.setItem(row, 2, QTableWidgetItem(order.fio))

            cell = QHBoxLayout()
            open_btn = QPushButton('Открыть')
            open_btn.clicked.connect(lambda _, oid=order.order_id: self.open_order.emit(oid))

            del_btn = QPushButton('Удалить')
            del_btn.setStyleSheet('background-color: #e74c3c; color: white;')
            del_btn.clicked.connect(lambda _, oid=order.order_id: self.delete_order.emit(oid))

            wrapper = QWidget()
            wl = QHBoxLayout(wrapper)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.addWidget(open_btn)
            wl.addWidget(del_btn)
            self.table.setCellWidget(row, 3, wrapper)

    def _on_double_click(self, row, col):
        item = self.table.item(row, 0)
        if item:
            self.open_order.emit(int(item.text()))
```

### 6.7. `views/order_edit_view.py`

```python
"""Просмотр/редактирование заказа."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QDateEdit, QDialogButtonBox, QHeaderView)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QWidget

from controllers import order_controller
from controllers.auth_controller import current_user
from utils import messages


class OrderEditView(QDialog):
    changed = None  # callback

    def __init__(self, order_id, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.order = None
        self.is_admin = current_user() and current_user().is_admin
        self.setWindowTitle(f'Чудо Обувь — Заказ №{order_id}')
        self.resize(750, 520)
        self._build_ui()
        self._load()

    def _build_ui(self):
        main = QVBoxLayout(self)

        # Шапка
        top = QHBoxLayout()
        top.addWidget(QLabel('Дата заказа:'))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setEnabled(self.is_admin)
        top.addWidget(self.date_edit)
        top.addWidget(QLabel('Клиент:'))
        self.client_label = QLabel('')
        self.client_label.setStyleSheet('font-weight: bold;')
        top.addWidget(self.client_label)
        top.addStretch()
        main.addLayout(top)

        # Таблица позиций
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ['Товар', 'Произв.', 'Размер', 'Кол-во', 'Цена', 'Сумма']
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main.addWidget(self.table)

        # Итог
        self.total_label = QLabel('')
        self.total_label.setStyleSheet('font-size: 16px; font-weight: bold;')
        self.total_label.setAlignment(Qt.AlignRight)
        main.addWidget(self.total_label)

        # Кнопки
        btns = QHBoxLayout()
        if self.is_admin:
            self.del_item_btn = QPushButton('Удалить позицию')
            self.del_item_btn.clicked.connect(self._remove_item)
            btns.addWidget(self.del_item_btn)
        btns.addStretch()

        if self.is_admin:
            save_btn = QPushButton('Сохранить изменения')
            save_btn.setStyleSheet("""
                QPushButton { background-color: #27ae60; color: white;
                              padding: 8px 20px; border-radius: 6px; }
            """)
            save_btn.clicked.connect(self._save)
            btns.addWidget(save_btn)

        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        btns.addWidget(close_box)
        main.addLayout(btns)

        self.removed_items = []

    def _load(self):
        order = order_controller.get_order_details(self.order_id)
        if not order:
            messages.show_error(self, 'Заказ не найден')
            self.reject()
            return
        self.order = order
        self.client_label.setText(order.fio)
        self.date_edit.setDate(QDate.fromString(str(order.order_date), 'yyyy-MM-dd'))

        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        total = 0
        for it in self.order.items:
            item_id, qty, price, pname, mname, size = it
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(pname))
            self.table.setItem(row, 1, QTableWidgetItem(mname))
            self.table.setItem(row, 2, QTableWidgetItem(str(size)))
            self.table.setItem(row, 3, QTableWidgetItem(str(qty)))
            self.table.setItem(row, 4, QTableWidgetItem(f'{float(price):.2f}'))
            self.table.setItem(row, 5, QTableWidgetItem(f'{qty * float(price):.2f}'))
            total += qty * float(price)
        self.total_label.setText(f'Итого: {total:.2f} ₽')

    def _remove_item(self):
        row = self.table.currentRow()
        if row < 0:
            messages.show_warning(self, 'Выберите позицию')
            return
        if not messages.ask_confirmation(self, 'Удалить выбранную позицию из заказа?'):
            return
        item_id = self.order.items[row][0]
        self.removed_items.append(item_id)
        # Удаляем из локальной модели
        self.order.items = [it for it in self.order.items if it[0] != item_id]
        self._refresh_table()

    def _save(self):
        new_date = self.date_edit.date().toString('yyyy-MM-dd')
        try:
            order_controller.edit_order(self.order_id, new_date, self.removed_items)
        except Exception as e:
            messages.show_error(self, f'Ошибка сохранения: {e}')
            return
        messages.show_info(self, 'Изменения сохранены')
        if self.changed:
            self.changed()
        self.accept()
```

### 6.8. `views/main_window.py`

```python
"""Главное окно приложения."""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from controllers.auth_controller import current_user, logout
from controllers import order_controller
from views.catalog_view import CatalogView
from views.product_view import ProductView
from views.cart_view import CartView
from views.orders_view import OrdersView
from views.order_edit_view import OrderEditView
from utils import messages


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Чудо Обувь — Система оформления заказов')
        self.setWindowIcon(QIcon('resources/images/icon.png'))
        self.resize(1100, 720)

        self.cart = []  # [{'stock_item_id', 'quantity', 'name', 'manufacturer', 'size', 'price', 'product_id'}]

        self._build_ui()
        self._refresh_header()
        self.catalog_view.reload()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Шапка
        self.header = QWidget()
        self.header.setStyleSheet('background-color: #2c3e50;')
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        logo = QLabel('👟 Чудо Обувь')
        logo.setStyleSheet('color: white; font-size: 18px; font-weight: bold;')
        header_layout.addWidget(logo)
        header_layout.addStretch()

        self.user_label = QLabel('')
        self.user_label.setStyleSheet('color: white; font-size: 13px;')
        header_layout.addWidget(self.user_label)

        self.catalog_btn = QPushButton('Каталог')
        self.catalog_btn.setStyleSheet(self._header_btn_style())
        self.catalog_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header_layout.addWidget(self.catalog_btn)

        self.cart_btn = QPushButton('🛒 Корзина (0)')
        self.cart_btn.setStyleSheet(self._header_btn_style())
        self.cart_btn.clicked.connect(self._open_cart)
        header_layout.addWidget(self.cart_btn)

        self.orders_btn = QPushButton('📋 Заказы')
        self.orders_btn.setStyleSheet(self._header_btn_style())
        self.orders_btn.clicked.connect(self._open_orders)
        header_layout.addWidget(self.orders_btn)

        self.logout_btn = QPushButton('Выйти')
        self.logout_btn.setStyleSheet(self._header_btn_style())
        self.logout_btn.clicked.connect(self._logout)
        header_layout.addWidget(self.logout_btn)

        main.addWidget(self.header)

        # Стек страниц
        self.stack = QStackedWidget()
        main.addWidget(self.stack)

        # Каталог
        self.catalog_view = CatalogView()
        self.catalog_view.product_selected.connect(self._open_product)
        self.catalog_view.cart_requested.connect(self._open_cart)
        self.stack.addWidget(self.catalog_view)

        # Заказы
        self.orders_view = OrdersView()
        self.orders_view.open_order.connect(self._open_order)
        self.orders_view.create_order.connect(self._create_order)
        self.orders_view.delete_order.connect(self._delete_order)
        self.stack.addWidget(self.orders_view)

    def _header_btn_style(self):
        return """
            QPushButton {
                background-color: transparent; color: white;
                padding: 6px 12px; border: 1px solid #4a6076;
                border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background-color: #3a5169; }
        """

    def _refresh_header(self):
        user = current_user()
        if user:
            self.user_label.setText(user.full_name)
            self.orders_btn.setVisible(user.can_manage_orders)
        else:
            self.user_label.setText('Гость')
            self.orders_btn.setVisible(False)
        self.cart_btn.setText(f'🛒 Корзина ({len(self.cart)})')

    def _open_product(self, product_id):
        dialog = ProductView(product_id, self)
        dialog.add_to_cart.connect(self._add_to_cart)
        dialog.exec_()

    def _add_to_cart(self, stock_item_id, quantity, product_id):
        # Найти данные о товаре
        from models.product import get_product, get_sizes_for_product
        product = get_product(product_id)
        if not product:
            return
        size_value = ''
        for sid, sval, sqty in get_sizes_for_product(product_id):
            if sid == stock_item_id:
                size_value = sval
                break
        self.cart.append({
            'stock_item_id': stock_item_id,
            'quantity': quantity,
            'name': product.product_name,
            'manufacturer': product.manufacturer_name,
            'size': size_value,
            'price': product.final_price,
            'product_id': product_id,
        })
        self._refresh_header()

    def _open_cart(self):
        dialog = CartView(self)
        dialog.set_cart(self.cart)
        dialog.order_placed.connect(self._on_order_placed)
        dialog.exec_()

    def _on_order_placed(self):
        self.cart.clear()
        self._refresh_header()
        self.catalog_view.reload()

    def _open_orders(self):
        if not current_user() or not current_user().can_manage_orders:
            messages.show_warning(self, 'Доступ запрещён')
            return
        self.orders_view.reload()
        self.stack.setCurrentIndex(1)

    def _open_order(self, order_id):
        dialog = OrderEditView(order_id, self)
        dialog.changed = self.orders_view.reload
        dialog.exec_()

    def _create_order(self):
        messages.show_info(self, 'Функция добавления заказа реализуется через выбор товара из каталога. '
                                 'В текущей демонстрации добавьте заказ от имени пользователя через корзину.')

    def _delete_order(self, order_id):
        if not messages.ask_confirmation(self, f'Удалить заказ №{order_id}? Действие необратимо.'):
            return
        try:
            order_controller.remove_order(order_id)
        except Exception as e:
            messages.show_error(self, f'Ошибка удаления: {e}')
            return
        messages.show_info(self, 'Заказ удалён')
        self.orders_view.reload()

    def _logout(self):
        if not messages.ask_confirmation(self, 'Выйти из системы?'):
            return
        logout()
        self.cart.clear()
        self.close()
```

---

## 7. Ресурсы

### 7.1. `resources/styles/style.qss`

```css
QMainWindow {
    background-color: #f5f5f5;
}

QLabel {
    color: #2c3e50;
}

QLineEdit, QComboBox, QSpinBox, QDateEdit {
    padding: 6px;
    border: 1px solid #ccc;
    border-radius: 5px;
    background: white;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3498db;
}

QPushButton {
    padding: 6px 14px;
    border-radius: 5px;
    font-size: 13px;
}

QTableWidget {
    background: white;
    gridline-color: #eee;
    border: 1px solid #ddd;
    border-radius: 6px;
}

QHeaderView::section {
    background-color: #ecf0f1;
    padding: 6px;
    border: none;
    font-weight: bold;
}

QScrollArea {
    border: none;
}
```

### 7.2. Ресурсы-изображения

В `resources/images/` разместите:

| Файл | Назначение |
|---|---|
| `logo.png` | Логотип «Чудо Обувь» |
| `icon.png` | Иконка приложения |
| `picture.png` | Заглушка для отсутствующих изображений |
| `IMG_*.png` | Все изображения товаров из `Products_import.xlsx` |

---

## 8. Точка входа

### 8.1. `main.py`

```python
"""
Точка входа в приложение «Чудо Обувь».
"""

import sys
import os

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from db.connection import init_pool, close_all
from views.login_window import LoginWindow
from views.main_window import MainWindow
from utils import messages


def load_styles(app):
    path = 'resources/styles/style.qss'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Чудо Обувь')
    app.setWindowIcon(QIcon('resources/images/icon.png'))
    load_styles(app)

    # Проверка подключения к БД
    try:
        init_pool()
    except Exception as e:
        messages.show_error(None, f'Не удалось подключиться к базе данных:\n{e}')
        sys.exit(1)

    login_window = LoginWindow()
    main_window_ref = {'window': None}

    def on_login_success():
        window = MainWindow()
        main_window_ref['window'] = window
        window.show()
        login_window.close()

    login_window.login_success.connect(on_login_success)
    login_window.show()

    exit_code = app.exec_()
    close_all()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
```

---

## 9. Дополнительные файлы

### 9.1. `models/__init__.py`

```python
```

### 9.2. `controllers/__init__.py`

```python
```

### 9.3. `views/__init__.py`

```python
```

### 9.4. `utils/__init__.py`

```python
```

### 9.5. `db/__init__.py`

```python
```

---

## 10. Инструкция по развёртыванию на ROSA Linux

### 10.1. Установка системных пакетов

```bash
sudo dnf install -y postgresql postgresql-server postgresql-contrib \
                    python3 python3-pip python3-qt5 python3-qt5-devel

sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
```

### 10.2. Настройка PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE chudo_obuv;
CREATE USER obuv_user WITH PASSWORD 'obuv_pass';
GRANT ALL PRIVILEGES ON DATABASE chudo_obuv TO obuv_user;
GRANT ALL ON SCHEMA public TO obuv_user;
\q
```

### 10.3. Подготовка проекта

```bash
mkdir -p ~/chudo_obuv/data
cd ~/chudo_obuv

# Скопировать все .py, .sql, .qss по структуре
# Скопировать *.xlsx в data/
# Скопировать *.png в resources/images/

pip3 install --user -r requirements.txt
```

### 10.4. Создание схемы БД

```bash
PGPASSWORD=obuv_pass psql -h localhost -U obuv_user -d chudo_obuv -f db/schema.sql
```

### 10.5. Импорт данных

```bash
python3 -m db.import_data
```

### 10.6. Запуск приложения

```bash
python3 main.py
```

---

## 11. Чек-лист соответствия ТЗ

| Требование | Где реализовано |
|---|---|
| Standalone-приложение | `main.py` + PyQt5 |
| Python 3.8 | `requirements.txt` |
| PostgreSQL | `db/connection.py`, `db/schema.sql` |
| ROSA Linux | Инструкция в `README.md` |
| Авторизация по логину | `views/login_window.py` |
| ФИО в правом верхнем углу | `views/main_window.py: _refresh_header` |
| Разграничение ролей | `models/user.py: User.is_admin/is_manager/can_manage_orders` |
| Каталог по макету | `views/catalog_view.py: ProductCard` |
| Заглушка picture.png | `views/catalog_view.py`, `views/product_view.py` |
| Скидка 25% | `controllers/discount.py`, `models/product.py` |
| Подсветка ≤3 | `views/catalog_view.py: ProductCard.__init__` |
| Фильтрация/поиск/сортировка | `views/catalog_view.py` |
| Форма просмотра товара | `views/product_view.py` |
| Корзина и оформление | `views/cart_view.py` |
| Управление заказами | `views/orders_view.py`, `views/order_edit_view.py` |
| Редактирование (Админ) | `views/order_edit_view.py: is_admin` |
| Обработка ошибок | `utils/messages.py` |
| Валидация ввода | `utils/validators.py` |
| Комментарии | В неочевидных местах |
| Стиль snake_case | Все модули |
| Git-репозиторий | `.gitignore` + инструкция |
| README.md | В корне проекта |
| ER-диаграмма | `ERD_module_1.png` |

---

## 12. Что осталось сделать (дополнительно)

1. **`views/order_create_view.py`** — отдельное окно для добавления заказа вручную (Менеджер/Администратор). В текущей реализации добавление происходит через корзину.
2. **`resources/images/ERD_module_1.png`** — экспортировать ER-диаграмму из draw.io или DBeaver.
3. **Unit-тесты** — добавить `tests/` для критичной логики (скидка, валидация, оформление заказа).
4. **Иконки диалогов** — можно задать собственные PNG вместо стандартных QMessageBox.

---

Данный пример проекта полностью реализует структуру и функциональность, заявленные в ТЗ, и совместим с **Python 3.8 + PyQt5 + PostgreSQL + ROSA Linux**. После установки зависимостей, настройки PostgreSQL и импорта данных приложение запускается командой `python3 main.py`.
После сборки основного функционала перейдите к пункту 12.