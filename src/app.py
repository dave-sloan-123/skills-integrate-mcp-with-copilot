"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Initial seed data for a fresh database.
SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

DB_DIR = current_dir / "data"
DB_PATH = DB_DIR / "school.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL CHECK (max_participants > 0)
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                UNIQUE(activity_id, user_id),
                FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        activity_count = conn.execute("SELECT COUNT(*) AS count FROM activities").fetchone()["count"]

        if activity_count == 0:
            for activity_name, details in SEED_ACTIVITIES.items():
                cursor = conn.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        activity_name,
                        details["description"],
                        details["schedule"],
                        details["max_participants"],
                    ),
                )
                activity_id = cursor.lastrowid

                for email in details["participants"]:
                    conn.execute(
                        "INSERT OR IGNORE INTO users (email) VALUES (?)",
                        (email,),
                    )
                    user_id = conn.execute(
                        "SELECT id FROM users WHERE email = ?",
                        (email,),
                    ).fetchone()["id"]

                    conn.execute(
                        """
                        INSERT OR IGNORE INTO enrollments (activity_id, user_id)
                        VALUES (?, ?)
                        """,
                        (activity_id, user_id),
                    )


@app.on_event("startup")
def on_startup():
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                a.name,
                a.description,
                a.schedule,
                a.max_participants,
                u.email
            FROM activities a
            LEFT JOIN enrollments e ON e.activity_id = a.id
            LEFT JOIN users u ON u.id = e.user_id
            ORDER BY a.name, u.email
            """
        ).fetchall()

    activities = {}
    for row in rows:
        activity_name = row["name"]
        if activity_name not in activities:
            activities[activity_name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }
        if row["email"] is not None:
            activities[activity_name]["participants"].append(row["email"])

    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_connection() as conn:
        activity_row = conn.execute(
            "SELECT id, max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()

        if activity_row is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        activity_id = activity_row["id"]
        max_participants = activity_row["max_participants"]

        conn.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (email,))
        user_id = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()["id"]

        existing = conn.execute(
            "SELECT 1 FROM enrollments WHERE activity_id = ? AND user_id = ?",
            (activity_id, user_id),
        ).fetchone()
        if existing is not None:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        current_count = conn.execute(
            "SELECT COUNT(*) AS count FROM enrollments WHERE activity_id = ?",
            (activity_id,),
        ).fetchone()["count"]

        if current_count >= max_participants:
            raise HTTPException(
                status_code=400,
                detail="Activity is full"
            )

        conn.execute(
            "INSERT INTO enrollments (activity_id, user_id) VALUES (?, ?)",
            (activity_id, user_id),
        )

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_connection() as conn:
        activity_row = conn.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity_row is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if user_row is None:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        deleted = conn.execute(
            "DELETE FROM enrollments WHERE activity_id = ? AND user_id = ?",
            (activity_row["id"], user_row["id"]),
        )
        if deleted.rowcount == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

    return {"message": f"Unregistered {email} from {activity_name}"}
