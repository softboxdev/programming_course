# Практическая работа: Разработка системы оформления заказа обуви (подготовка к демо-экзамену)

**Технологии:** Python 3.8 (встроенные средства) + JavaScript (фронтенд)
**Предметная область:** Компания по продаже обуви
**Файлы-источники:** Products_import.xlsx, Stock_Items_import.xlsx, Sizes_import.xlsx, Orders_import.xlsx, Users_import.xlsx

---

## Цель работы

Разработать полноценное веб-приложение для оформления заказов обуви, включающее:
1. Проектирование и создание базы данных (SQLite, встроен в Python).
2. Импорт данных из Excel-файлов.
3. Backend на Python (http.server + sqlite3, без сторонних библиотек).
4. Frontend на чистом JavaScript (SPA-приложение).
5. Авторизацию, каталог, фильтрацию, поиск, сортировку, корзину, оформление заказов.
6. Панель администратора и менеджера.

> **Важно:** Так как требуется Python 3.8 «встроенными средствами», не используем Flask/Django/pandas/openpyxl. Для чтения Excel применим распаковку `.xlsx` через `zipfile` + `xml.etree` (xlsx — это zip с XML внутри).

---

## Часть 1. Проектирование базы данных

### 1.1. Анализ предметной области и приведение к 3НФ

Выделяем сущности:

| Сущность | Атрибуты |
|---|---|
| **Категории** | id, название |
| **Производители** | id, название |
| **Товары (модели)** | id, категория_id, производитель_id, наименование, подкатегория, описание, состав, цена, изображение |
| **Размеры** | id, значение |
| **Склад (товар+размер)** | id, товар_id, размер_id, количество |
| **Пользователи** | id, фамилия, имя, отчество, логин, роль |
| **Заказы** | id, дата, пользователь_id |
| **Позиции заказа** | id, заказ_id, склад_id, количество, цена_на_момент |

Все таблицы находятся в 3НФ: нет транзитивных зависимостей, все неключевые атрибуты зависят только от первичного ключа.

### 1.2. SQL-скрипт создания БД

Сохраните как `schema.sql`:

```sql
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS OrderItems;
DROP TABLE IF EXISTS Orders;
DROP TABLE IF EXISTS Stock;
DROP TABLE IF EXISTS Products;
DROP TABLE IF EXISTS Sizes;
DROP TABLE IF EXISTS Manufacturers;
DROP TABLE IF EXISTS Categories;
DROP TABLE IF EXISTS Users;

CREATE TABLE Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    login TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Администратор','Менеджер','Авторизованный пользователь'))
);

CREATE TABLE Categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE Manufacturers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE Products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES Categories(id),
    manufacturer_id INTEGER NOT NULL REFERENCES Manufacturers(id),
    name TEXT NOT NULL,
    subcategory TEXT,
    description TEXT,
    composition TEXT,
    price REAL NOT NULL CHECK(price >= 0),
    image TEXT,
    UNIQUE(name, manufacturer_id)
);

CREATE TABLE Sizes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value TEXT UNIQUE NOT NULL
);

CREATE TABLE Stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES Products(id) ON DELETE CASCADE,
    size_id INTEGER NOT NULL REFERENCES Sizes(id),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    UNIQUE(product_id, size_id)
);

CREATE TABLE Orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_date TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES Users(id)
);

CREATE TABLE OrderItems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
    stock_id INTEGER NOT NULL REFERENCES Stock(id),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL
);
```

### 1.3. ER-диаграмма

Схема связей:

```
Users 1───* Orders 1───* OrderItems *───1 Stock *───1 Products *───1 Categories
                                                       │
                                                       └───1 Manufacturers
                                              Stock *───1 Sizes
```

Для получения ER-диаграммы в PDF можно использовать `sqlite3` + `graphviz` или онлайн-сервис dbdiagram.io. В рамках практической работы достаточно этой схемы.

---

## Часть 2. Импорт данных из Excel

Файл `.xlsx` — это ZIP-архив. Читаем его встроенными модулями `zipfile` и `xml.etree.ElementTree`.

Создайте файл `import_data.py`:

```python
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
import os
import shutil
import re
from datetime import datetime

NS = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def col_to_idx(col: str) -> int:
    """A->0, B->1, ..., AA->26"""
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - ord('A') + 1)
    return idx - 1

def read_xlsx(path: str):
    """Возвращает список листов: [(sheet_name, [row, row, ...]), ...]"""
    with zipfile.ZipFile(path) as z:
        # читаем shared strings
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('a:si', NS):
                text = ''.join(t.text or '' for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'))
                shared.append(text)

        # читаем workbook — порядок листов
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        sheets = [(s.get('name'), s.get('sheetId')) for s in wb.findall('.//a:sheet', NS)]

        # связи sheetId -> rId
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rel_map = {r.get('Id'): r.get('Target') for r in rels}

        result = []
        for name, _ in sheets:
            # ищем файл листа
            for rid, target in rel_map.items():
                if 'worksheets' in target:
                    sheet_file = 'xl/' + target.lstrip('/')
                    if sheet_file in z.namelist():
                        break
            root = ET.fromstring(z.read(sheet_file))
            rows = []
            for row in root.findall('.//a:sheetData/a:row', NS):
                cells = {}
                for c in row.findall('a:c', NS):
                    ref = c.get('r')
                    col_letters = re.match(r'[A-Z]+', ref).group()
                    idx = col_to_idx(col_letters)
                    t = c.get('t')
                    v = c.find('a:v', NS)
                    if v is None:
                        val = ''
                    elif t == 's':
                        val = shared[int(v.text)]
                    else:
                        val = v.text
                    cells[idx] = val
                if cells:
                    max_idx = max(cells.keys())
                    rows.append([cells.get(i, '') for i in range(max_idx + 1)])
            result.append((name, rows))
            break  # берём первый лист
        return result

def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    except Exception:
        return s

def get_or_create(cur, table, name):
    cur.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table}(name) VALUES (?)", (name,))
    return cur.lastrowid

def import_all(db_path='shop.db', data_dir='.'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(open('schema.sql', encoding='utf-8').read())

    # ---------- Sizes ----------
    _, rows = read_xlsx(os.path.join(data_dir, 'Sizes_import.xlsx'))[0]
    for row in rows[1:]:  # пропускаем заголовок
        if row and row[0].strip():
            cur.execute("INSERT OR IGNORE INTO Sizes(value) VALUES (?)", (row[0].strip(),))

    # ---------- Users ----------
    _, rows = read_xlsx(os.path.join(data_dir, 'Users_import.xlsx'))[0]
    for row in rows[1:]:
        if len(row) < 5 or not row[3]:
            continue
        cur.execute("""INSERT OR IGNORE INTO Users(last_name, first_name, middle_name, login, role)
                       VALUES (?,?,?,?,?)""",
                    (row[0], row[1], row[2], row[3], row[4]))

    # ---------- Products + Categories + Manufacturers ----------
    _, rows = read_xlsx(os.path.join(data_dir, 'Products_import.xlsx'))[0]
    for row in rows[1:]:
        if len(row) < 8 or not row[3]:
            continue
        cat = get_or_create(cur, 'Categories', row[0].strip())
        man = get_or_create(cur, 'Manufacturers', row[4].strip())
        cur.execute("""INSERT OR IGNORE INTO Products
            (category_id, manufacturer_id, name, subcategory, description, composition, price, image)
            VALUES (?,?,?,?,?,?,?,?)""",
            (cat, man, row[3].strip(), row[1], row[5], row[6], float(row[7]), row[2]))
        # если уже есть — обновим картинку (для случаев повторного импорта)
        cur.execute("""UPDATE Products SET image=? WHERE name=? AND manufacturer_id=?""",
                    (row[2], row[3].strip(), man))

    # ---------- Stock ----------
    _, rows = read_xlsx(os.path.join(data_dir, 'Stock_Items_import.xlsx'))[0]
    for row in rows[1:]:
        if len(row) < 4 or not row[0]:
            continue
        name = row[0].strip()
        man_name = row[1].strip()
        size_val = str(row[2]).strip()
        qty = int(float(row[3])) if row[3] else 0

        cur.execute("""SELECT p.id FROM Products p
                       JOIN Manufacturers m ON m.id = p.manufacturer_id
                       WHERE p.name = ? AND m.name = ?""", (name, man_name))
        p = cur.fetchone()
        if not p:
            print(f'[!] Не найден товар: {name} / {man_name}')
            continue
        cur.execute("SELECT id FROM Sizes WHERE value = ?", (size_val,))
        s = cur.fetchone()
        if not s:
            cur.execute("INSERT INTO Sizes(value) VALUES (?)", (size_val,))
            s_id = cur.lastrowid
        else:
            s_id = s[0]

        cur.execute("""INSERT INTO Stock(product_id, size_id, quantity) VALUES (?,?,?)
                       ON CONFLICT(product_id, size_id) DO UPDATE SET quantity = excluded.quantity""",
                    (p[0], s_id, qty))

    # ---------- Orders ----------
    _, rows = read_xlsx(os.path.join(data_dir, 'Orders_import.xlsx'))[0]
    # кэш: (order_num) -> order_id
    order_cache = {}
    for row in rows[1:]:
        if len(row) < 9 or not row[0]:
            continue
        order_num = str(row[0]).strip()
        order_date = parse_date(row[1])
        fio = row[2].strip()
        # ищем пользователя по ФИО
        parts = fio.split()
        last_name = parts[0] if len(parts) > 0 else ''
        first_name = parts[1] if len(parts) > 1 else ''
        cur.execute("SELECT id FROM Users WHERE last_name=? AND first_name=?",
                    (last_name, first_name))
        u = cur.fetchone()
        user_id = u[0] if u else None
        if user_id is None:
            # создаём гостя
            cur.execute("""INSERT INTO Users(last_name, first_name, middle_name, login, role)
                           VALUES (?,?,?,?,'Авторизованный пользователь')""",
                        (last_name, first_name, parts[2] if len(parts) > 2 else '',
                         'guest_' + order_num))
            user_id = cur.lastrowid

        if order_num not in order_cache:
            cur.execute("INSERT INTO Orders(order_date, user_id) VALUES (?,?)",
                        (order_date, user_id))
            order_cache[order_num] = cur.lastrowid
        order_id = order_cache[order_num]

        # позиция
        name = row[4].strip()
        man_name = row[5].strip()
        size_val = str(row[6]).strip()
        qty = int(float(row[7])) if row[7] else 1
        price = float(row[8]) if row[8] else 0

        cur.execute("""SELECT s.id FROM Stock s
                       JOIN Products p ON p.id = s.product_id
                       JOIN Manufacturers m ON m.id = p.manufacturer_id
                       JOIN Sizes sz ON sz.id = s.size_id
                       WHERE p.name=? AND m.name=? AND sz.value=?""",
                    (name, man_name, size_val))
        st = cur.fetchone()
        if st:
            cur.execute("""INSERT INTO OrderItems(order_id, stock_id, quantity, unit_price)
                           VALUES (?,?,?,?)""", (order_id, st[0], qty, price))

    conn.commit()
    conn.close()
    print('Импорт завершён успешно!')

if __name__ == '__main__':
    import_all()
```

**Запуск:**
```bash
python import_data.py
```
На выходе получите файл `shop.db` со всеми данными.

---

## Часть 3. Backend на Python (встроенный http.server)

Создайте `server.py`:

```python
import json
import sqlite3
import os
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

DB = 'shop.db'
STATIC_DIR = 'static'  # сюда положим index.html, app.js, style.css
UPLOADS_DIR = 'static/uploads'  # сюда — картинки товаров

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

class Handler(BaseHTTPRequestHandler):
    # ---------- утилиты ----------
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        if not os.path.isfile(path):
            self.send_error(404)
            return
        ctype, _ = mimetypes.guess_type(path)
        ctype = ctype or 'application/octet-stream'
        with open(path, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode('utf-8'))

    # ---------- маршрутизация ----------
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        qs = parse_qs(url.query)

        # API
        if path == '/api/login':
            return self.api_login(qs)
        if path == '/api/products':
            return self.api_products(qs)
        if path == '/api/product':
            return self.api_product(qs)
        if path == '/api/categories':
            return self.api_categories()
        if path == '/api/orders':
            return self.api_orders(qs)
        if path == '/api/order':
            return self.api_order(qs)

        # статика
        if path == '/':
            path = '/index.html'
        file_path = os.path.join(STATIC_DIR, path.lstrip('/'))
        return self.send_file(file_path)

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        data = self.read_json()

        if path == '/api/order/create':
            return self.api_create_order(data)
        if path == '/api/order/update':
            return self.api_update_order(data)
        if path == '/api/order/delete':
            return self.api_delete_order(data)
        self.send_error(404)

    # ---------- API ----------
    def api_login(self, qs):
        login = (qs.get('login', [''])[0] or '').strip()
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id, last_name, first_name, middle_name, role FROM Users WHERE login=?",
                    (login,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return self.send_json({'error': 'Логин не найден'}, 404)
        return self.send_json(dict(row))

    def api_categories(self):
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM Categories ORDER BY name")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return self.send_json(rows)

    def api_products(self, qs):
        """Список товаров с суммарным количеством, ценой со скидкой, фильтрами/поиском/сортировкой."""
        category_id = qs.get('category', [None])[0]
        search = qs.get('search', [''])[0].strip().lower()
        sort = qs.get('sort', [''])[0]  # 'price_asc' | 'price_desc'

        conn = db()
        cur = conn.cursor()
        # товары + суммарное количество + признак заказов за прошлый месяц
        query = """
        SELECT p.id, p.name, p.subcategory, p.description, p.composition,
               p.price, p.image, c.name AS category, m.name AS manufacturer,
               COALESCE((SELECT SUM(quantity) FROM Stock WHERE product_id=p.id), 0) AS total_qty,
               (SELECT COUNT(*) FROM OrderItems oi
                  JOIN Stock s ON s.id = oi.stock_id
                  JOIN Orders o ON o.id = oi.order_id
                 WHERE s.product_id = p.id
                   AND o.order_date >= ? AND o.order_date < ?) AS orders_last_month
        FROM Products p
        JOIN Categories c ON c.id = p.category_id
        JOIN Manufacturers m ON m.id = p.manufacturer_id
        """
        params = []
        today = datetime.now().replace(day=1)
        prev_month_start = (today - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
        prev_month_end = today.strftime('%Y-%m-%d')
        params.extend([prev_month_start, prev_month_end])

        where = []
        if category_id:
            where.append("c.id = ?")
            params.append(int(category_id))
        if search:
            where.append("(LOWER(p.name) LIKE ? OR LOWER(p.description) LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])
        if where:
            query += " WHERE " + " AND ".join(where)

        # сортировка с учётом скидки — считаем в Python
        cur.execute(query, params)
        items = []
        for r in cur.fetchall():
            d = dict(r)
            # Скидка 25% если в прошлом месяце заказов не было
            d['discount'] = 25 if d['orders_last_month'] == 0 else 0
            d['price_final'] = round(d['price'] * (100 - d['discount']) / 100, 2)
            # "много"/"мало"
            d['availability'] = 'много' if d['total_qty'] > 5 else 'мало'
            items.append(d)

        if sort == 'price_asc':
            items.sort(key=lambda x: x['price_final'])
        elif sort == 'price_desc':
            items.sort(key=lambda x: x['price_final'], reverse=True)

        conn.close()
        return self.send_json(items)

    def api_product(self, qs):
        pid = int(qs.get('id', [0])[0])
        conn = db()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.name, p.subcategory, p.description, p.composition,
                   p.price, p.image, c.name AS category, m.name AS manufacturer
            FROM Products p
            JOIN Categories c ON c.id = p.category_id
            JOIN Manufacturers m ON m.id = p.manufacturer_id
            WHERE p.id = ?
        """, (pid,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return self.send_json({'error': 'not found'}, 404)
        product = dict(row)
        # скидка
        today = datetime.now().replace(day=1)
        prev_start = (today - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
        prev_end = today.strftime('%Y-%m-%d')
        cur.execute("""SELECT COUNT(*) FROM OrderItems oi
                       JOIN Stock s ON s.id=oi.stock_id
                       JOIN Orders o ON o.id=oi.order_id
                       WHERE s.product_id=? AND o.order_date>=? AND o.order_date<?""",
                    (pid, prev_start, prev_end))
        orders_last = cur.fetchone()[0]
        product['discount'] = 25 if orders_last == 0 else 0
        product['price_final'] = round(product['price'] * (100 - product['discount']) / 100, 2)

        # размеры
        cur.execute("""SELECT s.id, sz.value, s.quantity
                       FROM Stock s JOIN Sizes sz ON sz.id = s.size_id
                       WHERE s.product_id = ? ORDER BY CAST(sz.value AS REAL)""", (pid,))
        product['sizes'] = [dict(r) for r in cur.fetchall()]
        conn.close()
        return self.send_json(product)

    def api_orders(self, qs):
        user_id = qs.get('user_id', [None])[0]
        conn = db()
        cur = conn.cursor()
        if user_id:
            cur.execute("""SELECT o.id, o.order_date, u.last_name||' '||u.first_name||' '||COALESCE(u.middle_name,'') AS fio
                           FROM Orders o JOIN Users u ON u.id=o.user_id
                           WHERE o.user_id=? ORDER BY o.id DESC""", (int(user_id),))
        else:
            cur.execute("""SELECT o.id, o.order_date, u.last_name||' '||u.first_name||' '||COALESCE(u.middle_name,'') AS fio
                           FROM Orders o JOIN Users u ON u.id=o.user_id ORDER BY o.id DESC""")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return self.send_json(rows)

    def api_order(self, qs):
        oid = int(qs.get('id', [0])[0])
        conn = db()
        cur = conn.cursor()
        cur.execute("""SELECT o.id, o.order_date, u.last_name||' '||u.first_name||' '||COALESCE(u.middle_name,'') AS fio
                       FROM Orders o JOIN Users u ON u.id=o.user_id WHERE o.id=?""", (oid,))
        order = cur.fetchone()
        if not order:
            conn.close()
            return self.send_json({'error': 'not found'}, 404)
        order = dict(order)
        cur.execute("""SELECT oi.id, oi.quantity, oi.unit_price,
                              p.name AS product, m.name AS manufacturer, sz.value AS size
                       FROM OrderItems oi
                       JOIN Stock s ON s.id = oi.stock_id
                       JOIN Products p ON p.id = s.product_id
                       JOIN Manufacturers m ON m.id = p.manufacturer_id
                       JOIN Sizes sz ON sz.id = s.size_id
                       WHERE oi.order_id = ?""", (oid,))
        order['items'] = [dict(r) for r in cur.fetchall()]
        order['total'] = sum(i['quantity'] * i['unit_price'] for i in order['items'])
        conn.close()
        return self.send_json(order)

    def api_create_order(self, data):
        user_id = data.get('user_id')
        items = data.get('items', [])  # [{stock_id, quantity}, ...]
        if not user_id or not items:
            return self.send_json({'error': 'Нет данных'}, 400)
        conn = db()
        cur = conn.cursor()
        try:
            order_date = datetime.now().strftime('%Y-%m-%d')
            cur.execute("INSERT INTO Orders(order_date, user_id) VALUES (?,?)",
                        (order_date, user_id))
            order_id = cur.lastrowid
            for it in items:
                cur.execute("SELECT quantity FROM Stock WHERE id=?", (it['stock_id'],))
                st = cur.fetchone()
                if not st or st[0] < it['quantity']:
                    raise ValueError(f"Недостаточно товара на складе (stock_id={it['stock_id']})")
                cur.execute("""SELECT p.price FROM Stock s JOIN Products p ON p.id=s.product_id
                               WHERE s.id=?""", (it['stock_id'],))
                # цена без скидки
                price = cur.fetchone()[0]
                cur.execute("""INSERT INTO OrderItems(order_id, stock_id, quantity, unit_price)
                               VALUES (?,?,?,?)""",
                            (order_id, it['stock_id'], it['quantity'], price))
                cur.execute("UPDATE Stock SET quantity = quantity - ? WHERE id=?",
                            (it['quantity'], it['stock_id']))
            conn.commit()
            return self.send_json({'order_id': order_id})
        except Exception as e:
            conn.rollback()
            return self.send_json({'error': str(e)}, 400)
        finally:
            conn.close()

    def api_update_order(self, data):
        """Администратор меняет дату заказа и удаляет позиции."""
        oid = data.get('order_id')
        new_date = data.get('order_date')
        remove_items = data.get('remove_items', [])
        conn = db()
        cur = conn.cursor()
        try:
            if new_date:
                cur.execute("UPDATE Orders SET order_date=? WHERE id=?", (new_date, oid))
            for item_id in remove_items:
                # возвращаем товар на склад
                cur.execute("SELECT stock_id, quantity FROM OrderItems WHERE id=?", (item_id,))
                row = cur.fetchone()
                if row:
                    cur.execute("UPDATE Stock SET quantity = quantity + ? WHERE id=?",
                                (row[1], row[0]))
                    cur.execute("DELETE FROM OrderItems WHERE id=?", (item_id,))
            conn.commit()
            return self.send_json({'ok': True})
        except Exception as e:
            conn.rollback()
            return self.send_json({'error': str(e)}, 400)
        finally:
            conn.close()

    def api_delete_order(self, data):
        oid = data.get('order_id')
        conn = db()
        cur = conn.cursor()
        try:
            # вернуть всё на склад
            cur.execute("SELECT stock_id, quantity FROM OrderItems WHERE order_id=?", (oid,))
            for stock_id, qty in cur.fetchall():
                cur.execute("UPDATE Stock SET quantity = quantity + ? WHERE id=?", (qty, stock_id))
            cur.execute("DELETE FROM Orders WHERE id=?", (oid,))
            conn.commit()
            return self.send_json({'ok': True})
        except Exception as e:
            conn.rollback()
            return self.send_json({'error': str(e)}, 400)
        finally:
            conn.close()

    def log_message(self, fmt, *args):
        pass  # отключаем лишний вывод


if __name__ == '__main__':
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print('Сервер запущен: http://localhost:8000')
    HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
```

---

## Часть 4. Frontend на чистом JavaScript

### 4.1. Структура проекта

```
project/
├── schema.sql
├── import_data.py
├── server.py
├── shop.db
├── static/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── uploads/         ← сюда положить все .png из Products_import
└── *.xlsx
```

### 4.2. `static/index.html`

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Обувной магазин</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header id="header">
  <div class="logo">👟 Обувной магазин</div>
  <div id="user-info"></div>
</header>

<main id="app"></main>

<!-- Шаблон карточки товара -->
<template id="tpl-product">
  <div class="product-card" data-id="">
    <img class="product-img" src="" alt="">
    <div class="product-info">
      <div class="row title-row">
        <span class="prod-title"></span>
        <span class="prod-price"></span>
      </div>
      <div class="row"><span class="label">Категория:</span> <span class="cat"></span></div>
      <div class="row"><span class="label">Количество:</span> <span class="qty"></span></div>
      <div class="row"><span class="label">Состав:</span> <span class="composition"></span></div>
    </div>
  </div>
</template>

<script src="/app.js"></script>
</body>
</html>
```

### 4.3. `static/style.css`

```css
* { box-sizing: border-box; font-family: Arial, sans-serif; }
body { margin: 0; background: #f5f5f5; color: #222; }
header { display: flex; justify-content: space-between; align-items: center;
         padding: 12px 24px; background: #2c3e50; color: #fff; }
.logo { font-size: 20px; font-weight: bold; }
main { max-width: 1100px; margin: 20px auto; padding: 0 16px; }

.controls { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.controls input, .controls select, .controls button {
  padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px;
}
.controls button { background: #3498db; color: #fff; border: none; cursor: pointer; }
.controls button:hover { background: #2980b9; }

.product-card { display: flex; gap: 16px; background: #fff; padding: 14px;
                margin-bottom: 12px; border-radius: 8px; cursor: pointer;
                box-shadow: 0 1px 3px rgba(0,0,0,.1); transition: .2s; }
.product-card:hover { box-shadow: 0 3px 10px rgba(0,0,0,.15); }
.product-card.low-stock { background: #ffe0e0; }
.product-img { width: 120px; height: 90px; object-fit: contain; background: #fafafa;
               border-radius: 6px; border: 1px solid #eee; }
.product-info { flex: 1; }
.row { margin: 4px 0; }
.title-row { display: flex; justify-content: space-between; font-size: 17px; font-weight: bold; }
.label { color: #666; margin-right: 4px; }
.prod-price { color: #27ae60; }

button.primary { background: #27ae60; color:#fff; border:none; padding:10px 18px;
                 border-radius:6px; cursor:pointer; font-size:14px; }
button.primary:hover { background: #219150; }
button.danger { background: #e74c3c; color:#fff; border:none; padding:8px 12px;
                border-radius:6px; cursor:pointer; }
button.ghost { background: transparent; border: 1px solid #888; padding:8px 14px;
               border-radius:6px; cursor:pointer; }

.modal-backdrop { position: fixed; inset:0; background: rgba(0,0,0,.5);
                  display:flex; align-items:center; justify-content:center; z-index:100; }
.modal { background:#fff; border-radius:10px; max-width:700px; width: 92%;
         max-height: 90vh; overflow-y:auto; padding: 20px; }
.modal h2 { margin-top: 0; }
.cart-item { display:flex; justify-content:space-between; align-items:center;
             padding:8px 0; border-bottom:1px solid #eee; }

table { width:100%; border-collapse: collapse; }
table th, table td { padding:8px; border-bottom:1px solid #eee; text-align:left; }
```

### 4.4. `static/app.js`

```javascript
/* ============ Глобальное состояние ============ */
const state = {
  user: null,           // {id, last_name, first_name, role, ...}
  products: [],
  categories: [],
  filters: { search: '', category: '', sort: '' },
  cart: [],             // [{stock_id, quantity, name, size, price, manufacturer}]
  view: 'catalog',      // 'catalog' | 'orders' | 'admin'
};

const app = document.getElementById('app');
const headerInfo = document.getElementById('user-info');

/* ============ Утилиты ============ */
async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({error: 'Ошибка'}));
    throw new Error(err.error || 'Ошибка');
  }
  return res.json();
}

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

function showModal(html) {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.innerHTML = `<div class="modal">${html}</div>`;
  backdrop.addEventListener('click', e => {
    if (e.target === backdrop) backdrop.remove();
  });
  document.body.appendChild(backdrop);
  return backdrop;
}

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.style.cssText = `position:fixed;top:20px;right:20px;padding:12px 18px;border-radius:6px;
    color:#fff;font-size:14px;z-index:1000;box-shadow:0 2px 10px rgba(0,0,0,.2);
    background:${type==='error'?'#e74c3c':type==='success'?'#27ae60':'#3498db'}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

/* ============ Авторизация ============ */
async function login() {
  const modal = showModal(`
    <h2>Вход в систему</h2>
    <p>Введите логин (пароль не требуется):</p>
    <input id="login-input" type="text" placeholder="например, isivanov"
           style="width:100%;padding:10px;font-size:14px;border:1px solid #ccc;border-radius:6px;">
    <div style="margin-top:14px;text-align:right;">
      <button class="ghost" id="cancel-login">Отмена</button>
      <button class="primary" id="do-login">Войти</button>
    </div>
  `);
  const input = modal.querySelector('#login-input');
  input.focus();
  modal.querySelector('#cancel-login').onclick = () => modal.remove();
  const doLogin = async () => {
    const login = input.value.trim();
    if (!login) return toast('Введите логин', 'error');
    try {
      const user = await api('/api/login?login=' + encodeURIComponent(login));
      state.user = user;
      modal.remove();
      renderHeader();
      toast('Добро пожаловать, ' + user.first_name, 'success');
      render();
    } catch (e) {
      toast(e.message, 'error');
    }
  };
  modal.querySelector('#do-login').onclick = doLogin;
  input.addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
}

function renderHeader() {
  if (!state.user) {
    headerInfo.innerHTML = `<button class="ghost" id="login-btn">Войти</button>`;
    document.getElementById('login-btn').onclick = login;
    return;
  }
  const fio = `${state.user.last_name} ${state.user.first_name} ${state.user.middle_name || ''}`.trim();
  const isAdmin = state.user.role === 'Администратор';
  const isManager = state.user.role === 'Менеджер';
  headerInfo.innerHTML = `
    <span style="margin-right:12px;">${escapeHtml(fio)} (${state.user.role})</span>
    <button class="ghost" id="cart-btn">🛒 Корзина (${state.cart.length})</button>
    ${(isAdmin || isManager) ? '<button class="ghost" id="orders-btn">📋 Заказы</button>' : ''}
    <button class="ghost" id="logout-btn">Выйти</button>
  `;
  document.getElementById('cart-btn').onclick = showCart;
  const ordersBtn = document.getElementById('orders-btn');
  if (ordersBtn) ordersBtn.onclick = () => { state.view = 'orders'; render(); };
  document.getElementById('logout-btn').onclick = () => {
    state.user = null; state.cart = []; state.view = 'catalog';
    renderHeader(); render();
  };
}

/* ============ Каталог ============ */
async function loadCatalog() {
  const params = new URLSearchParams();
  if (state.filters.search) params.set('search', state.filters.search);
  if (state.filters.category) params.set('category', state.filters.category);
  if (state.filters.sort) params.set('sort', state.filters.sort);
  state.products = await api('/api/products?' + params.toString());
}

async function loadCategories() {
  state.categories = await api('/api/categories');
}

function renderCatalog() {
  app.innerHTML = `
    <div class="controls">
      <input id="search-input" type="text" placeholder="🔍 Поиск по названию и описанию"
             value="${escapeHtml(state.filters.search)}">
      <select id="cat-select">
        <option value="">Все категории</option>
        ${state.categories.map(c =>
          `<option value="${c.id}" ${state.filters.category == c.id ? 'selected' : ''}>${escapeHtml(c.name)}</option>`
        ).join('')}
      </select>
      <select id="sort-select">
        <option value="">Без сортировки</option>
        <option value="price_asc" ${state.filters.sort==='price_asc'?'selected':''}>Цена ↑</option>
        <option value="price_desc" ${state.filters.sort==='price_desc'?'selected':''}>Цена ↓</option>
      </select>
    </div>
    <div id="products-list"></div>
  `;
  const list = document.getElementById('products-list');
  list.innerHTML = state.products.map(p => {
    const lowClass = p.total_qty <= 3 ? 'low-stock' : '';
    const img = p.image ? `/uploads/${p.image}` : '/uploads/picture.png';
    return `
      <div class="product-card ${lowClass}" data-id="${p.id}">
        <img class="product-img" src="${img}" alt="" onerror="this.src='/uploads/picture.png'">
        <div class="product-info">
          <div class="row title-row">
            <span class="prod-title">${escapeHtml(p.manufacturer)} | ${escapeHtml(p.name)}</span>
            <span class="prod-price">${p.price_final} ₽ ${p.discount ? `<s style="color:#999;font-size:13px">${p.price} ₽</s>` : ''}</span>
          </div>
          <div class="row"><span class="label">Категория:</span> ${escapeHtml(p.category)}</div>
          <div class="row"><span class="label">Количество:</span> ${p.availability}</div>
          <div class="row"><span class="label">Состав:</span> ${escapeHtml(p.composition)}</div>
        </div>
      </div>
    `;
  }).join('');

  list.querySelectorAll('.product-card').forEach(card => {
    card.onclick = () => openProduct(Number(card.dataset.id));
  });

  // живые фильтры
  const searchInput = document.getElementById('search-input');
  searchInput.oninput = debounce(async e => {
    state.filters.search = e.target.value;
    await loadCatalog(); renderCatalog();
  }, 300);

  document.getElementById('cat-select').onchange = async e => {
    state.filters.category = e.target.value;
    await loadCatalog(); renderCatalog();
  };
  document.getElementById('sort-select').onchange = async e => {
    state.filters.sort = e.target.value;
    await loadCatalog(); renderCatalog();
  };
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

/* ============ Карточка товара ============ */
async function openProduct(id) {
  const p = await api('/api/product?id=' + id);
  const img = p.image ? `/uploads/${p.image}` : '/uploads/picture.png';
  const modal = showModal(`
    <div style="display:flex;gap:16px;">
      <img src="${img}" onerror="this.src='/uploads/picture.png'"
           style="width:180px;height:150px;object-fit:contain;border:1px solid #eee;border-radius:8px;">
      <div style="flex:1;">
        <h2 style="margin:0 0 8px;">${escapeHtml(p.manufacturer)} | ${escapeHtml(p.name)}</h2>
        <div><b>Категория:</b> ${escapeHtml(p.category)}</div>
        <div><b>Цена со скидкой:</b> ${p.price_final} ₽
             ${p.discount ? `<s style="color:#999">${p.price} ₽</s> <span style="color:#e74c3c">(-${p.discount}%)</span>` : ''}
        </div>
        <div><b>Состав:</b> ${escapeHtml(p.composition)}</div>
        <div><b>Описание:</b> ${escapeHtml(p.description)}</div>
      </div>
    </div>
    <hr>
    <h3>Доступные размеры</h3>
    <div id="sizes-box"></div>
  `);
  const sizesBox = modal.querySelector('#sizes-box');
  sizesBox.innerHTML = p.sizes.map(s =>
    `<label style="display:inline-block;margin:6px 8px 6px 0;">
      <input type="radio" name="size" value="${s.id}" data-qty="${s.quantity}">
      Размер ${escapeHtml(s.value)} (${s.quantity} шт.)
    </label>`
  ).join('') || '<i>Нет в наличии</i>';

  if (p.sizes.length) {
    sizesBox.insertAdjacentHTML('beforeend', `
      <div style="margin-top:12px;">
        <label>Количество:
          <input id="qty-input" type="number" min="1" value="1" style="width:80px;padding:6px;">
        </label>
        <button class="primary" id="add-cart-btn" style="margin-left:12px;">Добавить в корзину</button>
      </div>
    `);
    modal.querySelector('#add-cart-btn').onclick = () => {
      const sizeInput = modal.querySelector('input[name=size]:checked');
      if (!sizeInput) return toast('Выберите размер', 'error');
      const qty = Number(modal.querySelector('#qty-input').value);
      const maxQty = Number(sizeInput.dataset.qty);
      if (qty < 1 || qty > maxQty) return toast(`Доступно от 1 до ${maxQty}`, 'error');
      const sizeLabel = sizeInput.parentElement.textContent.trim().split(' ')[1];
      state.cart.push({
        stock_id: Number(sizeInput.value),
        quantity: qty,
        name: p.name, manufacturer: p.manufacturer,
        size: sizeLabel, price: p.price_final, product_id: p.id
      });
      toast('Добавлено в корзину', 'success');
      modal.remove();
      renderHeader();
    };
  }
}

/* ============ Корзина ============ */
function showCart() {
  if (!state.cart.length) {
    return showModal('<h2>Корзина пуста</h2><button class="ghost" onclick="this.closest(\'.modal-backdrop\').remove()">Закрыть</button>');
  }
  const total = state.cart.reduce((s, i) => s + i.price * i.quantity, 0);
  const modal = showModal(`
    <h2>Корзина</h2>
    <div id="cart-list">
      ${state.cart.map((i, idx) => `
        <div class="cart-item">
          <div>
            <b>${escapeHtml(i.manufacturer)} | ${escapeHtml(i.name)}</b><br>
            <small>Размер ${i.size} × ${i.quantity} = ${i.price * i.quantity} ₽</small>
          </div>
          <button class="danger" data-idx="${idx}">Удалить</button>
        </div>
      `).join('')}
    </div>
    <div style="text-align:right;font-size:18px;margin:12px 0;"><b>Итого: ${total} ₽</b></div>
    <div style="text-align:right;">
      <button class="ghost" id="close-cart">Отмена</button>
      <button class="primary" id="checkout">Оформить заказ</button>
    </div>
  `);
  modal.querySelectorAll('button.danger').forEach(b => {
    b.onclick = () => {
      state.cart.splice(Number(b.dataset.idx), 1);
      modal.remove();
      renderHeader();
      showCart();
    };
  });
  modal.querySelector('#close-cart').onclick = () => modal.remove();
  modal.querySelector('#checkout').onclick = async () => {
    if (!state.user) return toast('Требуется авторизация', 'error');
    try {
      const items = state.cart.map(i => ({ stock_id: i.stock_id, quantity: i.quantity }));
      const res = await api('/api/order/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_id: state.user.id, items })
      });
      toast('Заказ №' + res.order_id + ' оформлен!', 'success');
      state.cart = [];
      modal.remove();
      renderHeader();
      await loadCatalog();
      render();
    } catch (e) {
      toast(e.message, 'error');
    }
  };
}

/* ============ Заказы (Менеджер/Администратор) ============ */
async function renderOrders() {
  const orders = await api('/api/orders');
  const isAdmin = state.user.role === 'Администратор';
  app.innerHTML = `
    <button class="ghost" id="back-btn" style="margin-bottom:16px;">← Назад в каталог</button>
    <h2>Список заказов</h2>
    <table>
      <thead><tr><th>№</th><th>Дата</th><th>ФИО клиента</th><th></th></tr></thead>
      <tbody>
        ${orders.map(o => `
          <tr>
            <td>${o.id}</td>
            <td>${o.order_date}</td>
            <td>${escapeHtml(o.fio)}</td>
            <td><button class="ghost" data-id="${o.id}">Открыть</button></td>
          </tr>`).join('')}
      </tbody>
    </table>
  `;
  document.getElementById('back-btn').onclick = () => { state.view='catalog'; render(); };
  app.querySelectorAll('button[data-id]').forEach(b => {
    b.onclick = () => openOrder(Number(b.dataset.id), isAdmin);
  });
}

async function openOrder(id, isAdmin) {
  const o = await api('/api/order?id=' + id);
  const itemsHtml = o.items.map(it => `
    <tr>
      <td>${escapeHtml(it.manufacturer)} | ${escapeHtml(it.product)} (размер ${it.size})</td>
      <td>${it.quantity}</td>
      <td>${it.unit_price} ₽</td>
      <td>${it.quantity * it.unit_price} ₽</td>
      ${isAdmin ? `<td><button class="danger" data-item="${it.id}">✕</button></td>` : ''}
    </tr>`).join('');
  const modal = showModal(`
    <h2>Заказ №${o.id}</h2>
    <div><b>Дата:</b>
      ${isAdmin
        ? `<input type="date" id="order-date" value="${o.order_date}">`
        : o.order_date}
    </div>
    <div><b>Клиент:</b> ${escapeHtml(o.fio)}</div>
    <table style="margin-top:12px;">
      <thead><tr><th>Товар</th><th>Кол-во</th><th>Цена</th><th>Сумма</th>${isAdmin?'<th></th>':''}</tr></thead>
      <tbody id="order-items">${itemsHtml}</tbody>
    </table>
    <div style="text-align:right;font-size:18px;margin-top:10px;"><b>Итого: ${o.total} ₽</b></div>
    <div style="text-align:right;margin-top:12px;">
      <button class="ghost" id="close-order">Закрыть</button>
      ${isAdmin ? '<button class="primary" id="save-order">Сохранить изменения</button>' : ''}
    </div>
  `);
  modal.querySelector('#close-order').onclick = () => modal.remove();

  if (isAdmin) {
    const removed = [];
    modal.querySelectorAll('button[data-item]').forEach(b => {
      b.onclick = () => {
        removed.push(Number(b.dataset.item));
        b.closest('tr').remove();
      };
    });
    modal.querySelector('#save-order').onclick = async () => {
      const newDate = modal.querySelector('#order-date').value;
      try {
        await api('/api/order/update', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ order_id: o.id, order_date: newDate, remove_items: removed })
        });
        toast('Изменения сохранены', 'success');
        modal.remove();
        renderOrders();
      } catch (e) { toast(e.message, 'error'); }
    };
  }
}

/* ============ Роутинг ============ */
async function render() {
  if (state.view === 'orders' && state.user &&
      (state.user.role === 'Администратор' || state.user.role === 'Менеджер')) {
    return renderOrders();
  }
  await loadCatalog();
  renderCatalog();
}

/* ============ Инициализация ============ */
(async function init() {
  renderHeader();
  await loadCategories();
  await render();
})();
```

---

## Часть 5. Подготовка ресурсов (изображений)

1. Создайте папку `static/uploads/`.
2. Скопируйте туда все `.png` из архива ресурсов (те, что указаны в колонке `Изображение` файла `Products_import.xlsx`).
3. Обязательно положите туда `picture.png` — картинку-заглушку.

Если каких-то изображений нет, `onerror` в HTML подставит заглушку.

---

## Часть 6. Запуск и проверка

```bash
# 1. Устанавливаем структуру
mkdir -p static/uploads

# 2. Кладём schema.sql, import_data.py, server.py
# 3. Кладём xlsx-файлы рядом
# 4. Кладём index.html, app.js, style.css в static/
# 5. Кладём картинки в static/uploads/

# 6. Импортируем данные
python import_data.py

# 7. Запускаем сервер
python server.py
```

Открываем `http://localhost:8000`.

### Сценарии проверки

1. **Авторизация.** Войти как `isivanov` (Администратор) — должна появиться кнопка «Заказы». Войти как `asidorova` — только корзина.
2. **Каталог.** Все товары отображаются с ценой со скидкой. Товары с количеством ≤3 — светло-красные. У товаров без заказов за прошлый месяц скидка 25%.
3. **Фильтры и поиск.** Ввод текста фильтрует в реальном времени; выбор категории и сортировки работают совместно.
4. **Карточка товара.** Открывается модальное окно с размерами. Можно добавить в корзину.
5. **Корзина.** Можно удалять позиции, оформить заказ. После оформления остаток на складе уменьшается.
6. **Заказы.** Менеджер и администратор видят список. Администратор может менять дату и удалять позиции (товар возвращается на склад).

---

## Часть 7. Сохранение результатов

Согласно спецификации, результаты сдаются через **Git-репозиторий**:

```
├── .git/
├── README.md         ← описание функциональности
├── schema.sql
├── import_data.py
├── server.py
├── shop.db           ← скрипт БД с данными
├── *.xlsx
└── static/
    ├── index.html
    ├── app.js
    ├── style.css
    └── uploads/
        ├── picture.png
        └── IMG_*.png
```

**README.md** — краткое описание:

```markdown
# Система оформления заказа обуви

## Технологии
- Python 3.8 (http.server, sqlite3, zipfile, xml.etree)
- JavaScript (vanilla), HTML, CSS

## Запуск
1. `python import_data.py` — создать БД из xlsx
2. `python server.py` — запустить сервер на :8000
3. Открыть http://localhost:8000

## Функциональность
- Авторизация по логину без пароля
- Каталог с фильтрацией, поиском, сортировкой
- Скидка 25% на товары без заказов в прошлом месяце
- Подсветка товаров с остатком ≤3
- Корзина и оформление заказа
- Панель заказов для Менеджера и Администратора
```

Загрузка в Git:

```bash
git init
git add .
git commit -m "Практическая работа: система заказа обуви"
git remote add origin <URL_вашего_репозитория>
git push -u origin master
```

---

## Контрольные вопросы

1. Почему БД приведена к 3НФ? Какие транзитивные зависимости устраняются?
2. Как реализована логика скидки 25%? Какой SQL-запрос её обеспечивает?
3. Как обеспечить ссылочную целостность при удалении заказа?
4. Как реализованы живые фильтры без перезагрузки страницы?
5. Как проверить корректность импорта данных из Excel?

---

## Критерии оценивания (соответствуют КИМ)

| Критерий | Балл |
|---|---|
| Разработка объектов БД по анализу предметной области | 12,00 |
| Реализация БД в конкретной СУБД | 3,00 |
| Формирование алгоритмов разработки модулей | 2,00 |
| Разработка программных модулей | 6,00 |
| Выполнение отладки | 2,00 |
| Модификация компонентов ПО | 22,00 |
| Использование средств поиска/анализа информации | 3,00 |
| Интеграция модулей | 21,00 |
| Выбор способов решения задач | 4,00 |
| **ИТОГО** | **75,00** |

---
