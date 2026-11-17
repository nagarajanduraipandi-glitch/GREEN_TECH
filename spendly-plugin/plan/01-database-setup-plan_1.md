# Implementation Plan (rev 1) — 01 Database Setup: close the remaining gaps

- **Inputs:** `Review/01-database-setup-review-verification.md` (dated 2026-10-30) and the live `spendly.db`
- **Supersedes nothing:** the first plan, `.claude/plan/01-database-setup-plan.md`, has already been implemented. This plan covers what the verification report still lists as open, measured against the real database.

## 1. What the live `spendly.db` shows (inspected 2026-11-02)

| Item | Observed |
|------|----------|
| Tables | `users`, `expenses` (plus SQLite's `sqlite_sequence` and the email auto-index) |
| `users` | 1 row: `Demo User`, `demo@spendly.com`, scrypt hash, `created_at` `2026-11-02 16:11:14` |
| `expenses` | 8 rows, user_id 1, all in November 2026 (`2026-11-01` to `2026-11-22`) |
| Categories | All 7 present (Food twice) |
| Total | 346.24; Bills (120.00) is the top category |
| Constraints | `NOT NULL`, `UNIQUE(email)`, FK to `users(id)`, `CHECK` on category, `created_at` default all present in the stored DDL |
| Health | `PRAGMA integrity_check` returns `ok` |

The database matches the first plan and the spec's Definition of Done on every data and schema point.

## 2. Report items versus reality

The verification report predates the implementation, so parts of it are now stale.

| Report statement | Current status | Action |
|------------------|----------------|--------|
| `db.py` is a stub; `app.py` has no DB wiring; Steps 01–09 not built (section 3, last action) | Stale: `db.py` and `app.py` are implemented for Step 01. Steps 02–09 are still not built. | Add a dated note to the report (section 4 below) |
| Findings 1, 2 done | Still true. `spendly.db` is in `.gitignore`; seed total and top category are verified in the DB. | None |
| Findings 3–6 left open as design decisions | Decided and implemented: `CHECK` constraint, path anchored to the project root, each function commits and closes its connection, `created_at` stored as `YYYY-MM-DD HH:MM:SS`. | Tick the open action and record the decisions |
| Finding 7 (seed dates vary by month) | Accepted: dates use fixed days 1–22 of the current month, so they are always valid. | Record as accepted |
| Finding 8 (`ON DELETE`) | Accepted: SQLite default (`NO ACTION`). | Record as accepted |
| Finding 9 (email case) | Deferred to Spec 02, which should lowercase the email before insert. Changing the column to `COLLATE NOCASE` here would not alter the existing table, because `CREATE TABLE IF NOT EXISTS` skips it. | Record as deferred |
| Finding 10 (`get_db` unused in `app.py`) | Still true and harmless; later steps use it. | Record as accepted |

## 3. Gaps still untested

The earlier run imported `app` but never started the server.

1. **Real server start:** run `python app.py` and confirm it starts without a traceback and serves the existing routes.
2. **Debug reloader:** `app.run(debug=True)` imports the module twice. Confirm that the database still holds exactly 1 user and 8 expenses afterwards.
3. **Restart persistence:** stop and start the server again; the row counts must not change and `created_at` of the demo user must stay `2026-11-02 16:11:14`.

No code change is expected from these checks. If one fails, fix `database/db.py` or `app.py` and re-run.

## 4. Documentation update

Edit `Review/01-database-setup-review-verification.md`:
- Add an "Update 2026-11-02" section stating that Step 01 is now implemented, with the live-database facts from section 1.
- Tick the final recommended action (findings 3–6) and list the four decisions.
- Record findings 7, 8 and 10 as accepted and finding 9 as deferred to Spec 02.
- Leave the original findings table and the 2026-10-30 text unchanged, so the history stays readable.

## 5. Implementation order

1. Start `python app.py` in the background and wait for it to listen on port 5001.
2. Request `/`, `/register`, `/login`, `/terms`, `/privacy` and confirm status 200. Confirm the placeholder routes still respond.
3. Query `spendly.db`: 1 user, 8 expenses, total 346.24, demo `created_at` unchanged.
4. Stop the server, start it again, repeat step 3.
5. Stop the server. Confirm `git status` still does not list `spendly.db`.
6. Update the verification report (section 4).

## 6. Done when

- [ ] Server starts with no traceback, with the debug reloader on
- [ ] Landing, register, login, terms and privacy pages return 200
- [ ] After two starts: 1 user, 8 expenses, total 346.24, demo `created_at` unchanged
- [ ] `spendly.db` is not in `git status`
- [ ] The verification report records the current state and the decisions on findings 3–10
