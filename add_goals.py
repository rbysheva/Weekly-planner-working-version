import sqlite3

conn = sqlite3.connect("weekplanner.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    current INTEGER DEFAULT 0,
    target INTEGER NOT NULL,
    emoji TEXT DEFAULT '🎯'
)
""")

conn.commit()
conn.close()
print("Goals table created!")