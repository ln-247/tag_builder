import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parents[1]/"data"/"tag_builder.db"

def init_db(): # создание бд
    DB_PATH.parent.mkdir(exist_ok=True) #создать папку data, если её ещё нет

    with sqlite3.connect(DB_PATH) as bd_table:
        bd_table.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_at TEXT NOT NULL,
                name_human TEXT,
                name_project TEXT,
                name_system TEXT,
                message TEXT NOT NULL)""")
        bd_table.commit()

init_db()

def save_feedback(name_human, name_project, name_system, message): 
    with sqlite3.connect(DB_PATH) as insert_table:
        cursor = insert_table.execute("""
            INSERT INTO feedback (
                date_at,
                name_human,
                name_project,
                name_system,
                message)
            VALUES (?, ?, ?, ?, ?)""", (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name_human,
            name_project,
            name_system,
            message))
        insert_table.commit()
        return cursor.lastrowid # id последней добавленной строки

def load_feedback(): # для чтения отзывов из БД
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row 
        rows = conn.execute("""
            SELECT
                id,
                date_at,
                name_human,
                name_project,
                name_system,
                message
            FROM feedback
            ORDER BY date_at DESC""").fetchall() # выполняет SQL-запрос и забирает все найденные строки
    return [dict(row) for row in rows] # в список словарей