import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Запрос к системной таблице sqlite_master,
# где SQLite хранит список всех таблиц.
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Таблицы в базе:", tables)

conn.close()