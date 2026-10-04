import sqlite3

conn = sqlite3.connect("weekplanner.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'Medium'")
    print("✅ Колонка priority добавлена!")
except Exception as e:
    print(f"ℹ️  {e}")

conn.commit()
conn.close()