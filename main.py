import sqlite3
import bcrypt
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request, Form
from fastapi.responses import RedirectResponse
import calendar
from datetime import datetime, date, timedelta
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeSerializer, BadSignature

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Секретный ключ для подписи cookie. Поменяй на свою случайную строку!
SECRET_KEY = "poke-planner-change-this-secret-key-2024"
signer = URLSafeSerializer(SECRET_KEY)


def make_session_cookie(user_id: int) -> str:
    """Создаём подписанное значение для cookie."""
    return signer.dumps({"user_id": user_id})


def read_session_cookie(request: Request):
    """Читаем user_id из cookie. Возвращает int или None."""
    raw = request.cookies.get("session")
    if not raw:
        return None
    try:
        data = signer.loads(raw)
        return data.get("user_id")
    except BadSignature:
        return None


def check_access(request: Request, url_user_id: int):
    """
    Проверяем, что залогиненный пользователь (из cookie)
    совпадает с user_id из URL. Возвращает True если всё ок.
    """
    session_user_id = read_session_cookie(request)
    if session_user_id is None:
        return False
    return session_user_id == url_user_id


def hash_password(password: str) -> str:
    """Хешируем пароль перед сохранением в БД."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Проверяем введённый пароль против хеша из БД."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_week_dates():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return [(monday + timedelta(days=i)).isoformat() for i in range(7)]


def get_rank(level):
    if level >= 50:  return "Pokemon Champion"
    if level >= 40:  return "Elite Four Member"
    if level >= 30:  return "Gym Leader"
    if level >= 20:  return "Gym Challenger"
    if level >= 15:  return "Expert Trainer"
    if level >= 10:  return "Ace Trainer"
    if level >= 5:   return "Rising Trainer"
    return "Pokemon Trainer"


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/register", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")


@app.post("/register")
def register_user(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    hashed = hash_password(password)
    cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/login")
def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    conn.close()
    # user[3] = password hash
    if user and verify_password(password, user[3]):
        response = RedirectResponse(url=f"/dashboard?user_id={user[0]}", status_code=303)
        # Кладём подписанную cookie с user_id
        response.set_cookie(
            key="session",
            value=make_session_cookie(user[0]),
            httponly=True,
            max_age=60 * 60 * 24 * 7,  # неделя
            samesite="lax"
        )
        return response
    return RedirectResponse(url="/login", status_code=303)


@app.get("/logout")
def logout():
    """Выход — удаляем cookie."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user_id: int):
    # Защита: проверяем что залогинен именно этот пользователь
    if not check_access(request, user_id):
        return RedirectResponse(url="/login", status_code=303)

    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name, xp, level FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    name, xp, level = user[0], user[1], user[2]
    rank = get_rank(level)

    current_date = datetime.now()
    month_name = current_date.strftime("%B")
    year = current_date.year
    current_day = current_date.day
    cal = calendar.monthcalendar(year, current_date.month)

    cursor.execute("SELECT title, day, status, priority FROM tasks WHERE user_id=?", (user_id,))
    tasks = cursor.fetchall()

    # ── Habits ──
    cursor.execute("SELECT id, name, emoji FROM habits WHERE user_id=?", (user_id,))
    habits_raw = cursor.fetchall()
    week_dates = get_week_dates()
    habits = []
    for h in habits_raw:
        habit_id, habit_name, emoji = h
        logs = []
        for d in week_dates:
            cursor.execute("SELECT 1 FROM habit_logs WHERE habit_id=? AND log_date=?", (habit_id, d))
            logs.append(bool(cursor.fetchone()))
        habits.append({"id": habit_id, "name": habit_name, "emoji": emoji, "logs": logs, "dates": week_dates})

    # ── Weekly progress ──
    week_progress = [0, 0, 0, 0, 0, 0, 0]
    cursor.execute(
        "SELECT completed_date FROM tasks WHERE user_id=? AND status='Completed' AND completed_date IS NOT NULL",
        (user_id,)
    )
    for row in cursor.fetchall():
        if row[0] in week_dates:
            week_progress[week_dates.index(row[0])] += 1
    max_progress = max(week_progress) if max(week_progress) > 0 else 1

    # ── Goals ──
    cursor.execute("SELECT id, title, current, target, emoji FROM goals WHERE user_id=?", (user_id,))
    goals_raw = cursor.fetchall()
    goals = []
    for g in goals_raw:
        gid, title, cur, target, gemoji = g
        pct = round(cur / target * 100) if target > 0 else 0
        pct = min(pct, 100)
        goals.append({
            "id": gid, "title": title, "current": cur,
            "target": target, "emoji": gemoji, "pct": pct
        })

    # ── Schedule (sorted by start time) ──
    cursor.execute(
        "SELECT id, title, start_time, end_time, emoji FROM schedule WHERE user_id=? ORDER BY start_time",
        (user_id,)
    )
    schedule_raw = cursor.fetchall()
    schedule = [
        {"id": s[0], "title": s[1], "start": s[2], "end": s[3], "emoji": s[4]}
        for s in schedule_raw
    ]

    conn.close()

    today_str = date.today().isoformat()
    today_col = week_dates.index(today_str) if today_str in week_dates else -1

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "tasks": tasks,
            "user_id": user_id,
            "name": name,
            "xp": xp,
            "level": level,
            "rank": rank,
            "calendar": cal,
            "month_name": month_name,
            "year": year,
            "current_day": current_day,
            "habits": habits,
            "day_labels": ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
            "today_col": today_col,
            "week_dates": week_dates,
            "week_progress": week_progress,
            "max_progress": max_progress,
            "goals": goals,
            "schedule": schedule,
        }
    )


@app.get("/add-task", response_class=HTMLResponse)
def add_task_page(request: Request, user_id: int):
    if not check_access(request, user_id):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="add_task.html", context={"request": {}, "user_id": user_id})


@app.post("/add-task")
def save_task(title: str = Form(...), description: str = Form(...), day: str = Form(...), priority: str = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, description, day, status, priority, user_id) VALUES (?, ?, ?, ?, ?, ?)", (title, description, day, "Pending", priority, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.get("/edit-task/{title}", response_class=HTMLResponse)
def edit_task_page(request: Request, title: str, user_id: int):
    if not check_access(request, user_id):
        return RedirectResponse(url="/login", status_code=303)
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, day, priority FROM tasks WHERE title=? AND user_id=?", (title, user_id))
    task = cursor.fetchone()
    conn.close()
    return templates.TemplateResponse(request=request, name="edit_task.html", context={
        "request": request,
        "title": task[0] if task else title,
        "day": task[1] if task else "Monday",
        "priority": task[2] if task else "Medium",
        "user_id": user_id
    })


@app.post("/edit-task/{old_title}")
def update_task(old_title: str, title: str = Form(...), day: str = Form(...), priority: str = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET title=?, day=?, priority=? WHERE title=? AND user_id=?", (title, day, priority, old_title, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.post("/delete-task")
def delete_task(title: str = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE title=? AND user_id=?", (title, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.post("/complete-task")
def complete_task(title: str = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("UPDATE tasks SET status='Completed', completed_date=? WHERE title=? AND user_id=?", (today, title, user_id))
    cursor.execute("UPDATE users SET xp = xp + 10 WHERE id = ?", (user_id,))
    cursor.execute("SELECT xp, level FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user[0] >= 100:
        cursor.execute("UPDATE users SET level = level + 1, xp = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


# ── Habits ──
@app.post("/add-habit")
def add_habit(name: str = Form(...), emoji: str = Form("⭐"), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (user_id, name, emoji) VALUES (?, ?, ?)", (user_id, name, emoji))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.post("/delete-habit")
def delete_habit(habit_id: int = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habits WHERE id=? AND user_id=?", (habit_id, user_id))
    cursor.execute("DELETE FROM habit_logs WHERE habit_id=?", (habit_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.post("/toggle-habit")
def toggle_habit(habit_id: int = Form(...), log_date: str = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM habit_logs WHERE habit_id=? AND log_date=?", (habit_id, log_date))
    exists = cursor.fetchone()
    if exists:
        cursor.execute("DELETE FROM habit_logs WHERE habit_id=? AND log_date=?", (habit_id, log_date))
    else:
        cursor.execute("INSERT INTO habit_logs (habit_id, user_id, log_date) VALUES (?, ?, ?)", (habit_id, user_id, log_date))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


# ── Goals ──
@app.post("/add-goal")
def add_goal(title: str = Form(...), target: int = Form(...), emoji: str = Form("🎯"), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO goals (user_id, title, current, target, emoji) VALUES (?, ?, 0, ?, ?)", (user_id, title, target, emoji))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.post("/goal-progress")
def goal_progress(goal_id: int = Form(...), step: int = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("SELECT current, target FROM goals WHERE id=? AND user_id=?", (goal_id, user_id))
    row = cursor.fetchone()
    if row:
        cur, target = row
        new_val = cur + step
        if new_val < 0:
            new_val = 0
        if new_val > target:
            new_val = target
        cursor.execute("UPDATE goals SET current=? WHERE id=? AND user_id=?", (new_val, goal_id, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.post("/delete-goal")
def delete_goal(goal_id: int = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM goals WHERE id=? AND user_id=?", (goal_id, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


# ── Schedule ──
@app.post("/add-schedule")
def add_schedule(title: str = Form(...), start_time: str = Form(...), end_time: str = Form(...), emoji: str = Form("📌"), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schedule (user_id, title, start_time, end_time, emoji) VALUES (?, ?, ?, ?, ?)",
        (user_id, title, start_time, end_time, emoji)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


@app.post("/delete-schedule")
def delete_schedule(schedule_id: int = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule WHERE id=? AND user_id=?", (schedule_id, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)


# ── Settings ──
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user_id: int, msg: str = "", error: str = ""):
    if not check_access(request, user_id):
        return RedirectResponse(url="/login", status_code=303)

    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, xp, level FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "request": request,
        "user_id": user_id,
        "name": user[0],
        "email": user[1],
        "xp": user[2],
        "level": user[3],
        "rank": get_rank(user[3]),
        "msg": msg,
        "error": error,
    })


@app.post("/update-profile")
def update_profile(name: str = Form(...), email: str = Form(...), user_id: int = Form(...)):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, email=? WHERE id=?", (name, email, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/settings?user_id={user_id}&msg=Profile+updated", status_code=303)


@app.post("/update-password")
def update_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user_id: int = Form(...)
):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()

    # проверяем текущий пароль
    if not row or not verify_password(current_password, row[0]):
        conn.close()
        return RedirectResponse(url=f"/settings?user_id={user_id}&error=Current+password+is+wrong", status_code=303)

    # новый и подтверждение должны совпадать
    if new_password != confirm_password:
        conn.close()
        return RedirectResponse(url=f"/settings?user_id={user_id}&error=Passwords+do+not+match", status_code=303)

    hashed = hash_password(new_password)
    cursor.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/settings?user_id={user_id}&msg=Password+changed", status_code=303)