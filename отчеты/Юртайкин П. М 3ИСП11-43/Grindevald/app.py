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
        print(f"[DB ERROR fetch] {e}")
        return []
    finally:
        conn.close()


def insert_task(title):
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
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET status = CASE WHEN status = 'done' THEN 'pending' ELSE 'done' END WHERE id = ? ",
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