# Практическая работа №6: Обработка ошибок и защита соединений

## 📚 Теоретическая справка

### Почему нельзя просто «открыть — сделать — закрыть»

В работах №1–5 мы писали прямолинейно:

```python
conn = get_connection()
cursor = conn.cursor()
cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
conn.commit()
conn.close()
```

Пока всё идёт по плану, это работает. Но представь: на строке `execute` произошла ошибка (например, диск переполнен, база заблокирована, нарушено ограничение `NOT NULL`). Python выбросит исключение — и **выполнение функции прервётся**. Строки `commit()` и `close()` **не выполнятся**.

Что произойдёт:
- Транзакция останется «висящей» — изменения не зафиксированы, но и не отменены явно. SQLite при следующем открытии может откатить её сам, но полагаться на это нельзя.
- Соединение **не закрыто** — файл базы остаётся заблокированным. Другая программа (например, DB Browser или второй экземпляр Flask) получит ошибку `database is locked`.
- В веб-приложении Flask при каждом падении будет утекать одно соединение. Через сотню запросов сервер намертво заблокирует базу.

Именно поэтому в реальном коде используется конструкция **try/except/finally**.

### Стандартный паттерн работы с транзакцией

```python
conn = sqlite3.connect('app.db')
try:
    cursor = conn.cursor()
    cursor.execute("INSERT ...", (...))
    conn.commit()                 # фиксируем, если всё ок
except sqlite3.Error as e:
    conn.rollback()               # откатываем при ошибке
    # обработать ошибку (лог, вернуть сообщение пользователю)
finally:
    conn.close()                  # закрываем ВСЕГДА
```

Разберём каждый блок.

### Блок `try` — «попытка»

Сюда кладём всё, что может упасть: `execute`, `commit`, `fetchall`. Пока внутри `try` не произошло исключение — код идёт по порядку.

### Блок `except` — «перехват ошибки»

Срабатывает, **только если** в `try` было исключение. Здесь:
1. **`conn.rollback()`** — отменяем транзакцию. Если `execute` успел изменить данные, но `commit` не выполнился, `rollback` вернёт базу в состояние до начала транзакции. Это защита от «полузаписанных» данных.
2. Обрабатываем ошибку: пишем в лог, возвращаем пользователю понятное сообщение (а не «стектрейс»).

> **Важно:** ловить нужно **конкретное** исключение (`sqlite3.Error`), а не голый `except:`. Голый `except` перехватит и `KeyboardInterrupt` (Ctrl+C), и системные ошибки — это плохо.

### Блок `finally` — «гарантированное закрытие»

Выполняется **всегда**: и если всё прошло успешно, и если было исключение, и даже если был `return` внутри `try`. Именно сюда ставится `conn.close()` — чтобы соединение закрылось при любом сценарии.

### Что такое `rollback()` на практике

Представь, что ты вставляешь две связанные записи: заказ и его позиции. Если первая вставка прошла, а вторая упала — без `rollback` в базе останется «заказ без позиций». С `rollback` обе вставки отменятся, и база останется консистентной.

В нашей задаче с одной таблицей эффект проще: `rollback` гарантирует, что при ошибке в базе не останется «мусорной» недописанной строки.

### Как специально вызвать ошибку для тренировки

Самый простой способ — нарушить ограничение `NOT NULL`. В таблице `tasks` колонка `title` объявлена как `TEXT NOT NULL`. Если попытаться вставить `NULL`, SQLite выбросит:

```
sqlite3.IntegrityError: NOT NULL constraint failed: tasks.title
```

`IntegrityError` — подкласс `sqlite3.Error`, поэтому `except sqlite3.Error` его поймает. Именно на этом мы и потренируемся.

### Как Flask должен реагировать на ошибку

В веб-приложении нельзя просто «упасть» — пользователь увидит страшную страницу с трассировкой. Правильно:
1. Поймать ошибку.
2. Залогировать (хотя бы `print` в консоль на этом этапе).
3. Вернуть пользователю нормальную страницу с сообщением.

Мы будем возвращать тот же шаблон `index.html` с переменной `error`, как в работе №5.

---

## 🎯 Пошаговая инструкция

### Шаг 1. Подготовка

Открой `app.py` из работы №5. Сейчас в нём ветка POST выглядит так:

```python
conn = get_connection()
cursor = conn.cursor()
cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
conn.commit()
conn.close()
return redirect(url_for('index'))
```

Этот код **не защищён**: если `execute` или `commit` упадут, `close()` не выполнится.

### Шаг 2. Переписываем ветку POST с try/except/finally

Замени блок на следующий:

```python
if request.method == 'POST':
    title = request.form.get('title', '').strip()

    if not title:
        return render_template(
            'index.html',
            items=fetch_all_tasks(),
            error='Название задачи не может быть пустым.'
        )

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        # В реальном проекте здесь был бы logging.error(...)
        print(f"[DB ERROR] {e}")
        return render_template(
            'index.html',
            items=fetch_all_tasks(),
            error='Не удалось сохранить задачу. Попробуйте ещё раз.'
        )
    finally:
        conn.close()

    return redirect(url_for('index'))
```

**Что изменилось:**
- Соединение открывается **до** `try`, чтобы `close()` в `finally` имел к чему обратиться.
- `cursor`, `execute`, `commit` — внутри `try`.
- При ошибке — `rollback()` и возврат формы с понятным сообщением. Пользователь видит не стектрейс, а «Не удалось сохранить задачу».
- `close()` — в `finally`, выполнится при любом исходе.
- Редирект — **после** `finally`, только если дошли до этой точки без `return` из `except`.

### Шаг 3. Применяем тот же паттерн к чтению

Даже чтение стоит защищать — `SELECT` тоже может упасть (нет таблицы, база заблокирована). Обнови `fetch_all_tasks()`:

```python
def fetch_all_tasks():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, status FROM tasks ORDER BY id")
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[DB ERROR] {e}")
        return []                  # при ошибке возвращаем пустой список
    finally:
        conn.close()
```

Обрати внимание на тонкость: `return cursor.fetchall()` внутри `try` — Python **сначала** выполнит `finally` (`conn.close()`), **потом** вернёт значение. Это нормальное поведение: `finally` гарантированно отработает перед выходом из функции.

### Шаг 4. Полный обновлённый `app.py`

```python
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DB_PATH = 'app.db'


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all_tasks():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, status FROM tasks ORDER BY id")
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()

        if not title:
            return render_template(
                'index.html',
                items=fetch_all_tasks(),
                error='Название задачи не может быть пустым.'
            )

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            print(f"[DB ERROR] {e}")
            return render_template(
                'index.html',
                items=fetch_all_tasks(),
                error='Не удалось сохранить задачу. Попробуйте ещё раз.'
            )
        finally:
            conn.close()

        return redirect(url_for('index'))

    return render_template('index.html', items=fetch_all_tasks())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

Шаблон `index.html` менять не нужно — он уже умеет показывать `{{ error }}` из работы №5.

### Шаг 5. Эксперимент 1 — специально вызываем ошибку NOT NULL

Нам нужно отправить в `INSERT` значение `None` (что станет `NULL` в SQL). Обычная форма не даст этого сделать: `request.form.get('title', '')` вернёт строку. Поэтому временно **модифицируем код** — заменим строку:

```python
cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
```

на:

```python
cursor.execute("INSERT INTO tasks (title) VALUES (?)", (None,))
```

Запусти сервер, открой страницу, введи любое название и нажми «Добавить».

**Что должно произойти:**
1. `execute` выбросит `sqlite3.IntegrityError: NOT NULL constraint failed: tasks.title`.
2. Управление перейдёт в `except`: выполнится `rollback()`, в консоль напечатается `[DB ERROR] ...`.
3. Пользователь увидит форму с сообщением **«Не удалось сохранить задачу. Попробуйте ещё раз.»**
4. `finally` закроет соединение.
5. Сервер **не упадёт** — продолжит принимать запросы.

**Проверка отсутствия «мусора»:** открой список — количество задач **не изменилось**. Значит, `rollback()` сработал: недописанная строка не попала в базу.

**Верни код обратно:** `(None,)` → `(title,)`. Эксперимент завершён.

### Шаг 6. Эксперимент 2 — доказываем необходимость `finally`

Временно **убери** блок `finally` (и `close()` вместе с ним) из ветки POST. Оставь только `try/except`.

Теперь вызови ошибку так же, как в шаге 5 (через `(None,)`). После того как пользователь увидит сообщение об ошибке, попробуй через **второй терминал** открыть базу в DB Browser for SQLite или выполнить:

```bash
python crud_console.py
```

Ты, скорее всего, получишь **`database is locked`** — потому что соединение не закрылось после ошибки.

Верни `finally: conn.close()` на место — и проблема исчезнет. Это наглядное доказательство, зачем нужен `finally`.

### Шаг 7. Эксперимент 3 — проверка `rollback` через явный сбой

Более тонкий эксперимент. Внутри `try` **после** `execute`, но **до** `commit`, добавь строку, которая гарантированно упадёт:

```python
try:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
    1 / 0                          # ← искусственная ошибка
    conn.commit()
except sqlite3.Error as e:
    ...
```

Заметь: `1/0` выбросит `ZeroDivisionError`, а мы ловим только `sqlite3.Error` — исключение **не поймается** нашим `except`, но `finally` всё равно выполнится и закроет соединение. А `rollback` не вызовется — потому что мы его не поймали.

**Вывод:** ловить нужно **все** исключения, которые могут возникнуть в `try`, либо расширять `except`. В реальном коде часто пишут:

```python
except Exception as e:
    conn.rollback()
    ...
```

Но для учебной задачи достаточно `sqlite3.Error` — мы работаем с базой, и другие ошибки в этом блоке маловероятны. Просто знай об этой тонкости.

Верни код в исходное состояние.

---

## ⚠️ Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| `database is locked` после серии ошибок | Нет `finally: conn.close()` | Всегда закрывай соединение в `finally` |
| `UnboundLocalError: local variable 'conn' referenced before assignment` | `conn` объявлен **внутри** `try`, а используется в `finally` | Открывай `conn` **до** `try` |
| Ошибка не ловится | Ловишь `sqlite3.Error`, а упало что-то другое (`ValueError`, `KeyError`) | Расширь `except` до `Exception` или добавь второй `except` |
| После ошибки осталась «полузаписанная» строка | Забыт `conn.rollback()` в `except` | Добавь `rollback()` |
| Пользователь видит стектрейс | Не обработал ошибку, вернул исключение наружу | Возвращай `render_template` с сообщением из `except` |
| `SyntaxError` после добавления `try` | Забыл сдвинуть отступы в блоке | Выдели тело `try` и нажми Tab |

---

## 🧠 Контрольные вопросы

1. Почему `conn.close()` нельзя оставлять просто в конце функции, а нужно помещать в `finally`?
2. Что делает `conn.rollback()` и в каком случае он вызывается?
3. Почему `conn` нужно открывать **до** `try`, а не внутри?
4. Чем `except sqlite3.Error` лучше, чем `except:` без указания типа?
5. Что произойдёт с данными, если `execute` прошёл, а `commit` упал?
6. Зачем в веб-приложении возвращать пользователю понятное сообщение вместо стектрейса?
7. Как проверить, что `rollback` действительно откатил транзакцию?

---

## ✅ Что должно получиться

1. В `app.py` ветка POST обёрнута в `try/except/finally`.
2. `fetch_all_tasks()` тоже защищена — при ошибке возвращает пустой список.
3. При искусственной ошибке (`(None,)`) пользователь видит сообщение, сервер не падает, база не «залочена», в ней нет мусорных строк.
4. После серии ошибок `crud_console.py` и DB Browser **открывают** базу без `database is locked`.
5. `rollback()` вызывается при ошибке — проверено экспериментом.

---

## 🚀 Что дальше

В Практической работе №7 — **финальный мини-проект «Список задач»**, в котором ты соберёшь всё вместе:

- полный CRUD в браузере (добавление, отметка выполненной, удаление);
- защищённые соединения (`try/except/finally`) во всех операциях;
- кнопки действий рядом с каждой задачей;
- подтверждение удаления;
- аккуратная структура кода (вынесенные функции `fetch_all_tasks`, `insert_task`, `mark_done`, `delete_task`).
