import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db"
)

CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    category_list = ", ".join(f"'{c}'" for c in CATEGORIES)
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS login_user (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES login_user(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL CHECK (category IN ({category_list})),
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_user(name, email, password):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO login_user (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), generate_password_hash(password)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM login_user WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM login_user WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM login_user").fetchone()[0] > 0:
            return

        cur = conn.execute(
            "INSERT INTO login_user (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        today = date.today()
        # (day of month, category, amount, description); amounts sum to 346.24
        samples = [
            (1, "Bills", 120.00, "Electricity and internet"),
            (3, "Food", 30.50, "Groceries"),
            (5, "Transport", 32.00, "Metro card top-up"),
            (8, "Health", 28.75, "Pharmacy"),
            (12, "Entertainment", 25.99, "Movie tickets"),
            (15, "Shopping", 58.00, "New shoes"),
            (18, "Food", 15.00, "Lunch out"),
            (22, "Other", 36.00, "Gift"),
        ]
        rows = [
            (user_id, amount, category, today.replace(day=day).isoformat(), desc)
            for day, category, amount, desc in samples
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
