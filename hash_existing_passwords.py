import sqlite3
import bcrypt

conn = sqlite3.connect("weekplanner.db")
cursor = conn.cursor()

cursor.execute("SELECT id, password FROM users")
users = cursor.fetchall()

count = 0
for user_id, password in users:
    # bcrypt-хеши начинаются с $2b$ (или $2a$). Если уже хеш — пропускаем.
    if password and password.startswith("$2"):
        continue
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    cursor.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
    count += 1

conn.commit()
conn.close()
print(f"Done! Hashed {count} password(s).")