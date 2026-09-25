# Подробная инструкция: создание базы данных для системы заказа обуви

**ОС:** ROSA Linux (ROSA Fresh / ROSA Chrome)
**Python:** 3.8 (встроенный)
**СУБД:** SQLite (входит в стандартную библиотеку Python)
**Инструмент проектирования:** DB Browser for SQLite (опционально)

---

## Содержание

1. [Подготовка рабочего окружения](#1-подготовка-рабочего-окружения)
2. [Проверка Python 3.8 в ROSA Linux](#2-проверка-python-38-в-rosa-linux)
3. [Установка вспомогательных инструментов](#3-установка-вспомогательных-инструментов)
4. [Анализ предметной области](#4-анализ-предметной-области)
5. [Проектирование схемы БД (3НФ)](#5-проектирование-схемы-бд-3нф)
6. [Написание SQL-скрипта создания БД](#6-написание-sql-скрипта-создания-бд)
7. [Создание базы данных из Python](#7-создание-базы-данных-из-python)
8. [Чтение Excel-файлов встроенными средствами](#8-чтение-excel-файлов-встроенными-средствами)
9. [Написание скрипта импорта данных](#9-написание-скрипта-импорта-данных)
10. [Запуск импорта и проверка](#10-запуск-импорта-и-проверка)
11. [Построение ER-диаграммы](#11-построение-er-диаграммы)
12. [Сохранение результатов](#12-сохранение-результатов)
13. [Типичные ошибки и их решение](#13-типичные-ошибки-и-их-решение)

---

## 1. Подготовка рабочего окружения

### 1.1. Создание рабочей папки

Откройте терминал (`Ctrl+Alt+T`) и выполните:

```bash
mkdir -p ~/shoe_shop/static/uploads
cd ~/shoe_shop
```

Проверьте путь:

```bash
pwd
# Должно вывести: /home/ваш_пользователь/shoe_shop
```

### 1.2. Размещение исходных файлов

Скопируйте в папку `~/shoe_shop/` пять Excel-файлов:

- `Products_import.xlsx`
- `Stock_Items_import.xlsx`
- `Sizes_import.xlsx`
- `Orders_import.xlsx`
- `Users_import.xlsx`

Также скопируйте в `~/shoe_shop/static/uploads/` все картинки товаров (`IMG_*.png`) и картинку-заглушку `picture.png`.

Проверить наличие файлов:

```bash
ls -la ~/shoe_shop/
ls -la ~/shoe_shop/static/uploads/
```

---

## 2. Проверка Python 3.8 в ROSA Linux

### 2.1. Проверка версии

ROSA Linux обычно поставляет Python 3.8 или выше. Проверим:

```bash
python3 --version
```

Ожидаемый вывод:

```
Python 3.8.x
```

Если выводится другая версия — проверьте альтернативные бинарники:

```bash
ls /usr/bin/python*
```

Для работы используем `python3`.

### 2.2. Проверка встроенных модулей

Убеждаемся, что доступны нужные модули (все они входят в стандартную библиотеку Python 3.8):

```bash
python3 -c "import sqlite3, zipfile, xml.etree.ElementTree, os, re, shutil; print('OK')"
```

Ожидаемый вывод:

```
OK
```

Если выводится ошибка — установите пакет `python3`:

```bash
sudo dnf install python3
```

> **Важно:** в ROSA Linux используется пакетный менеджер `dnf` (или `urpmi` в старых версиях). Проверьте, что у вас есть права `sudo`.

### 2.3. Проверка версии SQLite

```bash
python3 -c "import sqlite3; print('SQLite version:', sqlite3.sqlite_version)"
```

Ожидаемый вывод:

```
SQLite version: 3.2x.x
```

Версия не ниже 3.24 приветствуется (для поддержки `ON CONFLICT`). В ROSA Fresh 12 обычно SQLite 3.34+.

---

## 3. Установка вспомогательных инструментов

### 3.1. DB Browser for SQLite

Это удобный GUI для просмотра и редактирования БД. Установка:

```bash
sudo dnf install sqlitebrowser
```

Запуск:

```bash
sqlitebrowser &
```

Если пакет недоступен:

```bash
sudo dnf install sqlitebrowser-qt5 || sudo urpmi sqlitebrowser
```

Альтернатива — консольный клиент `sqlite3`:

```bash
sudo dnf install sqlite
sqlite3 --version
```

### 3.2. Редактор кода

Для написания Python-скриптов подойдёт:

- **VS Code**: `sudo dnf install code`
- **Kate** (встроен в KDE, а ROSA — KDE-ориентированный дистрибутив): обычно уже установлен
- **Nano/Vim** — для быстрого редактирования в терминале

Проверим:

```bash
which kate nano vim code
```

### 3.3. Инструмент для ER-диаграмм

Рекомендуем **DBeaver** (универсальный клиент БД с генерацией ER-диаграмм):

```bash
sudo dnf install dbeaver
```

Или используем **онлайн** — `https://dbdiagram.io` (но на экзамене интернет может быть ограничен). В крайнем случае ER-диаграмму можно нарисовать в **Dia** или **draw.io (диаграммы.net)**:

```bash
sudo dnf install dia
```

---

## 4. Анализ предметной области

### 4.1. Читаем задание

Из спецификации КИМ (Приложение 1):

> Компания занимается продажей обуви. Требуется система, которая даёт возможность клиентам выбрать и заказать одну или несколько моделей обуви из каталога.
>
> Функциональные требования:
> - в каталоге хранится актуальное доступное для заказа количество товарных позиций: сочетаний модели и размера;
> - для каждой модели хранится изображение;
> - клиент может выбрать из каталога одну или несколько пар доступного размера и модели;
> - должен быть доступен просмотр списка заказов с ключевой информацией: дата заказа, ФИО клиента;
> - должно быть реализовано управление заказами.

### 4.2. Выделяем сущности из файлов Excel

Откроем файлы (например, через LibreOffice Calc — он обычно установлен в ROSA):

```bash
libreoffice --calc ~/shoe_shop/Products_import.xlsx &
```

Анализ:

| Файл | Колонки | Что даёт |
|---|---|---|
| **Products_import.xlsx** | Категория, Подкатегория, Изображение, Наименование товара, Производство, Описание, Состав, Цена | Сущности **Товар**, **Категория**, **Производитель** |
| **Stock_Items_import.xlsx** | Наименование товара, Производство, Размер, Количество доступное для заказа | Сущности **Склад (Товар+Размер)**, **Размер** |
| **Sizes_import.xlsx** | Размер | Справочник **Размер** |
| **Orders_import.xlsx** | Номер заказа, Дата заказа, ФИО, Категория, Наименование товара, Производство, Размер, Количество, Цена за единицу | Сущности **Заказ**, **Позиция заказа**, **Пользователь** |
| **Users_import.xlsx** | Фамилия, Имя, Отчество, Логин, Роль | Сущность **Пользователь** |

### 4.3. Определяем атрибуты

**Пользователи (Users):**
- `id` — первичный ключ (PK)
- `last_name`, `first_name`, `middle_name`
- `login` — уникальный
- `role` — одна из: Администратор, Менеджер, Авторизованный пользователь

**Категории (Categories):**
- `id` — PK
- `name` — уникальное

**Производители (Manufacturers):**
- `id` — PK
- `name` — уникальное

**Товары/Модели (Products):**
- `id` — PK
- `category_id` — FK → Categories
- `manufacturer_id` — FK → Manufacturers
- `name`, `subcategory`, `description`, `composition`, `price`, `image`

**Размеры (Sizes):**
- `id` — PK
- `value` — уникальное (может быть «36.5»)

**Склад (Stock):**
- `id` — PK
- `product_id` — FK → Products
- `size_id` — FK → Sizes
- `quantity` — количество
- UNIQUE(`product_id`, `size_id`) — нельзя дважды одну модель+размер

**Заказы (Orders):**
- `id` — PK
- `order_date`
- `user_id` — FK → Users

**Позиции заказа (OrderItems):**
- `id` — PK
- `order_id` — FK → Orders (ON DELETE CASCADE)
- `stock_id` — FK → Stock
- `quantity`
- `unit_price` — цена на момент заказа (важно: цена может поменяться)

---

## 5. Проектирование схемы БД (3НФ)

### 5.1. Что такое 3НФ

Третья нормальная форма требует:

1. **1НФ:** все атрибуты атомарны (нет массивов в одной ячейке).
2. **2НФ:** нет частичных зависимостей неключевых атрибутов от части составного ключа.
3. **3НФ:** нет транзитивных зависимостей (неключевой атрибут не зависит от другого неключевого).

### 5.2. Проверка нашей схемы

**Пример транзитивной зависимости (если бы мы её оставили):**

Если бы в таблице `Stock` мы хранили `category_name` вместо `category_id`, то `category_name` зависело бы от `product_id`, а `product_id` — от `id`. Это транзитивная зависимость → нарушение 3НФ.

**Решение:** вынести `Categories`, `Manufacturers`, `Sizes` в отдельные справочники. Так мы и сделали.

**Пример частичной зависимости (если бы она была):**

Если бы `OrderItems` имела составной первичный ключ `(order_id, stock_id)` и хранила `unit_price`, зависящий только от `stock_id` — это частичная зависимость. У нас PK — `id`, а `order_id` и `stock_id` — внешние ключи, поэтому всё в порядке.

### 5.3. Схема связей

```
Users 1─────* Orders 1─────* OrderItems *─────1 Stock *─────1 Products *─────1 Categories
                                                       │
                                                       └────1 Manufacturers
                                              Stock *───1 Sizes
```

Типы связей:
- Users → Orders: **1:M** (один пользователь — много заказов)
- Orders → OrderItems: **1:M** (один заказ — много позиций)
- OrderItems → Stock: **M:1** (одна позиция ссылается на одну строку склада)
- Stock → Products: **M:1**
- Stock → Sizes: **M:1**
- Products → Categories: **M:1**
- Products → Manufacturers: **M:1**

---

## 6. Написание SQL-скрипта создания БД

Создайте файл `schema.sql` в папке `~/shoe_shop/`:

```bash
nano ~/shoe_shop/schema.sql
```

Вставьте следующее содержимое (скопируйте целиком):

```sql
-- ================================================================
-- Схема базы данных системы оформления заказа обуви
-- СУБД: SQLite 3
-- Все таблицы в 3-й нормальной форме
-- ================================================================

PRAGMA foreign_keys = ON;

-- Удаление в обратном порядке зависимостей
DROP TABLE IF EXISTS OrderItems;
DROP TABLE IF EXISTS Orders;
DROP TABLE IF EXISTS Stock;
DROP TABLE IF EXISTS Products;
DROP TABLE IF EXISTS Sizes;
DROP TABLE IF EXISTS Manufacturers;
DROP TABLE IF EXISTS Categories;
DROP TABLE IF EXISTS Users;

-- ----------------------------------------------------------------
-- Пользователи системы
-- ----------------------------------------------------------------
CREATE TABLE Users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name    TEXT NOT NULL,
    first_name   TEXT NOT NULL,
    middle_name  TEXT,
    login        TEXT UNIQUE NOT NULL,
    role         TEXT NOT NULL CHECK(role IN
                    ('Администратор', 'Менеджер', 'Авторизованный пользователь'))
);

-- ----------------------------------------------------------------
-- Справочник категорий
-- ----------------------------------------------------------------
CREATE TABLE Categories (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT UNIQUE NOT NULL
);

-- ----------------------------------------------------------------
-- Справочник производителей
-- ----------------------------------------------------------------
CREATE TABLE Manufacturers (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT UNIQUE NOT NULL
);

-- ----------------------------------------------------------------
-- Модели товаров
-- ----------------------------------------------------------------
CREATE TABLE Products (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id      INTEGER NOT NULL REFERENCES Categories(id),
    manufacturer_id  INTEGER NOT NULL REFERENCES Manufacturers(id),
    name             TEXT NOT NULL,
    subcategory      TEXT,
    description      TEXT,
    composition      TEXT,
    price            REAL NOT NULL CHECK(price >= 0),
    image            TEXT,
    UNIQUE(name, manufacturer_id)
);

-- ----------------------------------------------------------------
-- Справочник размеров
-- ----------------------------------------------------------------
CREATE TABLE Sizes (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    value  TEXT UNIQUE NOT NULL
);

-- ----------------------------------------------------------------
-- Склад: товар + размер + доступное количество
-- ----------------------------------------------------------------
CREATE TABLE Stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES Products(id) ON DELETE CASCADE,
    size_id     INTEGER NOT NULL REFERENCES Sizes(id),
    quantity    INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    UNIQUE(product_id, size_id)
);

-- ----------------------------------------------------------------
-- Заказы
-- ----------------------------------------------------------------
CREATE TABLE Orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_date  TEXT NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES Users(id)
);

-- ----------------------------------------------------------------
-- Позиции заказов
-- ----------------------------------------------------------------
CREATE TABLE OrderItems (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
    stock_id    INTEGER NOT NULL REFERENCES Stock(id),
    quantity    INTEGER NOT NULL CHECK(quantity > 0),
    unit_price  REAL NOT NULL CHECK(unit_price >= 0)
);

-- ----------------------------------------------------------------
-- Индексы для ускорения часто используемых запросов
-- ----------------------------------------------------------------
CREATE INDEX idx_products_category ON Products(category_id);
CREATE INDEX idx_products_manufacturer ON Products(manufacturer_id);
CREATE INDEX idx_stock_product ON Stock(product_id);
CREATE INDEX idx_orders_user ON Orders(user_id);
CREATE INDEX idx_orders_date ON Orders(order_date);
CREATE INDEX idx_orderitems_order ON OrderItems(order_id);
CREATE INDEX idx_orderitems_stock ON OrderItems(stock_id);
```

Сохраните и выйдите: в `nano` — `Ctrl+O`, `Enter`, `Ctrl+X`.

### 6.1. Ключевые моменты

- **`PRAGMA foreign_keys = ON;`** — включает проверку внешних ключей (по умолчанию в SQLite они отключены).
- **`AUTOINCREMENT`** — автоувеличение PK.
- **`UNIQUE(name, manufacturer_id)`** в Products — одна модель одного производителя не может повторяться.
- **`ON DELETE CASCADE`** в OrderItems — при удалении заказа автоматически удаляются его позиции.
- **`CHECK(...)`** — встроенная валидация данных.

---

## 7. Создание базы данных из Python

### 7.1. Быстрый способ — через sqlite3 CLI

Если установлен `sqlite3`:

```bash
cd ~/shoe_shop
sqlite3 shop.db < schema.sql
```

Проверим, что таблицы созданы:

```bash
sqlite3 shop.db ".tables"
```

Ожидаемый вывод:

```
Categories  Manufacturers  OrderItems  Orders  Products  Sizes  Stock  Users
```

### 7.2. Способ через Python (универсальный)

Создайте файл `create_db.py`:

```bash
nano ~/shoe_shop/create_db.py
```

Содержимое:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт создания базы данных системы оформления заказа обуви.
Читает schema.sql и выполняет его в новом файле shop.db.
"""

import sqlite3
import os
import sys


def create_database(db_path: str = 'shop.db', schema_path: str = 'schema.sql'):
    if not os.path.exists(schema_path):
        print(f'[ОШИБКА] Файл схемы не найден: {schema_path}')
        sys.exit(1)

    if os.path.exists(db_path):
        print(f'[ИНФО] Файл {db_path} уже существует. Удаляем...')
        os.remove(db_path)

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print(f'[OK] База данных создана: {db_path}')
    except sqlite3.Error as e:
        print(f'[ОШИБКА SQL] {e}')
        sys.exit(1)
    finally:
        conn.close()

    # Проверка списка таблиц
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()

    print('[ИНФО] Созданные таблицы:')
    for t in tables:
        print(f'   - {t}')


if __name__ == '__main__':
    create_database()
```

Запустите:

```bash
cd ~/shoe_shop
python3 create_db.py
```

Ожидаемый вывод:

```
[OK] База данных создана: shop.db
[ИНФО] Созданные таблицы:
   - Categories
   - Manufacturers
   - OrderItems
   - Orders
   - Products
   - Sizes
   - Stock
   - Users
```

---

## 8. Чтение Excel-файлов встроенными средствами

### 8.1. Как устроен .xlsx внутри

Файл `.xlsx` — это **ZIP-архив** с XML-файлами. Проверим:

```bash
cd ~/shoe_shop
unzip -l Products_import.xlsx
```

Увидим структуру:

```
Archive:  Products_import.xlsx
  Length      Date    Time    Name
---------  ---------- -----   ----
      ...  ...      xl/workbook.xml
      ...  ...      xl/worksheets/sheet1.xml
      ...  ...      xl/sharedStrings.xml
      ...  ...      xl/_rels/workbook.xml.rels
      ...
```

Значит, для чтения нам достаточно встроенных модулей:
- `zipfile` — распаковка
- `xml.etree.ElementTree` — парсинг XML
- `re` — разбор ссылок ячеек (A1, B2)

### 8.2. Основные XML-файлы xlsx

| Файл | Назначение |
|---|---|
| `xl/workbook.xml` | Список листов |
| `xl/_rels/workbook.xml.rels` | Соответствие rId → путь к листу |
| `xl/sharedStrings.xml` | Пул текстовых значений |
| `xl/worksheets/sheetN.xml` | Данные листа |

В ячейке `<c r="B2" t="s"><v>5</v></c>`:
- `r="B2"` — адрес
- `t="s"` — тип «строка» (значение — индекс в sharedStrings)
- `<v>5</v>` — значение (индекс или число)

Если `t` отсутствует — это число.

### 8.3. Простой пример чтения

Проверим работу на лету:

```bash
python3 -c "
import zipfile, xml.etree.ElementTree as ET
NS = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile('Sizes_import.xlsx') as z:
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    strings = [si.find('.//a:t', NS).text for si in root.findall('a:si', NS)]
    print('Первые 10 строк:', strings[:10])
"
```

Ожидаемый вывод — список размеров.

---

## 9. Написание скрипта импорта данных

Создайте файл `import_data.py`:

```bash
nano ~/shoe_shop/import_data.py
```

### 9.1. Полный код импорта

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Импорт данных из xlsx-файлов в SQLite.

Используются только встроенные модули Python 3.8:
  sqlite3, zipfile, xml.etree.ElementTree, os, re, sys
"""

import sqlite3
import zipfile
import xml.etree.ElementTree as ET
import os
import re
import sys
from datetime import datetime

NS = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
DB_PATH = 'shop.db'
DATA_DIR = '.'


# ----------------------------------------------------------------
# Чтение xlsx
# ----------------------------------------------------------------
def col_to_idx(col: str) -> int:
    """'A' -> 0, 'B' -> 1, ..., 'AA' -> 26"""
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - ord('A') + 1)
    return idx - 1


def read_xlsx(path: str):
    """
    Читает первый лист xlsx.
    Возвращает список строк: [[значение, значение, ...], ...]
    """
    with zipfile.ZipFile(path) as z:

        # 1. sharedStrings
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('a:si', NS):
                text = ''.join(
                    t.text or ''
                    for t in si.iter(
                        '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'
                    )
                )
                shared.append(text)

        # 2. Найти файл первого листа
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        sheets = wb.findall('.//a:sheet', NS)
        if not sheets:
            return []

        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rel_map = {r.get('Id'): r.get('Target') for r in rels}

        # У первого листа r:id
        first_sheet_rid = sheets[0].get(
            '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
        )
        target = rel_map.get(first_sheet_rid)
        if target is None:
            return []

        # Нормализуем путь
        if not target.startswith('xl/'):
            target = 'xl/' + target.lstrip('/')

        root = ET.fromstring(z.read(target))
        rows = []
        for row in root.findall('.//a:sheetData/a:row', NS):
            cells = {}
            for c in row.findall('a:c', NS):
                ref = c.get('r', '')
                m = re.match(r'[A-Z]+', ref)
                if not m:
                    continue
                idx = col_to_idx(m.group())
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
        return rows


# ----------------------------------------------------------------
# Утилиты
# ----------------------------------------------------------------
def parse_date(s: str) -> str:
    """Приводим дату к виду YYYY-MM-DD."""
    if not s:
        return ''
    s = s.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return s


def get_or_create(cur, table: str, name: str) -> int:
    """Возвращает id записи по name, создавая её при необходимости."""
    name = name.strip()
    cur.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table}(name) VALUES (?)", (name,))
    return cur.lastrowid


def log(msg: str):
    print(f'[ИМПОРТ] {msg}')


# ----------------------------------------------------------------
# Загрузка по таблицам
# ----------------------------------------------------------------
def import_sizes(cur):
    log('Читаю Sizes_import.xlsx ...')
    rows = read_xlsx(os.path.join(DATA_DIR, 'Sizes_import.xlsx'))
    for row in rows[1:]:
        if row and str(row[0]).strip():
            val = str(row[0]).strip()
            cur.execute("INSERT OR IGNORE INTO Sizes(value) VALUES (?)", (val,))
    log(f'   Размеров загружено: {cur.rowcount} (или уже было)')


def import_users(cur):
    log('Читаю Users_import.xlsx ...')
    rows = read_xlsx(os.path.join(DATA_DIR, 'Users_import.xlsx'))
    count = 0
    for row in rows[1:]:
        if len(row) < 5 or not row[3]:
            continue
        last_name = row[0].strip()
        first_name = row[1].strip()
        middle_name = row[2].strip() if len(row) > 2 else ''
        login = row[3].strip()
        role = row[4].strip()
        try:
            cur.execute("""INSERT OR IGNORE INTO Users
                           (last_name, first_name, middle_name, login, role)
                           VALUES (?,?,?,?,?)""",
                        (last_name, first_name, middle_name, login, role))
            count += 1
        except sqlite3.Error as e:
            log(f'   [!] Не удалось добавить {login}: {e}')
    log(f'   Пользователей обработано: {count}')


def import_products(cur):
    log('Читаю Products_import.xlsx ...')
    rows = read_xlsx(os.path.join(DATA_DIR, 'Products_import.xlsx'))
    count = 0
    for row in rows[1:]:
        if len(row) < 8 or not row[3]:
            continue
        category = row[0].strip()
        subcategory = row[1].strip() if len(row) > 1 else ''
        image = row[2].strip() if len(row) > 2 else ''
        name = row[3].strip()
        manufacturer = row[4].strip()
        description = row[5].strip() if len(row) > 5 else ''
        composition = row[6].strip() if len(row) > 6 else ''
        try:
            price = float(row[7])
        except (ValueError, TypeError):
            price = 0.0

        cat_id = get_or_create(cur, 'Categories', category)
        man_id = get_or_create(cur, 'Manufacturers', manufacturer)

        cur.execute("""INSERT OR IGNORE INTO Products
                       (category_id, manufacturer_id, name, subcategory,
                        description, composition, price, image)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (cat_id, man_id, name, subcategory,
                     description, composition, price, image))

        # если уже был — обновим картинку и цену
        cur.execute("""UPDATE Products
                       SET image = ?, price = ?, description = ?, composition = ?
                       WHERE name = ? AND manufacturer_id = ?""",
                    (image, price, description, composition, name, man_id))
        count += 1
    log(f'   Товаров обработано: {count}')


def import_stock(cur):
    log('Читаю Stock_Items_import.xlsx ...')
    rows = read_xlsx(os.path.join(DATA_DIR, 'Stock_Items_import.xlsx'))
    count = 0
    for row in rows[1:]:
        if len(row) < 4 or not row[0]:
            continue
        name = row[0].strip()
        man_name = row[1].strip()
        size_val = str(row[2]).strip()
        try:
            qty = int(float(row[3]))
        except (ValueError, TypeError):
            qty = 0

        cur.execute("""SELECT p.id FROM Products p
                       JOIN Manufacturers m ON m.id = p.manufacturer_id
                       WHERE p.name = ? AND m.name = ?""", (name, man_name))
        p = cur.fetchone()
        if not p:
            log(f'   [!] Товар не найден: {name} / {man_name}')
            continue

        cur.execute("SELECT id FROM Sizes WHERE value = ?", (size_val,))
        s = cur.fetchone()
        if s:
            size_id = s[0]
        else:
            cur.execute("INSERT INTO Sizes(value) VALUES (?)", (size_val,))
            size_id = cur.lastrowid

        cur.execute("""INSERT INTO Stock(product_id, size_id, quantity)
                       VALUES (?,?,?)
                       ON CONFLICT(product_id, size_id)
                       DO UPDATE SET quantity = excluded.quantity""",
                    (p[0], size_id, qty))
        count += 1
    log(f'   Строк склада обработано: {count}')


def import_orders(cur):
    log('Читаю Orders_import.xlsx ...')
    rows = read_xlsx(os.path.join(DATA_DIR, 'Orders_import.xlsx'))
    order_cache = {}
    count_orders = 0
    count_items = 0

    for row in rows[1:]:
        if len(row) < 9 or not str(row[0]).strip():
            continue

        order_num = str(row[0]).strip()
        order_date = parse_date(row[1])
        fio = row[2].strip()
        name = row[4].strip()
        man_name = row[5].strip()
        size_val = str(row[6]).strip()
        try:
            qty = int(float(row[7]))
        except (ValueError, TypeError):
            qty = 1
        try:
            price = float(row[8])
        except (ValueError, TypeError):
            price = 0.0

        # Ищем пользователя по ФИО
        parts = fio.split()
        last_name = parts[0] if len(parts) > 0 else ''
        first_name = parts[1] if len(parts) > 1 else ''
        middle_name = parts[2] if len(parts) > 2 else ''

        cur.execute("""SELECT id FROM Users
                       WHERE last_name = ? AND first_name = ?""",
                    (last_name, first_name))
        u = cur.fetchone()
        if u:
            user_id = u[0]
        else:
            login = 'guest_' + order_num
            cur.execute("""INSERT INTO Users
                           (last_name, first_name, middle_name, login, role)
                           VALUES (?,?,?,?,'Авторизованный пользователь')""",
                        (last_name, first_name, middle_name, login))
            user_id = cur.lastrowid

        # Создаём заказ
        if order_num not in order_cache:
            cur.execute("""INSERT INTO Orders(order_date, user_id)
                           VALUES (?,?)""", (order_date, user_id))
            order_cache[order_num] = cur.lastrowid
            count_orders += 1
        order_id = order_cache[order_num]

        # Ищем stock_id
        cur.execute("""SELECT s.id FROM Stock s
                       JOIN Products p ON p.id = s.product_id
                       JOIN Manufacturers m ON m.id = p.manufacturer_id
                       JOIN Sizes sz ON sz.id = s.size_id
                       WHERE p.name = ? AND m.name = ? AND sz.value = ?""",
                    (name, man_name, size_val))
        st = cur.fetchone()
        if not st:
            log(f'   [!] Позиция не найдена: {name} / {man_name} / {size_val}')
            continue

        cur.execute("""INSERT INTO OrderItems(order_id, stock_id, quantity, unit_price)
                       VALUES (?,?,?,?)""",
                    (order_id, st[0], qty, price))
        count_items += 1

    log(f'   Заказов: {count_orders}, позиций: {count_items}')


# ----------------------------------------------------------------
# Точка входа
# ----------------------------------------------------------------
def main():
    if not os.path.exists(DB_PATH):
        log(f'[ОШИБКА] Не найден файл {DB_PATH}. Сначала запустите create_db.py')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    try:
        import_sizes(cur)
        import_users(cur)
        import_products(cur)
        import_stock(cur)
        import_orders(cur)
        conn.commit()
        log('ГОТОВО. Все данные импортированы.')
    except sqlite3.Error as e:
        conn.rollback()
        log(f'[ОШИБКА SQL] {e}')
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
```

### 9.2. Разбор ключевых фрагментов

**Чтение sharedStrings:**

```python
root = ET.fromstring(z.read('xl/sharedStrings.xml'))
for si in root.findall('a:si', NS):
    text = ''.join(t.text or '' for t in si.iter('{...}t'))
```

XLSX может хранить текст фрагментами (rich text) — поэтому собираем все `<t>` внутри `<si>`.

**Разбор адреса ячейки:**

```python
ref = c.get('r')       # "B12"
col_letters = re.match(r'[A-Z]+', ref).group()  # "B"
row_number = int(re.match(r'[A-Z]+(\d+)', ref).group(1))  # 12
```

`col_to_idx("B")` = 1.

**Импорт с `ON CONFLICT`:**

```sql
INSERT INTO Stock(product_id, size_id, quantity) VALUES (?,?,?)
ON CONFLICT(product_id, size_id) DO UPDATE SET quantity = excluded.quantity
```

Это удобно: если строка уже есть — обновляем количество, иначе — создаём.

**Импорт заказов через кэш:**

```python
if order_num not in order_cache:
    cur.execute("INSERT INTO Orders(...)")
    order_cache[order_num] = cur.lastrowid
order_id = order_cache[order_num]
```

Несколько строк Orders_import.xlsx с одним и тем же номером заказа → все попадут в один заказ.

---

## 10. Запуск импорта и проверка

### 10.1. Порядок запуска

```bash
cd ~/shoe_shop

# Шаг 1. Создание схемы БД
python3 create_db.py

# Шаг 2. Импорт данных
python3 import_data.py
```

Ожидаемый вывод `import_data.py`:

```
[ИМПОРТ] Читаю Sizes_import.xlsx ...
[ИМПОРТ]    Размеров загружено: ...
[ИМПОРТ] Читаю Users_import.xlsx ...
[ИМПОРТ]    Пользователей обработано: 20
[ИМПОРТ] Читаю Products_import.xlsx ...
[ИМПОРТ]    Товаров обработано: 33
[ИМПОРТ] Читаю Stock_Items_import.xlsx ...
[ИМПОРТ]    Строк склада обработано: 95
[ИМПОРТ] Читаю Orders_import.xlsx ...
[ИМПОРТ]    Заказов: 10, позиций: 30
[ИМПОРТ] ГОТОВО. Все данные импортированы.
```

### 10.2. Проверка через sqlite3 CLI

```bash
sqlite3 shop.db
```

Внутри CLI:

```sql
.headers on
.mode column

-- Сколько всего товаров?
SELECT COUNT(*) AS total_products FROM Products;

-- Сколько заказов?
SELECT COUNT(*) AS total_orders FROM Orders;

-- Первые 5 товаров с ценой
SELECT id, name, price FROM Products LIMIT 5;

-- Все размеры
SELECT * FROM Sizes;

-- Проверим связи (JOIN)
SELECT o.id, o.order_date,
       u.last_name || ' ' || u.first_name AS client,
       COUNT(oi.id) AS items_count
FROM Orders o
JOIN Users u ON u.id = o.user_id
JOIN OrderItems oi ON oi.order_id = o.id
GROUP BY o.id
ORDER BY o.id;

-- Проверим остатки на складе
SELECT p.name, sz.value AS size, s.quantity
FROM Stock s
JOIN Products p ON p.id = s.product_id
JOIN Sizes sz ON sz.id = s.size_id
ORDER BY p.name, CAST(sz.value AS REAL);

.quit
```

### 10.3. Проверка через DB Browser for SQLite

Запустите:

```bash
sqlitebrowser ~/shoe_shop/shop.db &
```

1. Вкладка **Database Structure** — увидите все таблицы с индексами.
2. Вкладка **Browse Data** — выберите таблицу и просмотрите данные.
3. Вкладка **Execute SQL** — можно выполнять произвольные запросы.

### 10.4. Проверка ключевой логики — скидка 25%

Убедимся, что запрос для определения скидки работает. Возьмём товар без заказов в прошлом месяце:

```sql
-- Товары без заказов в прошлом месяце (получат скидку 25%)
SELECT p.id, p.name, p.price
FROM Products p
WHERE NOT EXISTS (
    SELECT 1 FROM OrderItems oi
    JOIN Stock s ON s.id = oi.stock_id
    JOIN Orders o ON o.id = oi.order_id
    WHERE s.product_id = p.id
      AND o.order_date >= '2026-04-01'
      AND o.order_date < '2026-05-01'
);
```

Этот запрос дублирует логику Python-сервера: если для товара нет заказов в предыдущем календарном месяце, применяется скидка 25%.

### 10.5. Проверка ссылочной целостности

Попробуем вставить «битую» ссылку:

```sql
INSERT INTO Stock(product_id, size_id, quantity) VALUES (99999, 1, 10);
```

Ожидаемая ошибка:

```
Error: FOREIGN KEY constraint failed
```

Значит, `PRAGMA foreign_keys = ON` работает.

---

## 11. Построение ER-диаграммы

### 11.1. Способ 1 — через DB Browser

1. Откройте `shop.db` в `sqlitebrowser`.
2. Меню **Tools → Generate ER Diagram** (в новых версиях).
3. Сохраните схему как PDF: **File → Print → Print to File (PDF)**.

### 11.2. Способ 2 — через DBeaver

1. Установите: `sudo dnf install dbeaver`.
2. Откройте DBeaver → **New Connection → SQLite** → укажите путь к `shop.db`.
3. Разверните дерево → **ER Diagram**.
4. Экспорт в PDF/PNG: **File → Save As**.

### 11.3. Способ 3 — вручную в draw.io / Dia

1. Установите: `sudo dnf install dia`.
2. Нарисуйте 8 прямоугольников с именами таблиц и их атрибутами.
3. Соедините линиями по схеме связей (см. п. 5.3).
4. Экспорт: **Файл → Экспорт → PDF**.

### 11.4. Что должно быть на ER-диаграмме

- 8 таблиц: Users, Categories, Manufacturers, Products, Sizes, Stock, Orders, OrderItems
- Атрибуты каждой таблицы
- Обозначены PK (ключ) и FK (стрелка)
- Связи с указанием кратности (1:M)

---

## 12. Сохранение результатов

По спецификации КИМ результат нужно сохранить как:

- **SQL-скрипт** БД (`schema.sql`) — уже есть.
- **Файл БД с данными** (`shop.db`) — уже есть.
- **Файл конфигурации `.dt` для 1С** — если сдаёте на 1С, делайте через платформу; если на Python — не требуется.
- **ER-диаграмма в PDF** — сохраните как `ER_diagram.pdf`.

Структура папки к концу части 1:

```
~/shoe_shop/
├── Products_import.xlsx
├── Stock_Items_import.xlsx
├── Sizes_import.xlsx
├── Orders_import.xlsx
├── Users_import.xlsx
├── schema.sql
├── create_db.py
├── import_data.py
├── shop.db
├── ER_diagram.pdf
└── static/
    └── uploads/
        ├── picture.png
        └── IMG_*.png
```

### 12.1. Добавляем в Git

```bash
cd ~/shoe_shop
git init
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
EOF

git add schema.sql create_db.py import_data.py shop.db ER_diagram.pdf
git add static/
git add *.xlsx
git commit -m "Часть 1: создание БД и импорт данных из Excel"
```

---

## 13. Типичные ошибки и их решение

### 13.1. `ModuleNotFoundError: No module named 'sqlite3'`

**Причина:** Python собран без SQLite.

**Решение:**

```bash
sudo dnf install python3-sqlite
```

### 13.2. `sqlite3.OperationalError: no such table: Products`

**Причина:** не запущен `create_db.py`, либо запущен не в той папке.

**Решение:**

```bash
cd ~/shoe_shop
ls -la shop.db      # проверить наличие файла
python3 create_db.py
```

### 13.3. `zipfile.BadZipFile: File is not a zip file`

**Причина:** файл `*.xlsx` повреждён или это на самом деле `.xls` (старый формат).

**Решение:** проверьте расширение через `file`:

```bash
file Products_import.xlsx
# Должно вывести: Microsoft Excel 2007+
```

Если `.xls` — конвертируйте через LibreOffice:

```bash
libreoffice --headless --convert-to xlsx Products_import.xls
```

### 13.4. `KeyError` при разборе sharedStrings

**Причина:** индекс ячейки `t="s"` выходит за границы `sharedStrings` — обычно из-за того, что в xlsx другой лист.

**Решение:** убедитесь, что вы читаете именно `sheet1.xml`, и что в `xl/_rels/workbook.xml.rels` правильно указан target. Наш скрипт берёт первый лист — этого достаточно для файлов КИМ.

### 13.5. Импорт идёт, но таблица Stock пустая

**Причина:** имена товаров в Stock_Items_import не совпадают с Products_import (пробелы, кавычки, регистр).

**Решение:** проверьте несовпадающие записи — скрипт выводит сообщения `[!] Товар не найден: ...`. Сравните строки в обоих файлах. При необходимости нормализуйте:

```python
name = row[0].strip().replace('«','"').replace('»','"')
```

### 13.6. `FOREIGN KEY constraint failed` при импорте

**Причина:** для Stock ссылается на product_id, а товар не найден; или Categories/Manufacturers не создались.

**Решение:** скрипт использует `get_or_create` для категорий/производителей — они создадутся автоматически. Проверьте порядок вызова функций в `main()`: сначала справочники, потом товары, потом склад, потом заказы.

### 13.7. Импорт дублирует записи при повторном запуске

**Причина:** `INSERT` без `OR IGNORE`/`ON CONFLICT`.

**Решение:** либо удалите `shop.db` и пересоздайте (`python3 create_db.py`), либо добавьте уникальность. В нашем скрипте:
- Users: `INSERT OR IGNORE` по `login`
- Products: `INSERT OR IGNORE` по `UNIQUE(name, manufacturer_id)`
- Stock: `ON CONFLICT DO UPDATE`

Заказы пересоздавать нелья (id растёт) — при повторном запуске лучше всего удалять БД и создавать заново.

### 13.8. Кириллица отображается «крякозябрами» в sqlitebrowser

**Причина:** кодировка шрифта в Qt-приложении.

**Решение:** в DB Browser: **Edit → Preferences → Data Browser → Default encoding → UTF-8**. Или обновите систему: `sudo dnf update`.

### 13.9. Права доступа в ROSA

Если запускаете скрипт из-под root, файл `shop.db` может стать недоступен для обычного пользователя.

**Решение:** не работайте под root; используйте `sudo` только для установки пакетов.

### 13.10. Медленный импорт

**Причина:** SQLite по умолчанию делает commit после каждого INSERT.

**Решение:** обернуть импорт в одну транзакцию:

```python
conn.execute("BEGIN")
# ... все вставки ...
conn.commit()
```

В нашем скрипте уже сделан один `conn.commit()` в конце `main()`.

---

## Итог

По завершении этой части у вас есть:

1. **Спроектированная БД в 3НФ** (8 таблиц, связи, индексы).
2. **SQL-скрипт** `schema.sql`.
3. **Файл БД** `shop.db` со всеми импортированными данными.
4. **Скрипты** `create_db.py` и `import_data.py`, использующие только встроенные модули Python 3.8.
5. **ER-диаграмма** в PDF.

Следующий шаг — реализация backend и frontend (см. предыдущую инструкцию по `server.py` и `app.js`). 
