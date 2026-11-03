# Implementation Plan — 07 Add Expense

- **Inputs:** `Review/07-add-expense-review.md` (2026-10-30), `.claude/specs/07-add-expense.md`, and the live `spendly.db`
- **Files to change:** `app.py`, `database/queries.py`, `templates/profile.html`, `templates/base.html`, `static/css/style.css`, `static/css/profile.css`
- **Files to create:** `templates/add_expense.html`, `tests/test_add_expense.py`
- **New dependencies:** none. **Database changes:** none.

## 1. State of the inputs

**Live `spendly.db` (inspected 2026-11-03):** 1 user, 8 expenses, total 346.24. The `expenses` table already enforces `user_id` as a foreign key to `users`, `amount REAL NOT NULL`, `date TEXT NOT NULL`, nullable `description`, and `category` through `CHECK (category IN (7 names))`. So the database already rejects a bad user or category; the route still validates first so users see a clear message.

**Code in place:** Steps 01–06 are built. `/expenses/add` is still the one-line GET placeholder. `database/queries.py` has the read helpers. `CATEGORIES` (the 7 names) already exists in `database/db.py`. The logged-in navbar exists (`current_user`). `form-group`, `form-input`, `btn-submit`, `auth-section` and `auth-container` are already in `style.css`. The review's section 5 is stale for Steps 01–06.

## 2. Decisions on the review findings

| # | Finding | Decision |
|---|---------|----------|
| 1 | Non-ISO dates stored | Parse with `strptime("%Y-%m-%d")`, then save `parsed.date().isoformat()`, never the raw text. `2026-3-5` is stored as `2026-03-05`. |
| 2 | Non-finite / huge amounts | Reject `nan`, `inf` and values above a maximum of 10,000,000 (`math.isfinite`). Also reject zero and negatives. Round to 2 decimals before saving. |
| 3 | Error display | Errors are flashed with category `error` and the form is re-rendered (same pattern as register and login). The first failing rule is shown. Tests check the exact message text. |
| 4 | Description limit | Enforced on the server: strip, then reject more than 200 characters. Blank becomes `None`. |
| 5 | New row may not appear in the list | The table is capped at 10 newest rows. The tests use a recent date so the row appears; the redirect goes to a plain `/profile`, which clears any active filter. |
| 6 | `insert_expense` contract | Opens its own connection, inserts with `?` placeholders, commits, closes in `finally`, and returns the new row id. It does not validate; database constraints raise `sqlite3.IntegrityError`. |
| 7 | Navbar link owner | The logged-in navbar exists from Step 03; this step adds the "Add Expense" link in its logged-in branch. |
| 8 | Test isolation and login | Temporary database before importing `app`, and `session["user_id"]` set through `session_transaction()`, as in the earlier test files. |
| 9 | CSRF | Accepted risk for this project stage; recorded here. |
| 10 | Test gaps | Add tests: unknown `user_id` raises `IntegrityError`; the saved row belongs to the session user even if a `user_id` is posted; a 201-character description is rejected. |
| 11 | Re-render details | The submitted category stays selected after an error. |
| 12 | Default date | The server supplies today's date on a fresh form, using `get_today()` from `app.py`. |
| 13 | Currency label | The amount field is labelled "Amount (₹)". |

## 3. `database/queries.py` — `insert_expense`

```
insert_expense(user_id, amount, category, date, description) -> int
```
- `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`.
- Commit, return `cursor.lastrowid`, close the connection in `finally`.
- A missing user or invalid category raises `sqlite3.IntegrityError` (not caught).

## 4. `app.py` — `/expenses/add`

- `@app.route("/expenses/add", methods=["GET", "POST"])`; not logged in: redirect to `url_for("login")` for both methods.
- `GET`: render `add_expense.html` with `categories=CATEGORIES`, an empty `form` dict and the default date.
- `POST`: read `amount`, `category`, `date`, `description` from the form (never `user_id`; the session supplies it). Validate in this order and stop at the first failure:

| Rule | Message |
|------|---------|
| Amount empty | "Amount is required." |
| Amount not a number, not finite, zero or negative | "Enter a valid amount greater than 0." |
| Amount above 10,000,000 | "Amount is too large." |
| Category not one of the 7 | "Choose a valid category." |
| Date empty or not a real `YYYY-MM-DD` date | "Enter a valid date." |
| Description over 200 characters after stripping | "Description must be 200 characters or fewer." |

- On failure: flash the message and re-render with the submitted values (200).
- On success: `queries.insert_expense(user_id, round(amount, 2), category, iso_date, description or None)`, flash "Expense added." (success), redirect to `url_for("profile")`. The profile page has no flash block for success today, so the flash is shown there only if added; a success flash block is added to `profile.html` (the existing block already renders both categories).

## 5. Templates and CSS

- **`add_expense.html`:** extends `base.html`; title "Add expense — Spendly"; uses the existing `auth-section` / `auth-container` / `auth-card` layout and `form-group` / `form-input` / `btn-submit` classes. Flash loop, then `<form method="post" action="{{ url_for('add_expense') }}">` with:
  - amount: `type="number"`, `step="0.01"`, `min="0.01"`, `required`, label "Amount (₹)"
  - category: `<select>` with the 7 options and the submitted one selected
  - date: `type="date"`, `required`, value from the form or today
  - description: `type="text"`, `maxlength="200"`, optional
  - "Save Expense" submit and a "Cancel" link to `url_for('profile')`.
- **`profile.html`:** a `panel-header` row around the "Transaction history" heading with an "Add Expense" link (`url_for('add_expense')`).
- **`base.html`:** "Add Expense" link in the logged-in navbar branch.
- **CSS:** `.form-actions`, `.btn-cancel` and a select rule in `style.css`; `.panel-header` and `.btn-add` in `profile.css`. Variables only; no inline styles.

## 6. Tests — `tests/test_add_expense.py`

Temporary database; `session["user_id"]` set directly.

| Group | Cases |
|-------|-------|
| Unit | Insert with description; insert with `None` stores NULL; returns an id; unknown user raises `IntegrityError`; invalid category raises `IntegrityError` |
| Auth | GET and POST unauthenticated redirect to `/login` |
| GET | 200; select with exactly 7 options; form method POST, action `/expenses/add`; default date present; "Amount (₹)" label |
| POST valid | 302 to `/profile`; row exists for the session user; amount, category and date stored; the row appears on `/profile` |
| POST invalid | missing, zero, negative, non-numeric, `nan`, `inf`, `1e999`, too large; invalid category; invalid, empty and impossible dates; 201-character description; each gives 200, the exact message, no new row, and submitted values kept (category still selected) |
| Edge | No description stores NULL; whitespace-only description stores NULL; `2026-3-5` is stored as `2026-03-05`; amount `10.005`-style input is rounded to 2 decimals; a posted `user_id` is ignored |
| UI | Profile page has an "Add Expense" link to `/expenses/add`; navbar shows the link when logged in and not as a guest; no `$` or `£`; no inline styles in the new template |

## 7. Definition of Done mapping

| Spec item | Covered by |
|-----------|-----------|
| Logged out redirects | Auth tests |
| Form fields present | GET tests |
| Exactly 7 categories | GET test |
| Valid submit redirects and the row appears | POST valid tests |
| Missing/zero amount re-renders with values kept | POST invalid tests |
| Invalid category / date error | POST invalid tests |
| No description saves | Edge tests |
| Profile button and navbar link | UI tests |

## 8. Implementation order

1. Add `insert_expense`.
2. Update `app.py`.
3. Create `add_expense.html`; update `profile.html`, `base.html` and the two stylesheets.
4. Write the tests and run `python -m pytest tests -q`.
5. Re-run the earlier scratch scripts (login, registration, profile).
6. Real-server check with `curl`: start the server with `database.db.DB_PATH` pointed at a scratch copy of `spendly.db`, log in as the demo user, add an expense and confirm it shows on `/profile`. The live `spendly.db` is never written; its counts (1 user, 8 expenses) are checked before and after.
7. Add a dated update to `Review/07-add-expense-review.md`.

## 9. Risks

- **Live data:** the real-server check runs against a scratch copy, so the real database is not written.
- **No CSRF token:** accepted for now.
- **Future dates:** the spec does not forbid them, so they are accepted.
