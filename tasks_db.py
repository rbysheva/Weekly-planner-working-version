import sqlite3

conn = sqlite3.connect("weekplanner.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    day TEXT,
    user_id INTEGER
)
""")

conn.commit()
conn.close()

print("Tasks table created!")