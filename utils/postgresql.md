# Использование PostgreSQL в проекте «Конференции.РФ» (ROSА Linux)

## Введение

## Шаг 1. Установка PostgreSQL в ROSA Linux

### 1.1. Установка пакетов

В ROSA Linux используется менеджер пакетов `dnf` :

```bash
sudo dnf install postgresql-server postgresql-contrib
```

**Пояснение:**
- `postgresql-server` — сервер базы данных 
- `postgresql-contrib` — дополнительные модули и утилиты 

### 1.2. Инициализация базы данных

```bash

# Инициализация БД
sudo su - postgres
initdb -D /var/lib/pgsql/data
exit

# Запуск службы
sudo systemctl start postgresql12.service
sudo systemctl enable postgresql12.service

# Проверка
sudo systemctl status postgresql12.service

# Вход в psql
sudo -u postgres psql

# Внутри psql — работа с базой
\l              # список баз данных
\du             # список ролей
SELECT version();
\q              # выход
```

### 1.3. Запуск и автозагрузка

```bash
# Запуск сервера
sudo systemctl start postgresql12.service

# Включение автозапуска
sudo systemctl enable postgresql12.service
```

**Проверка статуса:**

```bash
sudo systemctl status postgresql12.service
```

**Ожидаемый вывод:**
```
● postgresql.service - PostgreSQL database server
   Active: active (running)
```

### 1.4. Проверка установки

```bash
psql --version
```

**Ожидаемый результат:**
```
psql (PostgreSQL) 16.x
```

---

## Шаг 2. Создание пользователя и базы данных

### 2.1. Переключение на пользователя postgres

PostgreSQL создаёт системного пользователя `postgres` с правами администратора БД:

```bash
sudo su - postgres
```

### 2.2. Создание пользователя БД

```bash
createuser -P conference_user
```

**Система запросит пароль.** Введите, например:
```
Enter password for new role: Conf2027!
Enter it again: Conf2027!
```

**Пояснение:** флаг `-P` создаёт пользователя с паролем .

### 2.3. Создание базы данных

```bash
createdb -O conference_user conference_db
```

**Пояснение:**
- `-O conference_user` — владелец базы 
- `conference_db` — имя базы данных

### 2.4. Проверка подключения

```bash
psql -U conference_user -d conference_db -h 127.0.0.1
```

Введите пароль `Conf2027!`. Если подключение успешно, вы увидите приглашение:

```
conference_db=>
```

Выход: `\q`

### 2.5. Возврат к обычному пользователю

```bash
exit
```

---

## Шаг 3. Обновление schema.sql для PostgreSQL

### 3.1. Синтаксические различия SQLite и PostgreSQL

| SQLite | PostgreSQL | Пояснение |
|--------|------------|-----------|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` | Автоинкремент  |
| `?` (плейсхолдер) | `%s` | Параметры запроса  |
| `INSERT OR IGNORE` | `INSERT ... ON CONFLICT DO NOTHING` | Игнорирование дубликатов  |
| `DATETIME` | `TIMESTAMP` | Тип даты-времени |
| `PRAGMA foreign_keys = ON` | Не требуется | PostgreSQL поддерживает FK нативно  |

### 3.2. Обновлённый schema.sql

Создайте файл `schema_postgres.sql`:

```sql
-- Таблица «Пользователь»
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    login VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(18) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user'
);

-- Таблица «Мероприятие»
CREATE TABLE IF NOT EXISTS event (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    place VARCHAR(200) NOT NULL,
    description TEXT
);

-- Таблица «Статус»
CREATE TABLE IF NOT EXISTS status (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Наполнение справочника статусов
INSERT INTO status (name) VALUES 
    ('Новая'),
    ('Мероприятие назначено'),
    ('Завершено')
ON CONFLICT (name) DO NOTHING;

-- Таблица «Заявка»
CREATE TABLE IF NOT EXISTS request (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    event_id INTEGER NOT NULL REFERENCES event(id),
    status_id INTEGER NOT NULL DEFAULT 1 REFERENCES status(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Таблица «Отзыв»
CREATE TABLE IF NOT EXISTS review (
    id SERIAL PRIMARY KEY,
    request_id INTEGER UNIQUE NOT NULL REFERENCES request(id),
    text TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

> **Внимание:** `user` — зарезервированное слово в PostgreSQL, поэтому используется в кавычках `"user"`.

### 3.3. Применение схемы

```bash
psql -U conference_user -d conference_db -h 127.0.0.1 -f schema_postgres.sql
```

Введите пароль. Если ошибок нет — таблицы созданы.

**Проверка:**

```bash
psql -U conference_user -d conference_db -h 127.0.0.1 -c "\dt"
```

---

## Шаг 4. Установка драйвера psycopg2

### 4.1. Активация виртуального окружения

```bash
cd ~/conference_portal
source venv/bin/activate
```

### 4.2. Установка psycopg2-binary

```bash
pip install psycopg2-binary
```

**Пояснение:** `psycopg2-binary` — драйвер Python для PostgreSQL, не требует компиляции .

### 4.3. Обновление requirements.txt

```bash
pip freeze > requirements.txt
```

**Содержимое:**
```
Flask==2.3.3
Werkzeug==2.3.7
psycopg2-binary==2.9.9
python-dotenv==1.0.0
```

---

## Шаг 5. Обновление database.py

### 5.1. Новый класс Database

Замените содержимое `backend/database.py`:

```python
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()


class Database:
    """Singleton-класс для работы с PostgreSQL."""
    _instance = None

    def __new__(cls, db_url=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_url=None):
        if self._initialized:
            return
        if db_url is None:
            db_url = os.environ.get(
                'DATABASE_URL',
                'postgresql://conference_user:Conf2027!@127.0.0.1:5432/conference_db'
            )
        self.db_url = db_url
        self._initialized = True

    def get_connection(self):
        conn = psycopg2.connect(self.db_url)
        return conn

    def execute(self, query, params=()):
        """Выполнить INSERT / UPDATE / DELETE с возвратом id."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                # Для INSERT с RETURNING
                try:
                    result = cursor.fetchone()
                    return result[0] if result else None
                except psycopg2.ProgrammingError:
                    return None

    def fetch_one(self, query, params=()):
        """Получить одну запись как словарь."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None

    def fetch_all(self, query, params=()):
        """Получить все записи как список словарей."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
```

**Ключевые изменения:**
- `sqlite3.connect()` → `psycopg2.connect()` 
- `sqlite3.Row` → `psycopg2.extras.RealDictCursor` 
- `PRAGMA foreign_keys` — не нужен (PostgreSQL поддерживает FK нативно) 

### 5.2. Обновление .env

Создайте файл `.env` в корне проекта:

```
DATABASE_URL=postgresql://conference_user:Conf2027!@127.0.0.1:5432/conference_db
FLASK_SECRET_KEY=your-secret-key-here
```

Установите `python-dotenv`:

```bash
pip install python-dotenv
```

---

## Шаг 6. Замена плейсхолдеров `?` на `%s`

### 6.1. Проблема

SQLite использует `?` для параметров, PostgreSQL (psycopg2) — `%s` .

### 6.2. Замена во всех моделях

**Пример для `user.py`:**

**Было (SQLite):**
```python
row = self.db.fetch_one(
    "SELECT id FROM user WHERE login = ?", (self.login,)
)
```

**Стало (PostgreSQL):**
```python
row = self.db.fetch_one(
    'SELECT id FROM "user" WHERE login = %s', (self.login,)
)
```

**Пример для `request.py`:**

**Было:**
```python
db.fetch_all(
    """SELECT r.id, e.name AS event_name, ...
       WHERE r.user_id = ?""",
    (user_id,)
)
```

**Стало:**
```python
db.fetch_all(
    """SELECT r.id, e.name AS event_name, ...
       WHERE r.user_id = %s""",
    (user_id,)
)
```

### 6.3. Полный список замен

| Файл | Метод | Что заменить |
|------|-------|--------------|
| `user.py` | `login_exists()` | `?` → `%s`, `user` → `"user"` |
| `user.py` | `email_exists()` | `?` → `%s`, `user` → `"user"` |
| `user.py` | `authenticate()` | `?` → `%s`, `user` → `"user"` |
| `user.py` | `save()` | `?` → `%s`, `user` → `"user"`, добавить `RETURNING id` |
| `request.py` | `get_by_user()` | `?` → `%s` |
| `request.py` | `update_status()` | `?` → `%s` |
| `event.py` | `save()` | `?` → `%s`, добавить `RETURNING id` |
| `review.py` | `save()` | `?` → `%s`, добавить `RETURNING id` |

### 6.4. Пример обновлённого метода save() для User

```python
def save(self) -> tuple:
    ok, msg = self.validate()
    if not ok:
        return False, msg
    if self.login_exists():
        return False, "Пользователь с таким логином уже существует"
    if self.email_exists():
        return False, "Пользователь с таким email уже существует"

    password_hash = generate_password_hash(self.password)
    
    user_id = self.db.execute(
        """INSERT INTO "user" (login, password_hash, email, phone, role)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING id""",
        (self.login, password_hash, self.email, self.phone, self.role)
    )
    self.id = user_id
    return True, user_id
```

**Пояснение:** `RETURNING id` — синтаксис PostgreSQL для получения сгенерированного ID .

---

## Шаг 7. Обновление обработки ошибок

### 7.1. Замена исключений

**Было (SQLite):**
```python
import sqlite3

try:
    ...
except sqlite3.IntegrityError:
    ...
```

**Стало (PostgreSQL):**
```python
from psycopg2 import errors

try:
    ...
except errors.UniqueViolation:
    ...
except errors.IntegrityError:
    ...
```

---

## Шаг 8. Проверка и тестирование

### 8.1. Запуск приложения

```bash
source venv/bin/activate
python -m backend.app
```

**Ожидаемый вывод:**
```
✓ Администратор Conf2027 создан
 * Running on http://127.0.0.1:5000
```

### 8.2. Проверка через psql

```bash
psql -U conference_user -d conference_db -h 127.0.0.1 -c 'SELECT * FROM "user";'
```

**Ожидаемый результат:** таблица с администратором `Conf2027`.

### 8.3. Тестовые сценарии

| Действие | Ожидаемый результат |
|----------|---------------------|
| Регистрация нового пользователя | ✅ Запись появляется в БД |
| Вход под администратором | ✅ Перенаправление на `/admin` |
| Создание заявки | ✅ Запись в таблице `request` |
| Смена статуса | ✅ Обновление `status_id` |

---

## Шаг 9. Миграция существующих данных (если есть)

Если в SQLite уже есть данные, которые нужно перенести:

### 9.1. Экспорт из SQLite

```bash
sqlite3 database/conference.db .dump > dump_sqlite.sql
```

### 9.2. Конвертация дампа

Замените в `dump_sqlite.sql`:
- `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY`
- `?` → `%s` (если есть)
- `"user"` → `"user"` (зарезервированное слово)

### 9.3. Импорт в PostgreSQL

```bash
psql -U conference_user -d conference_db -h 127.0.0.1 -f dump_sqlite.sql
```

---
