# Практическая работа №7: Мини-проект «Список задач» (итоговая работа)

## 📚 Теоретическая справка

### Что мы собираем

За работы №1–6 ты освоил все строительные блоки:

- **№1** — создание базы и таблицы;
- **№2** — CRUD через консоль;
- **№3** — Flask и маршруты;
- **№4** — чтение из базы в шаблон Jinja2;
- **№5** — добавление через форму (POST + PRG);
- **№6** — защита соединений (`try/except/finally` + `rollback`).

Теперь собираем **полноценное веб-приложение** — список задач, в котором через браузер можно:

1. **Прочитать** все задачи (R);
2. **Создать** новую задачу (C);
3. **Обновить** статус задачи на «выполнено» (U);
4. **Удалить** задачу (D).

Это полный CRUD, реализованный по всем правилам: параметризованные запросы, `commit`/`rollback`, `finally: close()`, PRG-паттерн, серверная валидация.

### Новые приёмы этой работы

**1. Параметр в URL — `<int:task_id>`**

Раньше маршруты были фиксированными (`/`, `/about`). Но для удаления конкретной задачи нужен адрес вроде `/delete/5`, где `5` — id. Flask позволяет описать это так:

```python
@app.route('/delete/<int:task_id>', methods=['POST'])
def delete(task_id):
    ...
```

- `<int:task_id>` — «переменная часть URL, целое число, попадёт в аргумент `task_id`».
- Flask сам преобразует строку из URL в `int` и вернёт **404**, если в URL не число. Тебе не нужно вручную делать `int()` и проверять `isdigit()`.

**2. Почему действия меняют данные — только через POST**

Кнопки «Выполнено» и «Удалить» **меняют данные**. Значит, по правилу из работы №5, они должны отправляться **POST-формой**, а не быть ссылками `<a href>`. Ссылка — это GET, а GET не должен менять состояние (иначе браузерный кэш или случайный клик по ссылке сломают данные). Мы оформим кнопки как мини-формы:

```html
<form method="POST" action="{{ url_for('toggle_done', task_id=item.id) }}">
    <button type="submit">✅</button>
</form>
```

**3. Разделение ответственности в коде**

Плохой стиль — писать всё в одной функции `index()`. Хороший — вынести работу с базой в отдельные функции:

- `fetch_all_tasks()` — вернуть список;
- `insert_task(title)` — вставить;
- `toggle_task_status(task_id)` — переключить статус;
- `delete_task(task_id)` — удалить.

Каждая функция сама открывает соединение, оборачивает работу в `try/except/finally` и закрывает его. Маршруты Flask становятся тонкими: получили запрос → вызвали функцию → отрендерили шаблон или редиректнули.

**4. Что значит «переключить статус»**

Проще, чем кажется: если статус `new` — ставим `done`, если `done` — ставим `new`. Один SQL-запрос:

```sql
UPDATE tasks
SET status = CASE WHEN status = 'done' THEN 'new' ELSE 'done' END
WHERE id = ?
```

`CASE WHEN ... THEN ... ELSE ... END` — это SQL-аналог `if/else`. Работает в SQLite без проблем.

---

## 🎯 Пошаговая инструкция

### Шаг 1. Структура проекта

К этому моменту у тебя должно быть:

```
task_manager/
├── init_db.py
├── check_db.py
├── crud_console.py
├── app.db
├── app.py
└── templates/
    └── index.html
```

Мы полностью перепишем `app.py` и `index.html`, остальные файлы не трогаем (они полезны как «резервный» способ проверить базу).

### Шаг 2. Новый шаблон `templates/index.html`

Полностью замени содержимое файла:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Список задач</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #222; }
        h1 { color: #333; }
        .add-form { display: flex; gap: 8px; margin-bottom: 24px; }
        .add-form input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 15px; }
        button { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; }
        .btn-primary { background: #007bff; color: #fff; }
        .btn-primary:hover { background: #0056b3; }
        .btn-icon { background: #e9e9e9; padding: 6px 10px; }
        .btn-icon:hover { background: #d4d4d4; }
        .btn-danger { background: #fde0e0; }
        .btn-danger:hover { background: #f8c0c0; }
        ul { list-style: none; padding: 0; }
        li { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin: 6px 0; background: #f4f4f4; border-radius: 6px; }
        .task-title { flex: 1; }
        li.done .task-title { text-decoration: line-through; color: #888; }
        .status { font-size: 12px; color: #666; background: #fff; padding: 2px 8px; border-radius: 10px; }
        .empty { color: #999; font-style: italic; }
        .error { color: #c00; margin-bottom: 12px; padding: 8px 12px; background: #fde0e0; border-radius: 6px; }
        .actions { display: flex; gap: 6px; }
    </style>
</head>
<body>
    <h1>Мой список задач</h1>

    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}

    <form class="add-form" method="POST" action="{{ url_for('index') }}">
        <input type="text" name="title" placeholder="Новая задача..." required autofocus>
        <button type="submit" class="btn-primary">Добавить</button>
    </form>

    {% if items %}
        <ul>
            {% for item in items %}
                <li class="{% if item.status == 'done' %}done{% endif %}">
                    <span class="task-title">#{{ item.id }} — {{ item.title }}</span>
                    <span class="status">{{ item.status }}</span>

                    <div class="actions">
                        <!-- Отметить/снять выполнение -->
                        <form method="POST" action="{{ url_for('toggle_done', task_id=item.id) }}">
                            <button type="submit" class="btn-icon" title="Переключить статус">
                                {% if item.status == 'done' %}↩{% else %}✅{% endif %}
                            </button>
                        </form>

                        <!-- Удалить с подтверждением -->
                        <form method="POST"
                              action="{{ url_for('delete_task', task_id=item.id) }}"
                              onsubmit="return confirm('Удалить задачу #{{ item.id }}?');">
                            <button type="submit" class="btn-icon btn-danger" title="Удалить">🗑</button>
                        </form>
                    </div>
                </li>
            {% endfor %}
        </ul>
    {% else %}
        <p class="empty">Список пуст. Добавь первую задачу!</p>
    {% endif %}
</body>
</html>
```

**Разбор нового:**
- **`<form>` для каждой кнопки** — действия идут через POST, а не через ссылки. Это правильно по семантике HTTP.
- **`url_for('toggle_done', task_id=item.id)`** — Flask соберёт URL вида `/toggle/5`. Второй аргумент — значение для параметра из маршрута.
- **`onsubmit="return confirm(...)"`** — встроенное браузерное подтверждение. Если пользователь нажмёт «Отмена», форма не отправится (возврат `false` отменяет submit).
- **`{% if item.status == 'done' %}↩{% else %}✅{% endif %}`** — кнопка показывает разные иконки в зависимости от состояния.

### Шаг 3. Полный новый `app.py`

Замени содержимое файла:

```python
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DB_PATH = 'app.db'


# ============================================================
# РАБОТА С БАЗОЙ
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all_tasks():
    """R: вернуть все задачи."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, status FROM tasks ORDER BY id")
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[DB ERROR fetch] {e}")
        return []
    finally:
        conn.close()


def insert_task(title):
    """C: вставить новую задачу. Возвращает (success, message)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        conn.commit()
        return True, None
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[DB ERROR insert] {e}")
        return False, "Не удалось сохранить задачу."
    finally:
        conn.close()


def toggle_task_status(task_id):
    """U: переключить статус (new <-> done). Возвращает число затронутых строк."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tasks
            SET status = CASE WHEN status = 'done' THEN 'new' ELSE 'done' END
            WHERE id = ?
            """,
            (task_id,)
        )
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[DB ERROR toggle] {e}")
        return 0
    finally:
        conn.close()


def delete_task_by_id(task_id):
    """D: удалить задачу. Возвращает число затронутых строк."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[DB ERROR delete] {e}")
        return 0
    finally:
        conn.close()


# ============================================================
# МАРШРУТЫ FLASK
# ============================================================

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

        success, message = insert_task(title)
        if not success:
            return render_template(
                'index.html',
                items=fetch_all_tasks(),
                error=message
            )

        return redirect(url_for('index'))

    return render_template('index.html', items=fetch_all_tasks())


@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle_done(task_id):
    affected = toggle_task_status(task_id)
    if affected == 0:
        return render_template(
            'index.html',
            items=fetch_all_tasks(),
            error=f'Задача #{task_id} не найдена.'
        )
    return redirect(url_for('index'))


@app.route('/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    affected = delete_task_by_id(task_id)
    if affected == 0:
        return render_template(
            'index.html',
            items=fetch_all_tasks(),
            error=f'Задача #{task_id} не найдена.'
        )
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**Что важно понять:**
- **Каждая функция работы с базой — самодостаточна:** открыла соединение, сделала дело, закрыла в `finally`. Маршруты не знают, как устроена база.
- **Возврат `(success, message)`** из `insert_task` — простой способ сообщить маршруту, что пошло не так, без выбрасывания исключения наружу.
- **`toggle_task_status` возвращает `rowcount`** — так маршрут узнаёт, было ли что обновлять.
- **Действия `/toggle/<id>` и `/delete/<id>` принимают только POST** (`methods=['POST']`). Если открыть их в браузере как GET (ввести URL в адресную строку) — получишь **405 Method Not Allowed**. Это защита от случайного выполнения действия.
- **`<int:task_id>`** — Flask сам приводит к `int` и возвращает 404, если в URL не число. Проверка `isdigit()` больше не нужна.

### Шаг 4. Запуск и базовый сценарий

Если сервер работает — он сам перезагрузится. Иначе:

```bash
python app.py
```

Открой `http://127.0.0.1:5000`. Пройди сценарий:

1. Добавь задачу `Купить хлеб` → появилась в списке со статусом `new`.
2. Нажми ✅ рядом с задачей → статус стал `done`, текст зачёркнут, иконка сменилась на ↩.
3. Нажми ↩ → статус вернулся в `new`.
4. Нажми 🗑 → браузер спросил подтверждение → после «ОК» задача исчезла.
5. Нажми F5 после каждого действия — **ничего не дублируется** (PRG работает везде).
6. Добавь 3–4 задачи, потом переключи статус одной, удали другую.

### Шаг 5. Проверка полноты CRUD

Прогони все четыре операции и сверь результат с базой:

| Операция | Действие в браузере | Проверка |
|---|---|---|
| **C** (Create) | Ввод + «Добавить» | Новая строка в списке; `SELECT COUNT(*)` выросло на 1 |
| **R** (Read) | Открытие `/` | Список совпадает с содержимым `app.db` |
| **U** (Update) | Кнопка ✅/↩ | Статус в базе изменился; `UPDATE` вернул `rowcount = 1` |
| **D** (Delete) | Кнопка 🗑 + подтверждение | Строка исчезла; `DELETE` вернул `rowcount = 1` |

Сверяй через `crud_console.py` или DB Browser — они работают с тем же файлом `app.db`.

### Шаг 6. Проверка защиты от неверных запросов

**6.1. GET на действие.** Введи в адресную строку:

```
http://127.0.0.1:5000/delete/1
```

Браузер отправит **GET**, а маршрут принимает только POST → увидишь **405 Method Not Allowed**. Это правильно: удалять задачу можно только через кнопку.

**6.2. Несуществующий id.**

```
http://127.0.0.1:5000/toggle/9999
```

Но это GET — снова 405. Чтобы проверить обработку несуществующего id, нажми кнопку ✅ у задачи, которую перед этим удалил из другого терминала (`crud_console.py`). Flask вызовет `toggle_task_status(9999)`, получит `rowcount = 0`, и пользователь увидит сообщение «Задача #9999 не найдена». Это проверка `affected == 0`.

**6.3. Нецелый id в URL.** Открой:

```
http://127.0.0.1:5000/toggle/abc
```

Flask не сможет привести `abc` к `int` → вернёт **404 Not Found**. Тебе не нужен `isdigit()` — за тебя это делает конвертер `<int:...>`.

**6.4. SQL-инъекция в названии.** Добавь задачу с названием:

```
'); DROP TABLE tasks; --
```

Она сохранится как текст, таблица останется целой. Параметризованный `INSERT` работает.

### Шаг 7. Эксперимент: отключи `rollback` — и посмотри, что будет

В `insert_task` временно убери `conn.rollback()`. Затем искусственно вызови ошибку: замени `(title,)` на `(None,)` (как в работе №6). Нажми «Добавить».

**Что произойдёт:**
- `execute` упадёт с `NOT NULL constraint failed`.
- `except` напечатает ошибку и вернёт сообщение пользователю.
- **Но** без `rollback()` SQLite может оставить транзакцию в «подвешенном» состоянии. При следующей операции в том же соединении (которого у нас нет — мы закрываем соединение в `finally`) — на практике незаметно, но **в реальных многооперационных сценариях** это приводит к блокировкам.

**Вывод:** `rollback()` — не паранойя, а страховка. Верни код обратно: `(None,)` → `(title,)`, `rollback()` на место.

### Шаг 8. Проверка «живучести» после серии ошибок

1. Отправь 5–10 раз задачу с пустым названием (обойди `required` через DevTools, как в работе №5).
2. После каждой — приложение отвечает формой с ошибкой.
3. Затем открой `crud_console.py` **во втором терминале** и попробуй добавить задачу.

Если всё сделано правильно — `database is locked` **не будет**. Соединения закрываются в `finally` при каждой ошибке.

---

## ⚠️ Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| `405 Method Not Allowed` при клике по кнопке | В маршруте `/toggle/<id>` нет `methods=['POST']` | Добавь `methods=['POST']` в `@app.route` |
| `BuildError: Could not build url for endpoint 'toggle_done'` | Имя функции в `url_for` не совпадает с `def` | Сверь имена: `url_for('toggle_done', ...)` ↔ `def toggle_done(...)` |
| Кнопки не работают, форма ничего не делает | В шаблоне `<a href>` вместо `<form method="POST">` | Используй `<form method="POST" action="...">` |
| `404` при переходе на `/toggle/5` | Маршрут не зарегистрирован или опечатка в пути | Сверь `@app.route('/toggle/<int:task_id>')` |
| После удаления в браузере, но не в базе | Забыт `conn.commit()` в `delete_task_by_id` | Добавь `commit()` внутри `try` |
| `rowcount` всегда 0 | Проверяешь `rowcount` после `close()` | Читай `rowcount` **до** закрытия соединения |
| Кнопка 🗑 удаляет без подтверждения | Не подключён `onsubmit="return confirm(...)"` | Проверь атрибут в `<form>` |
| Иконки ✅ и ↩ не переключаются | В шаблоне нет условия по `item.status` | Проверь `{% if item.status == 'done' %}` |

---

## 🧠 Контрольные вопросы

1. Почему действия «переключить статус» и «удалить» отправляются через POST-форму, а не через `<a href>`?
2. Что делает конвертер `<int:task_id>` в маршруте и почему с ним не нужен `isdigit()`?
3. Что означает `rowcount = 0` после `UPDATE` или `DELETE`?
4. Почему каждая функция работы с базой открывает **своё** соединение, а не получает его параметром?
5. Где в `toggle_task_status` находится `commit()`, и почему без него статус не сохранится после перезапуска?
6. Что произойдёт, если открыть `/delete/3` в адресной строке браузера (GET)?
7. Зачем в шаблоне `onsubmit="return confirm(...)"` и можно ли обойти эту защиту?
8. Почему `return redirect(url_for('index'))` стоит **после** `try/finally`, а не внутри `try`?

---

## ✅ Что должно получиться

1. Приложение на `http://127.0.0.1:5000` умеет **все четыре CRUD-операции** через браузер.
2. Каждое действие сопровождается редиректом — F5 не дублирует операции.
3. Кнопки ✅/↩ и 🗑 работают, статус отображается визуально (зачёркивание, иконки).
4. Удаление запрашивает подтверждение.
5. `/toggle/5` и `/delete/5` при GET возвращают 405.
6. `/toggle/abc` возвращает 404.
7. Несуществующий id → сообщение «Задача #N не найдена».
8. SQL-инъекция сохраняется как текст.
9. После серии ошибок база не «залочена» — `crud_console.py` открывает её без проблем.

---

## 🎓 Итог курса: что ты теперь умеешь

Пройдя все семь работ, ты освоил полный цикл разработки веб-приложения на Python:

| Навык | Работа |
|---|---|
| Создание БД SQLite и таблиц (DDL, `commit`) | №1 |
| CRUD на уровне SQL + параметризованные запросы | №2 |
| Flask: маршруты, `@app.route`, `debug=True` | №3 |
| Jinja2: `render_template`, циклы, условия, `sqlite3.Row` | №4 |
| HTML-формы, `request.form`, POST, PRG-паттерн, валидация | №5 |
| `try/except/finally`, `rollback`, защита соединений | №6 |
| Полный CRUD в веб-интерфейсе, параметры URL, конвертеры | №7 |
