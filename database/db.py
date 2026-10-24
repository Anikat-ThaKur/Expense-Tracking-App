import os
import sqlite3

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expense_tracker.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                description TEXT,
                date        TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_expenses_user_date
                ON expenses (user_id, date);
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo1234", method="pbkdf2:sha256")),
        )
        user_id = cur.lastrowid

        expenses = [
            (45.50, "Food", "Groceries", "2026-10-01"),
            (12.00, "Transport", "Metro card top-up", "2026-10-02"),
            (89.99, "Shopping", "Running shoes", "2026-10-05"),
            (15.75, "Food", "Lunch with team", "2026-10-07"),
            (120.00, "Bills", "Electricity bill", "2026-10-10"),
            (30.00, "Entertainment", "Movie night", "2026-10-12"),
            (8.40, "Food", "Coffee and pastry", "2026-10-15"),
            (60.00, "Health", "Pharmacy", "2026-10-18"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            [(user_id, *e) for e in expenses],
        )
        conn.commit()
    finally:
        conn.close()
