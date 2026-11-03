# Implementation Plan — 01 Database Setup

- **Spec:** `.claude/specs/01-database-setup.md`
- **Review:** `.claude/specs/01-database-setup-review.md`
- **Review verification:** `Review/01-database-setup-review-verification.md` (2026-10-30)
- **Files to change:** `database/db.py` (currently a 5-line comment stub), `app.py` (no DB code yet)
- **Files to create:** none
- **New dependencies:** none (`sqlite3`, `werkzeug.security`)

## 0. Current state

- `database/db.py` is still the comment stub: no functions, no `spendly.db` reference. `app.py` has no DB wiring. Step 01 is entirely unimplemented in this working tree, and so are Steps 02–09.
- The verification report confirms findings 1 and 2. Both are already handled in the spec set: `spendly.db` is in `.gitignore`, and spec section 5 requires the seed amounts to sum to 346.24 with Bills as the top category.
- Findings 3–6 are real spec gaps that the report left open as design decisions. Section 1 resolves them.
- Findings 7–10 are low severity. Section 1 accepts or defers each one.
- The old comparison against `claude/spec/spec.md` was withdrawn (the file does not exist), so nothing from it is used.

## 1. Decisions that close the review findings

| Finding | Severity | Decision |
|---------|----------|----------|
| #1 `spendly.db` not git-ignored | High | Done per the report. Re-check in verification step 16. |
| #2 Seed data not pinned | High | The spec requires sum 346.24 and Bills highest. This plan pins the exact 8 rows (section 2). |
| #3 Category enforcement | Medium | Add a SQL `CHECK (category IN (...))` on `expenses.category`, built from one `CATEGORIES` constant. |
| #4 Ambiguous DB path | Medium | Build the path from `__file__`: `<project root>/spendly.db`, independent of the working directory. |
| #5 Connection lifecycle | Medium | `get_db()` only opens. `init_db()` and `seed_db()` commit and close their own connections. Later helpers do the same. |
| #6 `created_at` format | Medium | `DEFAULT (datetime('now'))`, stored as `YYYY-MM-DD HH:MM:SS`. |
| #7 Seed dates vary by month | Low | Keep "current month" (the prompt requires it). Use fixed days 1–28 so dates are always valid. |
| #8 `ON DELETE` | Low | Keep the SQLite default (`NO ACTION`). The spec does not ask for cascade. |
| #9 Email case | Low | Out of scope here. Spec 02 should lowercase the email before inserting. |
| #10 Unused `get_db` import | Low | Keep it, as the spec says. Later steps use it. |

## 2. Pinned seed data

Dates are the stated day of the current month, formatted `YYYY-MM-DD`.

| Day | Category | Amount | Description |
|-----|----------|--------|-------------|
| 1 | Bills | 120.00 | Electricity and internet |
| 3 | Food | 30.50 | Groceries |
| 5 | Transport | 32.00 | Metro card top-up |
| 8 | Health | 28.75 | Pharmacy |
| 12 | Entertainment | 25.99 | Movie tickets |
| 15 | Shopping | 58.00 | New shoes |
| 18 | Food | 15.00 | Lunch out |
| 22 | Other | 36.00 | Gift |

Check: 120.00 + 30.50 + 32.00 + 28.75 + 25.99 + 58.00 + 15.00 + 36.00 = **346.24**. Bills (120.00) beats Food (45.50). All 7 categories appear, 8 rows total.

## 3. `database/db.py`

Replace the stub with the following structure.

**Module level**
- Imports: `sqlite3`, `os`, `date` from `datetime`, `generate_password_hash` from `werkzeug.security`.
- `DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db")`
- `CATEGORIES` tuple with the 7 fixed names (single source for the `CHECK` clause and the seed).

**`get_db()`**
1. `conn = sqlite3.connect(DB_PATH)`
2. `conn.row_factory = sqlite3.Row`
3. `conn.execute("PRAGMA foreign_keys = ON")`
4. `return conn`

**`init_db()`**
1. `conn = get_db()`
2. `CREATE TABLE IF NOT EXISTS users`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `name TEXT NOT NULL`, `email TEXT NOT NULL UNIQUE`, `password_hash TEXT NOT NULL`, `created_at TEXT NOT NULL DEFAULT (datetime('now'))`.
3. `CREATE TABLE IF NOT EXISTS expenses`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL REFERENCES users(id)`, `amount REAL NOT NULL`, `category TEXT NOT NULL CHECK (category IN (<CATEGORIES>))`, `date TEXT NOT NULL`, `description TEXT`, `created_at TEXT NOT NULL DEFAULT (datetime('now'))`.
4. `conn.commit()`, then `conn.close()` in a `try/finally`.

The `CHECK` list comes from the constant `CATEGORIES`, never from user input.

**`seed_db()`**
1. `conn = get_db()`
2. `SELECT COUNT(*) FROM users`. If above 0, close and return.
3. Insert the demo user with `?` placeholders: `("Demo User", "demo@spendly.com", generate_password_hash("demo123"))`. Take the id from `cursor.lastrowid`.
4. Build the 8 rows from section 2 with `date.today().replace(day=N).isoformat()`.
5. `conn.executemany("INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)", rows)`
6. `conn.commit()`, then `conn.close()` in a `try/finally`. Do not catch exceptions.

## 4. `app.py`

1. Add `from database.db import get_db, init_db, seed_db` below the Flask import.
2. After `app = Flask(__name__)`, add:
   ```python
   with app.app_context():
       init_db()
       seed_db()
   ```
3. Leave every route unchanged.

If `database/__init__.py` does not exist, the import still works as a namespace package. Confirm this in step 4 of section 7.

## 5. Verification

Run from the project root, then once from a different working directory to prove the path anchoring.

| # | Check | How | Expected |
|---|-------|-----|----------|
| 1 | App starts | `python app.py` | No traceback; `spendly.db` appears in the project root |
| 2 | Tables exist | `sqlite3 spendly.db ".schema"` | Both tables match the spec, including the `CHECK` |
| 3 | Demo user | `SELECT name, email, password_hash FROM users` | One row; hash is not `demo123` |
| 4 | Password hash works | `check_password_hash(hash, "demo123")` | `True` |
| 5 | Seed count | `SELECT COUNT(*), COUNT(DISTINCT category) FROM expenses` | `8, 7` |
| 6 | Seed total | `SELECT ROUND(SUM(amount), 2) FROM expenses` | `346.24` |
| 7 | Top category | `SELECT category FROM expenses GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1` | `Bills` |
| 8 | Dates | Compare every `date` to `YYYY-MM-DD` and the current month | All match |
| 9 | Idempotent | Run the app twice | Still 1 user, 8 expenses |
| 10 | Unique email | Insert `demo@spendly.com` again | `sqlite3.IntegrityError` |
| 11 | FK enforced | Insert an expense with `user_id = 999` through `get_db()` | `sqlite3.IntegrityError` |
| 12 | Category check | Insert category `Travel` | `sqlite3.IntegrityError` |
| 13 | NOT NULL | Insert an expense with `amount = NULL` | `sqlite3.IntegrityError` |
| 14 | `created_at` default | Insert a row without it | Value like `2026-11-02 10:15:00` |
| 15 | Path anchoring | Run the app by absolute path from another directory | One `spendly.db`, in the project root |
| 16 | Git ignore | `git status` | `spendly.db` not listed |

Write these checks as a throwaway script in the scratchpad, not in the repo.

## 6. Definition of Done mapping

| Spec item | Verified by |
|-----------|-------------|
| Database file created on app startup | Check 1 |
| Both tables exist with correct schema and constraints | Checks 2, 10, 11, 12, 13 |
| Demo user exists with hashed password | Checks 3, 4 |
| 8 sample expenses across all 7 categories | Checks 5, 6, 7 |
| No duplicate seed data on repeated runs | Check 9 |
| App starts without errors | Check 1 |
| Foreign key enforcement works | Check 11 |
| All queries use parameterized SQL | Code review: every value goes through `?`; the only interpolated string is the constant `CATEGORIES` in the DDL |

## 7. Implementation order

1. Write `database/db.py` (section 3).
2. Run `init_db()` and `seed_db()` from a Python shell and check results 2–9.
3. Edit `app.py` (section 4).
4. Start the app and run checks 1, 15 and 16.
5. Run the constraint checks 10–14.
6. Confirm `.gitignore` contains `spendly.db`.

## 8. Risks and notes

- **Existing database file:** `CREATE TABLE IF NOT EXISTS` will not alter a table that already exists. If a `spendly.db` was created earlier with a different schema, delete it and restart.
- **Flask debug reloader:** `app.run(debug=True)` imports the module twice, so `init_db()` and `seed_db()` run twice at startup. This is safe because both are idempotent.
- **Spec deviation:** the `CHECK` constraint is not in the spec. It follows section 10's "only valid values" rule. Remove it if you want the spec followed literally.
- **Status of later steps:** the verification report notes that later prompts describe Steps 01–09 as complete, but the code is not built. Treat only this plan's checks as proof of Step 01.
