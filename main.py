import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import Form
from fastapi.responses import RedirectResponse

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

        return templates.TemplateResponse(
             request=request,
            name="dashboard.html",
            context={
                "request": {},
                "name": user[1],
                "user_id": user[0],
                "tasks": tasks,
                "xp": user[4],
                "level": user[5]
            }
        )

    return {
        "message": "Invalid email or password"
    }

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
    "SELECT name FROM users WHERE id=?",
    (user_id,)
    )

    user = cursor.fetchone()
    name = user[0]

    cursor.execute(
    "SELECT title, day, status FROM tasks WHERE user_id=?",
    (user_id,)
    )

    tasks = cursor.fetchall()

    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "tasks": tasks,
            "user_id": user_id,
            "name": name
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

    conn.commit()
    conn.close()

    return RedirectResponse(
        url=f"/dashboard?user_id={user_id}",
        status_code=303
    )