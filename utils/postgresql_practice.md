
# Базовые команды PostgreSQL: просмотр таблиц и работа с БД


## 1. Подключение к базе данных

### 1.1. Подключение через psql

```bash
psql -U conference_user -d conference_db -h 127.0.0.1
```

**Пояснение параметров:**

| Параметр | Значение | Описание |
|----------|----------|----------|
| `-U` | `conference_user` | Имя пользователя БД |
| `-d` | `conference_db` | Имя базы данных |
| `-h` | `127.0.0.1` | Хост (localhost) |
| `-p` | `5432` | Порт (по умолчанию) |

После ввода пароля вы увидите приглашение:

```
conference_db=>
```

### 1.2. Подключение под суперпользователем postgres

```bash
sudo su - postgres
psql
```

### 1.3. Быстрое подключение одной командой

```bash
psql -U conference_user -d conference_db -h 127.0.0.1 -c "SELECT version();"
```

---

## 2. Просмотр таблиц

### 2.1. Список всех таблиц

**Мета-команда:**

```sql
\dt
```

**Ожидаемый вывод:**

```
          List of relations
 Schema |  Name   | Type  |     Owner
--------+---------+-------+----------------
 public | event   | table | conference_user
 public | request | table | conference_user
 public | review  | table | conference_user
 public | status  | table | conference_user
 public | user    | table | conference_user
(5 rows)
```

**SQL-эквивалент:**

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

### 2.2. Список таблиц с дополнительной информацией

```sql
\dt+
```

Показывает размер таблиц, описание, владельца.

### 2.3. Список всех схем

```sql
\dn
```

### 2.4. Список всех баз данных

```sql
\l
```

**Или SQL:**

```sql
SELECT datname FROM pg_database WHERE datistemplate = false;
```

---

## 3. Просмотр структуры таблицы

### 3.1. Структура конкретной таблицы

```sql
\d user
```

**Ожидаемый вывод:**

```
                       Table "public.user"
     Column     |          Type          | Collation | Nullable | Default
----------------+------------------------+-----------+----------+-----------------------------------
 id             | integer                |           | not null | nextval('user_id_seq'::regclass)
 login          | character varying(50)  |           | not null |
 password_hash  | character varying(255) |           | not null |
 email          | character varying(100) |           | not null |
 phone          | character varying(18)  |           | not null |
 role           | character varying(20)  |           | not null | 'user'::character varying
Indexes:
    "user_pkey" PRIMARY KEY, btree (id)
    "user_login_key" UNIQUE CONSTRAINT, btree (login)
    "user_email_key" UNIQUE CONSTRAINT, btree (email)
```

### 3.2. Расширенная информация о таблице

```sql
\d+ user
```

Показывает размер, описание, метод доступа.

### 3.3. Структура всех таблиц

```sql
\d
```

Показывает последовательно все таблицы, индексы, последовательности.

### 3.4. Только индексы

```sql
\di
```

### 3.5. Только последовательности

```sql
\ds
```

### 3.6. Просмотр внешних ключей

```sql
\d request
```

**Фрагмент вывода:**

```
Foreign-key constraints:
    "request_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id)
    "request_event_id_fkey" FOREIGN KEY (event_id) REFERENCES event(id)
    "request_status_id_fkey" FOREIGN KEY (status_id) REFERENCES status(id)
```

**SQL-эквивалент:**

```sql
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'request';
```

---

## 4. Просмотр данных

### 4.1. Все записи из таблицы

```sql
SELECT * FROM "user";
```

> **Важно:** `user` — зарезервированное слово, поэтому используется в кавычках.

### 4.2. Первые N записей

```sql
SELECT * FROM "user" LIMIT 10;
```

### 4.3. Записи с сортировкой

```sql
SELECT * FROM request ORDER BY created_at DESC;
```

### 4.4. Записи с фильтром

```sql
SELECT * FROM "user" WHERE role = 'admin';
```

### 4.5. Количество записей

```sql
SELECT COUNT(*) FROM "user";
```

### 4.6. Красивый вывод

Перед запросом выполните:

```sql
\x on
```

**Результат:** каждая запись отображается в виде «поле = значение»:

```
-[ RECORD 1 ]-+---------------------------
id            | 1
login         | Conf2027
email         | admin@conf2027.ru
phone         | 8(999)000-00-00
role          | admin
```

Отключить: `\x off`

### 4.7. Постраничный вывод

```sql
\pset pager on
```

Автоматически включает `less` для длинных таблиц.

---

## 5. Работа с таблицами (DDL)

### 5.1. Создание таблицы

```sql
CREATE TABLE test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2. Удаление таблицы

```sql
DROP TABLE test_table;
```

**С проверкой существования:**

```sql
DROP TABLE IF EXISTS test_table;
```

### 5.3. Изменение структуры таблицы

**Добавить колонку:**

```sql
ALTER TABLE "user" ADD COLUMN fio VARCHAR(150);
```

**Удалить колонку:**

```sql
ALTER TABLE "user" DROP COLUMN fio;
```

**Переименовать колонку:**

```sql
ALTER TABLE "user" RENAME COLUMN phone TO phone_number;
```

**Изменить тип:**

```sql
ALTER TABLE "user" ALTER COLUMN phone TYPE VARCHAR(25);
```

### 5.4. Переименование таблицы

```sql
ALTER TABLE test_table RENAME TO new_test_table;
```

### 5.5. Очистка таблицы

**Удалить все записи (сохранить структуру):**

```sql
TRUNCATE TABLE request;
```

**С каскадом (удалить зависимые записи):**

```sql
TRUNCATE TABLE "user" CASCADE;
```

---

## 6. Работа с данными (DML)

### 6.1. Вставка записи

```sql
INSERT INTO "user" (login, password_hash, email, phone, role)
VALUES ('testuser', 'hash123', 'test@mail.ru', '8(999)123-45-67', 'user');
```

**С возвратом id:**

```sql
INSERT INTO "user" (login, password_hash, email, phone, role)
VALUES ('testuser2', 'hash456', 'test2@mail.ru', '8(999)123-45-68', 'user')
RETURNING id;
```

### 6.2. Обновление записи

```sql
UPDATE "user" SET role = 'admin' WHERE login = 'testuser';
```

**С возвратом:**

```sql
UPDATE request SET status_id = 2 WHERE id = 1 RETURNING *;
```

### 6.3. Удаление записи

```sql
DELETE FROM "user" WHERE login = 'testuser';
```

### 6.4. Игнорирование дубликатов

```sql
INSERT INTO status (name) VALUES ('Новая')
ON CONFLICT (name) DO NOTHING;
```

---

## 7. Управление пользователями и правами

### 7.1. Список пользователей БД

```sql
\du
```

**Или SQL:**

```sql
SELECT usename FROM pg_user;
```

### 7.2. Создание пользователя

```sql
CREATE USER new_user WITH PASSWORD 'password123';
```

### 7.3. Права на базу данных

```sql
GRANT ALL PRIVILEGES ON DATABASE conference_db TO new_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO new_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO new_user;
```

### 7.4. Изменение пароля

```sql
ALTER USER conference_user WITH PASSWORD 'new_password';
```

### 7.5. Удаление пользователя

```sql
DROP USER new_user;
```

### 7.6. Смена владельца таблицы

```sql
ALTER TABLE "user" OWNER TO conference_user;
```

---

## 8. Мета-команды psql (полный список)

### 8.1. Информационные команды

| Команда | Описание |
|---------|----------|
| `\l` | Список баз данных |
| `\l+` | Список БД с размерами |
| `\dt` | Список таблиц |
| `\dt+` | Таблицы с размерами |
| `\d имя_таблицы` | Структура таблицы |
| `\d+ имя_таблицы` | Расширенная структура |
| `\di` | Список индексов |
| `\ds` | Список последовательностей |
| `\dv` | Список представлений |
| `\df` | Список функций |
| `\dn` | Список схем |
| `\du` | Список пользователей |
| `\dp` | Права доступа |
| `\dg` | Список групп |

### 8.2. Команды вывода

| Команда | Описание |
|---------|----------|
| `\x` | Переключить расширенный вывод |
| `\x on` | Включить расширенный вывод |
| `\x off` | Отключить |
| `\H` | HTML-вывод |
| `\t` | Только кортежи (без заголовков) |
| `\pset pager on` | Постраничный вывод |
| `\pset null 'NULL'` | Отображение NULL |
| `\timing` | Показать время выполнения |

### 8.3. Команды работы с файлами

| Команда | Описание |
|---------|----------|
| `\i file.sql` | Выполнить SQL-скрипт |
| `\o file.txt` | Перенаправить вывод в файл |
| `\o` | Вернуть вывод в терминал |
| `\copy` | Копирование данных |
| `\e` | Открыть редактор |
| `\w file.sql` | Записать буфер в файл |
| `\r` | Сбросить буфер |

### 8.4. Команды управления

| Команда | Описание |
|---------|----------|
| `\q` | Выход |
| `\c db_name` | Переключиться на другую БД |
| `\c db_name user` | Переключиться с пользователем |
| `\conninfo` | Информация о текущем подключении |
| `\!` | Выполнить shell-команду |
| `\?` | Справка по мета-командам |
| `\h` | Справка по SQL |
| `\h SELECT` | Справка по конкретной команде |

### 8.5. Команды редактирования

| Команда | Описание |
|---------|----------|
| `\e` | Открыть редактор |
| `\p` | Показать текущий буфер |
| `\g` | Выполнить буфер |
| `\gx` | Выполнить с расширенным выводом |
| `\s` | История команд |
| `\s file.txt` | Сохранить историю в файл |

---

## 9. Просмотр размеров и производительности

### 9.1. Размер базы данных

```sql
SELECT pg_size_pretty(pg_database_size('conference_db'));
```

### 9.2. Размер всех таблиц

```sql
SELECT
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;
```

### 9.3. Размер конкретной таблицы

```sql
SELECT pg_size_pretty(pg_total_relation_size('request'));
```

### 9.4. Активные подключения

```sql
SELECT pid, usename, application_name, state
FROM pg_stat_activity
WHERE datname = 'conference_db';
```

### 9.5. Время выполнения запроса

Включите таймер:

```sql
\timing
```

Теперь после каждого запроса будет отображаться время:

```
Time: 12.345 ms
```

---

## 10. Экспорт и импорт данных

### 10.1. Экспорт базы данных (pg_dump)

```bash
pg_dump -U conference_user -h 127.0.0.1 conference_db > backup.sql
```

### 10.2. Экспорт только схемы

```bash
pg_dump -U conference_user -h 127.0.0.1 --schema-only conference_db > schema_only.sql
```

### 10.3. Экспорт только данных

```bash
pg_dump -U conference_user -h 127.0.0.1 --data-only conference_db > data_only.sql
```

### 10.4. Импорт из дампа

```bash
psql -U conference_user -d conference_db -h 127.0.0.1 -f backup.sql
```

### 10.5. Экспорт в CSV

```sql
\copy (SELECT * FROM "user") TO '/tmp/users.csv' CSV HEADER;
```

### 10.6. Импорт из CSV

```sql
\copy "user"(login, password_hash, email, phone, role) FROM '/tmp/users.csv' CSV HEADER;
```

---

## 11. Управление сервером PostgreSQL (systemctl)

| Команда | Описание |
|---------|----------|
| `sudo systemctl start postgresql` | Запуск |
| `sudo systemctl stop postgresql` | Остановка |
| `sudo systemctl restart postgresql` | Перезапуск |
| `sudo systemctl status postgresql` | Статус |
| `sudo systemctl enable postgresql` | Автозапуск |
| `sudo systemctl disable postgresql` | Отключить автозапуск |

---

## 12. Практические примеры для проекта «Конференции.РФ»

### 12.1. Проверка всех таблиц

```sql
\dt
```

### 12.2. Просмотр всех пользователей

```sql
SELECT id, login, email, role FROM "user";
```

### 12.3. Просмотр всех заявок с деталями

```sql
SELECT
    r.id,
    u.login,
    e.name AS event_name,
    s.name AS status_name,
    r.created_at
FROM request r
JOIN "user" u ON r.user_id = u.id
JOIN event e ON r.event_id = e.id
JOIN status s ON r.status_id = s.id
ORDER BY r.created_at DESC;
```

### 12.4. Проверка администратора

```sql
SELECT * FROM "user" WHERE role = 'admin';
```

### 12.5. Смена статуса заявки

```sql
UPDATE request SET status_id = 2 WHERE id = 1 RETURNING *;
```

### 12.6. Количество заявок по статусам

```sql
SELECT s.name, COUNT(r.id) AS total
FROM status s
LEFT JOIN request r ON r.status_id = s.id
GROUP BY s.name;
```

### 12.7. Удаление тестовых данных

```sql
DELETE FROM request WHERE user_id IN (
    SELECT id FROM "user" WHERE login LIKE 'test%'
);
DELETE FROM "user" WHERE login LIKE 'test%';
```

---

## 13. Шпаргалка: топ-20 команд

| № | Команда | Что делает |
|---|---------|------------|
| 1 | `\l` | Список баз данных |
| 2 | `\dt` | Список таблиц |
| 3 | `\d user` | Структура таблицы `user` |
| 4 | `\d+ user` | Расширенная структура |
| 5 | `\du` | Список пользователей |
| 6 | `\di` | Список индексов |
| 7 | `\x` | Расширенный вывод |
| 8 | `\q` | Выход |
| 9 | `\c db_name` | Подключиться к БД |
| 10 | `\timing` | Таймер |
| 11 | `\i file.sql` | Выполнить скрипт |
| 12 | `\?` | Справка по мета-командам |
| 13 | `\h` | Справка по SQL |
| 14 | `\conninfo` | Информация о подключении |
| 15 | `SELECT * FROM "user";` | Все пользователи |
| 16 | `SELECT COUNT(*) FROM request;` | Количество заявок |
| 17 | `SELECT version();` | Версия PostgreSQL |
| 18 | `SELECT current_database();` | Текущая БД |
| 19 | `SELECT current_user;` | Текущий пользователь |
| 20 | `\copy ... TO ...` | Экспорт в CSV |

---

## 14. Возможные проблемы и решения

| Проблема | Решение |
|----------|---------|
| `\dt` ничего не показывает | Проверьте схему: `SET search_path TO public;` |
| `relation "user" does not exist` | Используйте `"user"` в кавычках |
| `permission denied for table` | Дайте права: `GRANT ALL ON ... TO ...` |
| `password authentication failed` | Проверьте пароль в `DATABASE_URL` |
| `could not connect to server` | `sudo systemctl start postgresql` |
| `database does not exist` | Создайте: `createdb -O user db_name` |
| Медленный вывод | `\pset pager on` |
| Длинный вывод обрезается | Используйте `\x on` |

---

## 15. Заключение

Теперь вы знаете **все базовые команды PostgreSQL**, необходимые для работы с проектом «Конференции.РФ»:

- ✅ Просмотр таблиц (`\dt`, `\d`, `\d+`)
- ✅ Просмотр данных (`SELECT`, `\x`)
- ✅ Работа со структурой (`CREATE`, `ALTER`, `DROP`)
- ✅ Управление пользователями (`\du`, `GRANT`)
- ✅ Экспорт/импорт (`pg_dump`, `\copy`)
- ✅ Управление сервером (`systemctl`)

**Рекомендация:** сохраните эту инструкцию как шпаргалку и используйте при работе с проектом. Для углублённого изучения обратитесь к официальной документации PostgreSQL: https://www.postgresql.org/docs/
