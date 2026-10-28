# Практическая работа №2: Базовые CRUD-операции через консоль

## 📚 Теоретическая справка

### Что такое CRUD

**CRUD** — аббревиатура от четырёх базовых операций с данными:

| Буква | Операция | SQL-команда | Смысл |
|---|---|---|---|
| **C** | Create (создать) | `INSERT` | Добавить новую запись |
| **R** | Read (прочитать) | `SELECT` | Получить записи из базы |
| **U** | Update (обновить) | `UPDATE` | Изменить существующую запись |
| **D** | Delete (удалить) | `DELETE` | Удалить запись |

Любое приложение (интернет-магазин, соцсеть, список задач) — это, по сути, набор CRUD-операций над разными сущностями. Освоив этот шаблон, ты сможешь работать с любой базой.

### Что такое параметризованный запрос и SQL-инъекция

**SQL-инъекция** — атака, при которой злоумышленник вставляет SQL-код через поле ввода. Пример **опасного** кода:

```python
# ❌ ТАК ДЕЛАТЬ НЕЛЬЗЯ
title = input("Введите задачу: ")
cursor.execute(f"INSERT INTO tasks (title) VALUES ('{title}')")
```

Если пользователь введёт `'); DROP TABLE tasks; --`, таблица будет **удалена**.

**Правильный способ** — параметризованный запрос с плейсхолдером `?`:

```python
# ✅ ТАК ПРАВИЛЬНО
cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
```

SQLite сам подставит значение, экранировав все опасные символы. Значение передаётся **вторым аргументом** в виде кортежа. Запомни это правило раз и навсегда — оно обязательно на демоэкзамене.

> **Обрати внимание:** `(title,)` — кортеж из одного элемента. Запятая обязательна, иначе Python воспримет это как просто строку в скобках.

### Как читать данные: `fetchone()` vs `fetchall()`

После `SELECT` результат нужно забрать из курсора:

- `cursor.fetchone()` — вернёт **одну** строку (кортеж) или `None`, если строк нет. Для запросов с `WHERE id = ?`.
- `cursor.fetchall()` — вернёт **список** всех строк. Для запросов «покажи всё».

### Как получить id только что вставленной строки

После `INSERT` полезно узнать, какой `id` присвоила база. Для этого есть `cursor.lastrowid`:

```python
cursor.execute("INSERT INTO tasks (title) VALUES (?)", ("Новая задача",))
new_id = cursor.lastrowid   # например, 5
conn.commit()
```

---

## 🎯 Пошаговая инструкция

### Шаг 1. Подготовка

Убедись, что Практическая работа №1 выполнена: в папке проекта есть файл `app.db` с таблицей `tasks`.

Создай новый файл `crud_console.py` в той же папке:

```
task_manager/
├── init_db.py
├── check_db.py
├── app.db
└── crud_console.py   ← новый файл
```

### Шаг 2. Каркас приложения с меню

Начнём с «скелета» — меню и цикла, который позволяет выполнять действия, пока пользователь не выйдет.

```python
import sqlite3


def get_connection():
    """Открывает соединение с базой. Вынесено в функцию, чтобы не дублировать код."""
    return sqlite3.connect('app.db')


def show_menu():
    print("\n===== СПИСОК ЗАДАЧ =====")
    print("1. Показать все задачи")
    print("2. Добавить задачу")
    print("3. Отметить задачу выполненной")
    print("4. Удалить задачу")
    print("0. Выход")


def main():
    while True:
        show_menu()
        choice = input("Выбери действие: ").strip()

        if choice == '1':
            list_tasks()
        elif choice == '2':
            add_task()
        elif choice == '3':
            mark_done()
        elif choice == '4':
            delete_task()
        elif choice == '0':
            print("До встречи!")
            break
        else:
            print("⚠ Нет такого пункта. Попробуй снова.")


if __name__ == '__main__':
    main()
```

Запусти — меню работает, но действия пока ничего не делают. Сейчас добавим каждую функцию.

### Шаг 3. READ — показать все задачи

```python
def list_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    # SELECT не меняет данные, поэтому commit не нужен.
    cursor.execute("SELECT id, title, status FROM tasks ORDER BY id")
    rows = cursor.fetchall()

    conn.close()

    if not rows:
        print("📭 Список пуст. Добавь первую задачу!")
        return

    print("\n--- ТВОИ ЗАДАЧИ ---")
    for row in rows:
        task_id, title, status = row     # распаковка кортежа
        mark = "✅" if status == 'done' else "⬜"
        print(f"{task_id:>3}. {mark} {title}  [{status}]")
```

**Разбор:**
- `ORDER BY id` — сортировка по возрастанию id (старые сверху).
- `row` — это кортеж `(id, title, status)`. Распаковываем в три переменные.
- `f"{task_id:>3}"` — выравнивание id по правому краю шириной 3 символа (для красоты).

**Последовательность транзакций:** подключение → SELECT → fetchall → закрытие. `commit()` не нужен, потому что данные не меняются.

### Шаг 4. CREATE — добавить задачу

```python
def add_task():
    title = input("Название задачи: ").strip()

    if not title:
        print("⚠ Название не может быть пустым.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks (title) VALUES (?)",
        (title,)                # ← кортеж! Запятая обязательна.
    )
    conn.commit()               # ← фиксация на диск
    new_id = cursor.lastrowid   # ← id вставленной строки (до закрытия!)

    conn.close()
    print(f"✅ Задача добавлена. Её id = {new_id}")
```

**Последовательность транзакций:**
1. Подключение.
2. `INSERT` с параметром.
3. **`commit()`** — запись в файл.
4. Получение `lastrowid` (пока соединение открыто).
5. Закрытие.

> **Важно:** `cursor.lastrowid` доступен **только до `commit()` и `close()`**. Если сначала закрыть соединение — получишь `None`.

### Шаг 5. UPDATE — отметить задачу выполненной

```python
def mark_done():
    list_tasks()    # показываем, что есть, чтобы пользователь выбрал id

    raw = input("Введи id задачи, которую выполнил: ").strip()

    if not raw.isdigit():
        print("⚠ id должен быть числом.")
        return

    task_id = int(raw)
    conn = get_connection()
    cursor = conn.cursor()

    # UPDATE не падает, если строки нет, — просто изменит 0 строк.
    # Поэтому проверяем через rowcount.
    cursor.execute(
        "UPDATE tasks SET status = 'done' WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    affected = cursor.rowcount    # ← сколько строк реально обновилось

    conn.close()

    if affected == 0:
        print(f"⚠ Задача с id={task_id} не найдена.")
    else:
        print(f"✅ Задача {task_id} отмечена выполненной.")
```

**Разбор `rowcount`:**
- Если id существует и статус меняется — `rowcount == 1`.
- Если id не существует — `rowcount == 0` (запрос выполнился, но ничего не изменил).
- Если задача уже была `done` и мы ставим `done` снова — SQLite тоже вернёт `rowcount == 1` (строка «затронута», хоть значение и не поменялось).

**Проверка `isdigit()`** защищает от ввода вроде `abc`, которое уронило бы `int()` с `ValueError`.

### Шаг 6. DELETE — удалить задачу

```python
def delete_task():
    list_tasks()

    raw = input("Введи id задачи для удаления: ").strip()
    if not raw.isdigit():
        print("⚠ id должен быть числом.")
        return

    task_id = int(raw)

    confirm = input(f"Точно удалить задачу {task_id}? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Отменено.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    affected = cursor.rowcount

    conn.close()

    if affected == 0:
        print(f"⚠ Задача с id={task_id} не найдена.")
    else:
        print(f"🗑 Задача {task_id} удалена.")
```

**Зачем подтверждение:** удаление необратимо. В реальных приложениях всегда спрашивают «Точно?».

**Последовательность транзакций:** подключение → DELETE → commit → rowcount → закрытие.

### Шаг 7. Полный скрипт (собери всё вместе)

```python
import sqlite3


def get_connection():
    return sqlite3.connect('app.db')


def show_menu():
    print("\n===== СПИСОК ЗАДАЧ =====")
    print("1. Показать все задачи")
    print("2. Добавить задачу")
    print("3. Отметить задачу выполненной")
    print("4. Удалить задачу")
    print("0. Выход")


def list_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, status FROM tasks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("📭 Список пуст. Добавь первую задачу!")
        return

    print("\n--- ТВОИ ЗАДАЧИ ---")
    for row in rows:
        task_id, title, status = row
        mark = "✅" if status == 'done' else "⬜"
        print(f"{task_id:>3}. {mark} {title}  [{status}]")


def add_task():
    title = input("Название задачи: ").strip()
    if not title:
        print("⚠ Название не может быть пустым.")
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    print(f"✅ Задача добавлена. Её id = {new_id}")


def mark_done():
    list_tasks()
    raw = input("Введи id задачи, которую выполнил: ").strip()
    if not raw.isdigit():
        print("⚠ id должен быть числом.")
        return

    task_id = int(raw)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = 'done' WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        print(f"⚠ Задача с id={task_id} не найдена.")
    else:
        print(f"✅ Задача {task_id} отмечена выполненной.")


def delete_task():
    list_tasks()
    raw = input("Введи id задачи для удаления: ").strip()
    if not raw.isdigit():
        print("⚠ id должен быть числом.")
        return

    task_id = int(raw)
    confirm = input(f"Точно удалить задачу {task_id}? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Отменено.")
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        print(f"⚠ Задача с id={task_id} не найдена.")
    else:
        print(f"🗑 Задача {task_id} удалена.")


def main():
    while True:
        show_menu()
        choice = input("Выбери действие: ").strip()

        if choice == '1':
            list_tasks()
        elif choice == '2':
            add_task()
        elif choice == '3':
            mark_done()
        elif choice == '4':
            delete_task()
        elif choice == '0':
            print("До встречи!")
            break
        else:
            print("⚠ Нет такого пункта. Попробуй снова.")


if __name__ == '__main__':
    main()
```

### Шаг 8. Сценарий проверки (пройди по шагам)

1. Запусти `python crud_console.py`.
2. Выбери `1` — увидишь «📭 Список пуст».
3. Выбери `2`, введи `Купить хлеб`.
4. Выбери `2`, введи `Сделать уроки`.
5. Выбери `1` — обе задачи в статусе `new`.
6. Выбери `3`, введи `1` — первая задача станет `done`.
7. Выбери `4`, введи `2`, подтверди `y` — вторая удалена.
8. Выбери `1` — осталась одна задача со статусом `done`.
9. Выбери `0` — выход.
10. **Запусти скрипт снова** и выбери `1`. Данные на месте — значит, `commit()` работает правильно.

### Шаг 9. Эксперимент с SQL-инъекцией (понимание защиты)

Попробуй в `add_task()` ввести название:

```
'); DROP TABLE tasks; --
```

С параметризованным запросом `(?)` это сохранится **как обычный текст**, и таблица останется целой. Можешь потом удалить эту запись. Если бы ты использовал f-строку — таблицы бы уже не было. Это наглядная демонстрация, зачем нужны плейсхолдеры.

---

## ⚠️ Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| `sqlite3.ProgrammingError: Incorrect number of bindings` | Передал строку вместо кортежа: `execute(sql, title)` | Оборачивай в кортеж: `execute(sql, (title,))` |
| `sqlite3.ProgrammingError: Parameters are of unsupported type` | Забыл `?` в SQL, но передал второй аргумент | Проверь, что в SQL есть плейсхолдер на каждое значение |
| `None` в `lastrowid` | Вызвал `lastrowid` после `close()` | Читай `lastrowid` **до** закрытия соединения |
| `ValueError: invalid literal for int()` | Пользователь ввёл `abc`, а ты делаешь `int()` | Проверка `isdigit()` перед `int()` |
| Данные исчезли после перезапуска | Забыт `conn.commit()` после INSERT/UPDATE/DELETE | Добавь `commit()` перед `close()` |
| `database is locked` | Не закрыл соединение в предыдущем запуске | Перезапусти терминал; всегда вызывай `close()` |

---

## 🧠 Контрольные вопросы

1. Почему для `SELECT` не нужен `commit()`, а для `INSERT` — нужен?
2. Что вернёт `fetchone()`, если в таблице нет строк?
3. Чем `fetchone()` отличается от `fetchall()` и когда какой использовать?
4. Почему `(title,)` — это кортеж, а `(title)` — нет?
5. Что вернёт `cursor.rowcount` после `UPDATE`, если такого id нет?
6. Зачем проверять `isdigit()` перед `int(input())`?
7. Как параметризованные запросы защищают от SQL-инъекции?

---

## 🚀 Что дальше

В Практической работе №3 ты откроешь Flask и увидишь, как этот же список задач превращается в **веб-страницу** в браузере. Логика работы с базой останется прежней, но вывод пойдёт не в консоль, а в HTML.
