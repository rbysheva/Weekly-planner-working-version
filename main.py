import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import Form
from fastapi.responses import RedirectResponse
import calendar
from datetime import datetime

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

@app.get("/register", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )

@app.post("/register")
def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, password)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
    url="/login",
    status_code=303
    )   

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.post("/login")
def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cursor.fetchone()

    conn.close()

    if user:
        task_conn = sqlite3.connect("weekplanner.db")
        task_cursor = task_conn.cursor()

        task_cursor.execute(
        "SELECT title, day FROM tasks WHERE user_id=?",
        (user[0],)
        )

        tasks = task_cursor.fetchall()

        task_conn.close()

        current_date = datetime.now()

        month_name = current_date.strftime("%B")
        year = current_date.year
        current_day = current_date.day

        cal = calendar.monthcalendar(year, current_date.month)

        return templates.TemplateResponse(
             request=request,
            name="dashboard.html",
            context={
                "request": request,
                "name": user[1],
                "user_id": user[0],
                "tasks": tasks,
                "xp": user[4],
                "level": user[5],
                "calendar": cal,
                "month_name": month_name,
                "year": year,
                "current_day": current_day
            }
        )

    return RedirectResponse(
            url=f"/dashboard?user_id={user[0]}",
            status_code=303
        )

@app.get("/add-task", response_class=HTMLResponse)
def add_task_page(
    request: Request,
    user_id: int
):
    return templates.TemplateResponse(
        request=request,
        name="add_task.html",
        context={
            "request": {},
            "user_id": user_id
        }
    )

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    
    request: Request,
    user_id: int
):
    
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, xp, level FROM users WHERE id=?",
        (user_id,)
    )  
    user = cursor.fetchone()    

    name = user[0]
    xp = user[1]
    level = user[2]

    current_date = datetime.now()

    month_name = current_date.strftime("%B")
    year = current_date.year
    current_day = current_date.day

    cal = calendar.monthcalendar(year, current_date.month)

    if level >= 50:
        rank = "Pokemon Champion"
    elif level >= 40:
        rank = "Elite Four Member"
    elif level >= 30:
        rank = "Gym Leader"
    elif level >= 20:
        rank = "Gym Challenger"
    elif level >= 15:
        rank = "Expert Trainer"
    elif level >= 10:
        rank = "Ace Trainer"
    elif level >= 5:
        rank = "Rising Trainer"
    else:
        rank = "Pokemon Trainer"

    cursor.execute(
    "SELECT title, day, status FROM tasks WHERE user_id=?",
    (user_id,)
    )

    tasks = cursor.fetchall()

    conn.close()

    print("USER:", user)
    print("TASKS:", tasks)
    
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
            "current_day": current_day
        }
    )

@app.get("/edit-task/{title}", response_class=HTMLResponse)
def edit_task_page(
    request: Request,
    title: str,
    user_id: int
):
    return templates.TemplateResponse(
        request=request,
        name="edit_task.html",
        context={
            "request": request,
            "title": title,
            "user_id": user_id
        }
    )

@app.post("/edit-task/{old_title}")
def update_task(
    old_title: str,
    title: str = Form(...),
    day: str = Form(...),
    user_id: int = Form(...)
):

    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET title=?, day=?
        WHERE title=?
        """,
        (title, day, old_title)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
    url=f"/dashboard?user_id={user_id}",
    status_code=303
    )

@app.post("/add-task")
def save_task(
    title: str = Form(...),
    description: str = Form(...),
    day: str = Form(...),
    user_id: int = Form(...)
):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tasks (
            title,
            description,
            day,
            status,
            user_id
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            title,
            description,
            day,
            "Pending",
            user_id
        )
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
    url=f"/dashboard?user_id={user_id}",
    status_code=303
    )

@app.post("/delete-task")
def delete_task(
    title: str = Form(...),
    user_id: int = Form(...)
):
    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE title=?",
        (title,)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
    url=f"/dashboard?user_id={user_id}",
    status_code=303
    )

@app.post("/complete-task")
def complete_task(
    title: str = Form(...),
    user_id: int = Form(...)
):

    conn = sqlite3.connect("weekplanner.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET status='Completed'
        WHERE title=? AND user_id=?
        """,
        (title, user_id)
    )

    cursor.execute(
    """
    UPDATE users
    SET xp = xp + 10
    WHERE id = ?
    """,
    (user_id,)
    )
    cursor.execute(
    """
    SELECT xp, level
    FROM users
    WHERE id = ?
    """,
    (user_id,)
    )

    cursor.execute(
    """
    SELECT xp, level
    FROM users
    WHERE id = ?
    """,
    (user_id,)
    )

    user = cursor.fetchone()

    xp = user[0]
    level = user[1]


    if xp >= 100:
        cursor.execute("""
        UPDATE users
        SET level = level + 1,
            xp = 0
        WHERE id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
        url=f"/dashboard?user_id={user_id}",
        status_code=303
    )


