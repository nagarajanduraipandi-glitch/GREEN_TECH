# Implementation Plan — 08 Edit Expense

- **Inputs:** `Review/08-edit-expense-review.md` (2026-10-30), `.claude/specs/08-edit-expense.md`, and the live `spendly.db`
- **Files to change:** `app.py`, `database/queries.py`, `templates/profile.html`, `templates/add_expense.html`, `static/css/profile.css`, `tests/test_backend_connection.py` (one assertion)
- **Files to create:** `templates/edit_expense.html`, `templates/_expense_form.html` (shared form partial), `tests/test_edit_expense.py`
- **New dependencies:** none. **Database changes:** none.

## 1. State of the inputs

**Live `spendly.db` (inspected 2026-11-03):** 1 user (id 1) and 8 expenses with ids 1–8, all owned by user 1: ids 1 Bills 120.00 (1 Nov), 2 Food 30.50 (3 Nov), 3 Transport 32.00, 4 Health 28.75, 5 Entertainment 25.99, 6 Shopping 58.00, 7 Food 15.00, 8 Other 36.00 (22 Nov). There is no second user, so "another user's expense" is tested with a temporary database.

**Code in place:** Steps 01–07 are built.
- `queries.py` has the read helpers and `insert_expense`.
- `app.py` has `validate_expense_form()` (ISO re-formatting of dates, finite and bounded amounts, 2-decimal rounding, 200-character description limit) and `CATEGORIES` is imported from `database/db.py`.
- `/expenses/<int:id>/edit` is still the one-line placeholder, and the profile table has no id or Actions column.
- The review's section 5 is stale for Steps 01–07.

## 2. Decisions on the review findings

| # | Finding | Decision |
|---|---------|----------|
| 1 | Older expenses unreachable | Accepted limitation, stated explicitly: the table keeps its 10-row cap (Step 05). Older expenses are reached through the Step 06 date filter, which shows the 10 newest rows inside the chosen range, each with an Edit link. No pagination in this step. |
| 2 | Silent no-op update | `update_expense` returns the number of rows changed (no exception when it is 0, as the spec's unit test requires). The route returns 404 when it is 0, so a deleted or foreign expense never looks like a success. |
| 3 | Validation gaps | The POST reuses `validate_expense_form()` from Step 07, so the same fixes apply: ISO date normalisation, `nan`/`inf`/huge amounts rejected, rounding, server-side description limit. |
| 4 | Return shape | `get_expense_by_id` returns a plain dict `{id, amount, category, date, description}` (like the other helpers), or `None`. |
| 5 | Category list | One list: `CATEGORIES` in `database/db.py`, used by Steps 07 and 08. |
| 6 | Filter lost after save | Accepted: the redirect is a plain `url_for("profile")`, as the spec says. |
| 7 | Error display | Flash with category `error` and re-render, like Step 07. Tests check exact message text. |
| 8 | Test isolation and login | Temporary database before importing `app`; `session["user_id"]` set directly. |
| 9 | Missing tests | Add tests for the Edit link on the profile page, category re-selection after an error, and a tampered `user_id` field. |
| 10 | Duplicated template | Move the shared form into `templates/_expense_form.html`; `add_expense.html` and `edit_expense.html` include it. The rendered HTML of the add form stays the same, and the Step 07 tests prove it. |
| 11 | CSRF | Accepted risk, as in Step 07. |
| 12 | Non-integer ids | `/expenses/abc/edit` is a 404 from Flask's `int` converter; a test records it. |

Also: the spec makes `get_recent_transactions` return `id`. That changes the dict keys the Step 05 test asserts (`{date, description, category, amount}`), so that one assertion is updated to include `id`.

## 3. `database/queries.py`

- `get_recent_transactions`: add `id` to the SELECT and to each returned dict.
- `get_expense_by_id(expense_id, user_id)`: `SELECT id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?`; returns a dict (description `""` if NULL) or `None`.
- `update_expense(expense_id, user_id, amount, category, date, description)`: `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?`; commit; return `cursor.rowcount`; close in `finally`.

## 4. `app.py` — `/expenses/<int:id>/edit`

`methods=["GET", "POST"]`, endpoint `edit_expense`. Order of checks:
1. Not logged in: redirect to `url_for("login")` (both methods).
2. `expense = queries.get_expense_by_id(id, user_id)`; `None`: `abort(404)` (also covers another user's expense, for GET and POST).
3. `GET`: render `edit_expense.html` with `expense`, `categories=CATEGORIES`, and `form` = the stored values (amount shown with two decimals).
4. `POST`: `validate_expense_form(request.form)`. On error: flash and re-render with the submitted values (200). On success: `update_expense(id, user_id, ...)`; if it returns 0, `abort(404)`; otherwise flash "Expense updated." and redirect to `url_for("profile")`.
5. `user_id` always comes from the session; the id comes from the URL; a posted `user_id` is ignored.

## 5. Templates and CSS

- `_expense_form.html`: the form body used by both pages (amount with the ₹ label, category select with the submitted/current value selected, date, description, submit button using `submit_label`, cancel link to `url_for('profile')`). The form `action` comes from `form_action`.
- `add_expense.html`: set `form_action` to `url_for('add_expense')` and `submit_label` to "Save Expense", then include the partial.
- `edit_expense.html`: title "Edit expense — Spendly"; `form_action` is `url_for('edit_expense', id=expense.id)`; `submit_label` is "Save Changes".
- `profile.html`: an "Actions" header and an "Edit" link per row, `url_for('edit_expense', id=e.id)`, class `row-action`.
- `profile.css`: `.row-action` styled with variables only. No inline styles, no hex values, no hardcoded paths.

## 6. Tests — `tests/test_edit_expense.py`

| Group | Cases |
|-------|-------|
| Unit | `get_expense_by_id`: own, wrong user, missing; `update_expense`: updates all four fields and returns 1; wrong user leaves the row unchanged and returns 0 with no error; missing id returns 0; `get_recent_transactions` includes `id` |
| Auth and 404 | GET and POST unauthenticated redirect to `/login`; GET and POST for another user's expense, a missing id and `/expenses/abc/edit` all give 404; the other user's row is unchanged |
| GET | 200; fields pre-filled with the stored values; the right category selected; form action `/expenses/<id>/edit`; "Save Changes"; cancel link to `/profile` |
| POST valid | 302 to `/profile`; database updated; updated values appear on `/profile`; no description stores NULL; whitespace description stores NULL; date `2026-3-5` is stored as `2026-03-05`; amount rounded to 2 decimals; a posted `user_id` is ignored and the owner does not change |
| POST invalid | missing, zero, negative, non-numeric, `nan`, `inf`, too-large amount; invalid category; invalid date; 201-character description: each gives 200, the exact message, an unchanged database row and the submitted values retained (including the selected category) |
| Race | Expense deleted between loading the form and submitting: POST gives 404, not a redirect |
| UI | Every row on `/profile` has an Edit link to its own id; the Actions header is present; no `$` or `£`; no inline styles or hex in the new templates |

## 7. Definition of Done mapping

| Spec item | Covered by |
|-----------|-----------|
| Logged out redirects | Auth tests |
| 404 for missing or foreign expense | 404 tests |
| Pre-filled form, correct category selected | GET tests |
| Valid save redirects and values appear | POST valid tests |
| Missing/zero amount keeps submitted values | POST invalid tests |
| Invalid category / date errors | POST invalid tests |
| No description saves | POST valid tests |
| Edit link on every row | UI tests |

## 8. Implementation order

1. Update `queries.py` (id in transactions, `get_expense_by_id`, `update_expense`), and the one assertion in `test_backend_connection.py`.
2. Add the shared partial and refactor `add_expense.html` onto it; run the Step 07 tests to confirm the output is unchanged.
3. Create `edit_expense.html`; update `profile.html` and `profile.css`.
4. Update `app.py`.
5. Write `tests/test_edit_expense.py` and run `python -m pytest tests -q`.
6. Re-run the earlier scratch scripts (login, registration).
7. Real-server check with `curl` against a scratch copy of `spendly.db` (the live database is never written): edit expense 2, confirm the profile shows the new values, and that another id gives 404.
8. Add a dated update to `Review/08-edit-expense-review.md`.

## 9. Risks

- **Template refactor:** touching `add_expense.html` risks changing Step 07 output; the existing Step 07 tests guard it.
- **Edit link on filtered views:** the redirect after saving drops the active date filter (accepted).
- **404 on a lost race:** the form data is not kept, because the expense no longer exists.
