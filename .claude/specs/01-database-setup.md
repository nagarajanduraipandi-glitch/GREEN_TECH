# Spec 01 — Database Setup

## 1. Overview

- Replaces the stub in `database/db.py` with a working SQLite implementation: a connection helper, schema creation, and development seed data.
- This is the foundational step: nothing else in Spendly can store or read data until it exists.
- Authentication (registration, login/logout), the profile page, and expense tracking (add, edit, delete, filtering) all depend on it.

## 2. Depends on

- None. This is the first step and has no prerequisites.

## 3. Routes

- No new routes.
- Existing placeholder routes in `app.py` remain unchanged.

## 4. Database Schema

### Table A: `users`

| Column | SQLite Type | Constraints |
|--------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| name | TEXT | NOT NULL |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL, DEFAULT current timestamp |

### Table B: `expenses`

| Column | SQLite Type | Constraints |
|--------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FOREIGN KEY → users(id) |
| amount | REAL | NOT NULL |
| category | TEXT | NOT NULL (must be one of the fixed categories in section 10) |
| date | TEXT | NOT NULL — must be in `YYYY-MM-DD` format |
| description | TEXT | nullable |
| created_at | TEXT | NOT NULL, DEFAULT current timestamp |

## 5. Functions to Implement (database/db.py)

| Function | Behavior |
|----------|----------|
| `get_db()` | Opens `spendly.db` in the project root; sets `row_factory = sqlite3.Row`; enables `PRAGMA foreign_keys = ON`; returns the connection |
| `init_db()` | Creates both tables with `CREATE TABLE IF NOT EXISTS`; safe to call multiple times |
| `seed_db()` | Checks whether the `users` table already has rows — if yes, returns early. Otherwise inserts one demo user (name: Demo User, email: demo@spendly.com, password: demo123 hashed via werkzeug) and 8 sample expenses linked to that user, covering all 7 categories, with dates spread across the current month. The 8 expense amounts must sum to 346.24, and Bills must be the category with the highest total (later steps assert these values) |

## 6. Changes to app.py

- Import `get_db`, `init_db`, `seed_db` from `database.db`.
- Call `init_db()` and `seed_db()` inside `app.app_context()` on startup.
- The database must be ready before any route is served.

## 7. Files to Change

- `database/db.py`
- `app.py`

## 8. Files to Create

- None.

## 9. Dependencies

- No new pip packages.
- Use `sqlite3` (standard library) and `werkzeug.security` (already installed).

## 10. Categories (Fixed List)

These are the only valid values for `expenses.category`:

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

## 11. Rules for Implementation

- No ORM, no SQLAlchemy.
- Parameterized queries only — never string formatting in SQL.
- `PRAGMA foreign_keys = ON` on every connection.
- Store `amount` as REAL, not INTEGER.
- Hash passwords with `generate_password_hash` from `werkzeug.security`.
- `seed_db()` must be idempotent (safe to call multiple times).
- Dates must always be `YYYY-MM-DD`.

## 12. Expected Behavior

- `get_db()` returns a usable connection whose rows are accessible by column name and which enforces foreign keys.
- `init_db()` creates `spendly.db` and both tables on first call; further calls change nothing and raise no error.
- `seed_db()` on an empty database inserts the demo user (with a hashed password) and 8 expenses covering all 7 categories within the current month; on a database that already has users it does nothing.
- Database-level constraints must enforce:
  - `users.email` is unique.
  - `expenses.user_id` must reference an existing user.
  - `NOT NULL` columns reject missing values.
  - `created_at` is filled automatically when not supplied.

## 13. Error Handling Expectations

- Duplicate email insert → UNIQUE constraint failure (`sqlite3.IntegrityError`).
- Expense with an invalid `user_id` → foreign key constraint failure (`sqlite3.IntegrityError`).
- Invalid queries → raise clear errors for debugging; do not swallow exceptions.

## 14. Definition of Done

- [ ] Database file created on app startup
- [ ] Both tables exist with correct schema and constraints
- [ ] Demo user exists with hashed password
- [ ] 8 sample expenses exist across all 7 categories
- [ ] No duplicate seed data on repeated runs
- [ ] App starts without errors
- [ ] Foreign key enforcement works
- [ ] All queries use parameterized SQL
