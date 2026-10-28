# Практическая работа №5: Интеграция Flask и SQLite (Добавление данных)

## 📚 Теоретическая справка

### Как работает отправка формы

В работе №4 мы только **читали** данные: браузер отправлял `GET /`, Flask возвращал HTML. Теперь нужно, чтобы пользователь **отправлял данные** в базу. Для этого используется HTML-форма и метод **POST**.

Схема полного цикла:

```
1. Браузер: GET /            → Flask возвращает HTML с формой
2. Пользователь заполняет форму и нажимает «Добавить»
3. Браузер: POST /add        → Flask читает данные из формы
4. Flask: INSERT + commit    → данные записаны в SQLite
5. Flask: redirect('/')      → браузер делает GET / заново
6. Пользователь видит новую задачу в списке
```

### GET vs POST — принципиальная разница

| | **GET** | **POST** |
|---|---|---|
| Назначение | **Получить** данные | **Отправить** данные на сервер |
| Где данные | В URL (`?title=...`) | В теле запроса (скрыто) |
| Видно ли в адресной строке | Да | Нет |
| Идемпотентен | Да (повтор безопасен) | Нет (повтор = новая запись) |
| Кэшируется браузером | Да | Нет |
| Когда использовать | Чтение страниц | Отправка форм, создание/изменение |

**Правило:** если операция **меняет данные** на сервере — используй POST.

### Что такое `request.form` и `request.method`

Flask даёт доступ к данным запроса через объект `request`:

- `request.method` — метод запроса (`'GET'` или `'POST'`).
- `request.form` — словарь с данными из POST-формы. Например, если в форме поле `<input name="title">`, то `request.form['title']` вернёт введённое значение.
- `request.args` — то же для GET-параметров в URL (нам сейчас не нужно).

### Зачем нужен `redirect` после POST

Представь, что после INSERT мы просто возвращаем `render_template('index.html', ...)` без редиректа. Пользователь видит список с новой задачей — всё хорошо. Но если он нажмёт **F5** (обновить), браузер **повторит последний запрос**, то есть POST. Flask снова выполнит INSERT — и задача **задублируется**. Ещё раз F5 — ещё одна копия.

Это называется **Post/Redirect/Get (PRG)** — паттерн, при котором после успешного POST сервер отвечает **редиректом** (HTTP 302) на GET-страницу. Браузер послушно идёт по адресу редиректа и получает свежий список. Обновление страницы теперь повторяет GET, а не POST, — дублирования нет.

В Flask это делается так:

```python
from flask import redirect, url_for
return redirect(url_for('index'))
```

- `url_for('index')` — возвращает URL маршрута с именем функции `index` (то есть `/`).
- `redirect(...)` — говорит браузеру: «перейди по этому адресу».

**Почему `url_for`, а не жёстко `'/'`:** если завтра маршрут изменится на `/tasks`, `url_for('index')` подставит новый URL автоматически. Жёсткая строка сломается.

### Обработка GET и POST в одной функции

Маршрут может принимать оба метода. Типичный шаблон «показать форму + обработать её»:

```python
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # обработать форму
        ...
        return redirect(url_for('index'))
    # GET: показать страницу
    ...
    return render_template('index.html', ...)
```

> **Важно:** по умолчанию Flask принимает **только GET**. Если не указать `methods=['GET', 'POST']`, POST-запрос вернёт **405 Method Not Allowed**.

### Валидация на стороне сервера

Атрибут `required` в HTML-форме заставляет браузер проверить поле до отправки. Но это **не защита**: злоумышленник может отправить POST напрямую (через curl, Postman или отключив JS). Поэтому сервер **обязан** сам проверять данные:

```python
title = request.form.get('title', '').strip()
if not title:
    # вернуть ошибку или показать форму снова
```

`request.form.get('title', '')` безопаснее, чем `request.form['title']`: если поля нет — вернёт `''`, а не выбросит `KeyError`.

### О параметризованных запросах

Здесь всё как в работе №2: `INSERT` выполняется только с плейсхолдером `?` и кортежем значений. Никаких f-строк.

---

## 🎯 Пошаговая инструкция

### Шаг 1. Обновляем шаблон `templates/index.html` — добавляем форму

Добавь форму **над** списком задач. Полный шаблон:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Список задач</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; }
        h1 { color: #333; }
        form { display: flex; gap: 8px; margin-bottom: 20px; }
        input[type="text"] { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 6px; }
        button { padding: 8px 16px; background: #007bff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
        button:hover { background: #0056b3; }
        ul { list-style: none; padding: 0; }
        li { padding: 10px; margin: 6px 0; background: #f4f4f4; border-radius: 6px; }
        .done { text-decoration: line-through; color: #888; }
        .empty { color: #999; font-style: italic; }
        .error { color: #c00; margin-bottom: 12px; }
    </style>
</head>
<body>
    <h1>Мой список задач</h1>

    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}

    <form method="POST" action="{{ url_for('index') }}">
        <input type="text" name="title" placeholder="Новая задача..." required>
        <button type="submit">Добавить</button>
    </form>

    {% if items %}
        <ul>
            {% for item in items %}
                <li class="{% if item.status == 'done' %}done{% endif %}">
                    <strong>#{{ item.id }}</strong>
                    {{ item.title }}
                    <em>[{{ item.status }}]</em>
                </li>
            {% endfor %}
        </ul>
    {% else %}
        <p class="empty">Список пуст. Добавь первую задачу!</p>
    {% endif %}
</body>
</html>
```

**Разбор нового в шаблоне:**
- `<form method="POST" action="{{ url_for('index') }}">` — форма отправляет POST на URL, который возвращает `url_for('index')` (то есть `/`).
- `<input name="title">` — **имя поля `title` критично**: Flask найдёт значение через `request.form['title']`.
- `required` — браузер не даст отправить пустое поле.
- `{{ error }}` — условный блок для сообщения об ошибке. Если переменная `error` не передана — блок не появится.

### Шаг 2. Обновляем `app.py`: обработка POST и INSERT

Приведи `app.py` к виду:

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
    """Возвращает все задачи. Используется и в GET, и в POST-ошибке."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, status FROM tasks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return rows


@app.route('/', methods=['GET', 'POST'])
def index():
    # ---- ОБРАБОТКА POST ----
    if request.method == 'POST':
        title = request.form.get('title', '').strip()

        # Серверная валидация: даже если браузер обошли, пустое не примем
        if not title:
            return render_template(
                'index.html',
                items=fetch_all_tasks(),
                error='Название задачи не может быть пустым.'
            )

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        conn.commit()
        conn.close()

        # PRG-паттерн: после POST — редирект на GET
        return redirect(url_for('index'))

    # ---- ОБРАБОТКА GET ----
    return render_template('index.html', items=fetch_all_tasks())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**Что нового по сравнению с работой №4:**
- Импортируются `request`, `redirect`, `url_for`.
- В `@app.route` добавлен `methods=['GET', 'POST']`.
- Появилась ветка `if request.method == 'POST'`, которая читает форму, валидирует, вставляет, коммитит и редиректит.
- Функция `fetch_all_tasks()` вынесена, чтобы не дублировать код: она нужна и в GET, и в ветке ошибки POST.
- В шаблон передаётся `error` — только при ошибке.

### Шаг 3. Запуск и проверка

Сервер уже работает — он перезагрузится сам. Открой `http://127.0.0.1:5000`.

**Сценарий проверки:**

1. Введи `Прочитать главу 3` и нажми «Добавить».
2. Произошёл POST → INSERT → redirect → GET. Задача появилась в списке.
3. **Нажми F5 (обновить).** Задача **не задублировалась** — сработал PRG.
4. Добавь ещё пару задач.
5. Оставь поле пустым и нажми «Добавить». Браузер покажет подсказку `required` и не отправит форму. Обойди защиту: открой DevTools (F12), удали атрибут `required` из `<input>` через Elements — и отправь. Сервер вернёт форму с ошибкой `Название задачи не может быть пустым.` Это доказывает, что серверная валидация работает независимо от браузерной.

### Шаг 4. Проверка порядка транзакций

Чтобы убедиться, что `commit()` реально пишет на диск:

1. Добавь задачу через веб-форму: `Проверка commit`.
2. Останови сервер (`Ctrl+C`).
3. Запусти сервер заново (`python app.py`).
4. Обнови страницу — задача `Проверка commit` **на месте**. Значит, `commit()` записал её в файл `app.db`.
5. Теперь **временно убери `conn.commit()`** из ветки POST и повтори эксперимент. После перезапуска сервера задача **исчезнет** — она осталась только в памяти. Верни `commit()` обратно.

Это самая наглядная демонстрация, почему `commit()` обязателен.

### Шаг 5. Эксперимент с SQL-инъекцией

Попробуй добавить задачу с названием:

```
'); DROP TABLE tasks; --
```

Она сохранится как **обычный текст**. Открой список — задача есть, таблица цела. Это заслуга параметризованного запроса `VALUES (?)`. Если бы в `execute()` стояла f-строка — таблица `tasks` уже не существовала бы. Можешь удалить эту задачу.

### Шаг 6. (Опционально) Проверка кода ответа redirect

Открой DevTools (F12) → вкладка **Network** → добавь задачу. Ты увидишь два запроса:

1. `POST /` — ответ **302 Found** (редирект).
2. `GET /` — ответ **200 OK** (страница со списком).

Это визуальное подтверждение PRG-паттерна.

---

## ⚠️ Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| `405 Method Not Allowed` при отправке формы | В маршруте нет `methods=['POST']` | Добавь `methods=['GET', 'POST']` в `@app.route` |
| `BadRequestKeyError: 'title'` | Поле в форме называется иначе, чем в `request.form[...]` | Сверь `name="title"` в HTML и ключ в Python |
| Задача дублируется при F5 | Нет `redirect` после POST | Добавь `return redirect(url_for('index'))` |
| `TypeError: The view function did not return a valid response` | В какой-то ветке нет `return` | Проверь, что все ветки `if/else` возвращают значение |
| `BuildError: Could not build url for endpoint 'index'` | В `url_for` указано неверное имя функции | Имя должно совпадать с функцией после `def` |
| Пустая задача всё равно добавляется | Нет серверной валидации, только `required` | Добавь проверку `if not title:` в Python |
| Данные не сохраняются после перезапуска | Забыт `conn.commit()` | Добавь `commit()` после `INSERT` |

---

## 🧠 Контрольные вопросы

1. Чем POST принципиально отличается от GET и почему формы отправляют именно POST?
2. Что произойдёт, если убрать `methods=['GET', 'POST']` из маршрута?
3. Зачем нужен паттерн Post/Redirect/Get? Что сломается без него?
4. Почему `url_for('index')` лучше, чем жёсткая строка `'/'`?
5. Почему `request.form.get('title', '')` безопаснее, чем `request.form['title']`?
6. Зачем нужна серверная валидация, если в HTML уже есть `required`?
7. В каком порядке идут транзакции при добавлении задачи через форму?

---

## ✅ Что должно получиться

1. На странице `http://127.0.0.1:5000` есть форма ввода новой задачи.
2. При отправке формы задача сохраняется в `app.db` и появляется в списке.
3. F5 после добавления **не дублирует** задачу (PRG работает).
4. Пустое название не проходит: браузер блокирует через `required`, сервер — через проверку `if not title`.
5. SQL-инъекция вида `'); DROP TABLE tasks; --` сохраняется как текст и не ломает базу.
6. После перезапуска сервера данные на месте.

---

## 🚀 Что дальше

В Практической работе №6 ты:
- научишься правильно закрывать соединения через `try/except/finally`;
- добавишь `rollback()` на случай ошибки в транзакции;
- специально вызовешь ошибку (например, `NOT NULL`) и убедишься, что приложение не падает;
- поймёшь, почему паттерн «открыл → try → commit → except → rollback → finally → close» — стандарт индустрии.

Это подготовит тебя к Практической работе №7, где ты соберёшь полный CRUD в одном Flask-приложении (добавление, отметка выполненной, удаление, защита соединений).

