# Implementation Plan — 09 Delete Expense

- **Inputs:** `Review/09-delete-expense-review.md` (2026-10-30), `.claude/specs/09-delete-expense.md`, and the live `spendly.db`
- **Files to change:** `app.py`, `database/queries.py`, `templates/profile.html`, `static/css/style.css`, `static/js/main.js`
- **Files to create:** `tests/test_delete_expense.py`
- **New dependencies:** none. **Database changes:** none.

## 1. State of the inputs

**Live `spendly.db` (inspected 2026-11-03):** 1 user, 8 expenses with ids 1–8, total 346.24, all owned by user 1. This plan never deletes from the live database; every delete check runs against a temporary or scratch copy.

**Code in place:** Steps 01–08 are built.
- `queries.py` has `get_expense_by_id`, `update_expense` and `insert_expense`.
- `/expenses/<int:id>/delete` in `app.py` is still the GET placeholder `delete_expense`.
- The profile table already has the Actions column with an Edit link per row, and its flash block renders success messages.
- `static/js/main.js` is an empty comment and `base.html` already loads it. `--danger` and `--danger-light` exist in `style.css`.
- The review's section 5 is stale for Steps 01–08.

## 2. Decisions on the review findings

| # | Finding | Decision |
|---|---------|----------|
| 1 | Name collision on `delete_expense` | No collision in practice: `app.py` imports `queries` as a module and calls `queries.delete_expense(...)`, so the helper never shares a namespace with the view function. The view keeps the name `delete_expense` (the endpoint used by `url_for`). A test pins this. |
| 2 | No CSRF protection on a destructive POST | Partly mitigated: set `SESSION_COOKIE_SAMESITE = "Lax"`, so browsers do not send the login cookie on cross-site POSTs. A full token system is out of scope (it would also change the Step 07 and 08 forms). Recorded as an accepted residual risk. |
| 3 | Missing route tests for the UI | Add tests that `/profile` renders a delete form per row with the right URL and the `btn-delete` class, next to the Edit link. |
| 4 | Redundant lookup, no result | `delete_expense` returns the number of rows deleted. The route calls only it and returns 404 when it is 0. This is one atomic query that still enforces ownership through `WHERE id = ? AND user_id = ?`, and it removes the race between a lookup and the delete. (This replaces the spec's separate `get_expense_by_id` call; the outcome is the same.) |
| 5 | Inline `style` and `onsubmit` | Neither is used. The form gets a CSS class (`inline-form`) and a `data-confirm="Delete this expense?"` attribute; a listener in `main.js` calls `confirm()` and cancels the submit when the user declines. This keeps the "no inline styles" rule without the exception. |
| 6 | No confirmation message | Flash "Expense deleted." (success) before the redirect; the profile page already displays it. |
| 7 | Unauthenticated GET vs POST | The route is POST-only, so a GET gets 405 for everyone, logged in or not. A logged-out POST redirects to `/login`. Both are tested. |
| 8 | Where `.btn-delete` lives | `static/css/style.css` as the spec says, using `--danger` (text and border) and `--danger-light` (hover). |
| 9 | Filter lost after deleting | Accepted: the redirect is a plain `/profile`, as in Step 08. |
| 10 | Test isolation and login | Temporary database before importing `app`; `session["user_id"]` set directly. |
| 11 | Permanent deletion | Accepted: there is no undo or soft delete. |

## 3. `database/queries.py`

`delete_expense(expense_id, user_id)`: `DELETE FROM expenses WHERE id = ? AND user_id = ?`, commit, return `cursor.rowcount`, close in `finally`. No exception for a missing or foreign row; the count is 0.

## 4. `app.py`

- `app.config["SESSION_COOKIE_SAMESITE"] = "Lax"`.
- `@app.route("/expenses/<int:id>/delete", methods=["POST"])`:
  1. Not logged in: redirect to `url_for("login")`.
  2. `deleted = queries.delete_expense(id, session["user_id"])`; if 0: `abort(404)`.
  3. Flash "Expense deleted." (success) and redirect to `url_for("profile")`. No template is rendered.

## 5. Templates, CSS and JS

- `profile.html`: in each row's Actions cell, after the Edit link, add `<form method="post" action="{{ url_for('delete_expense', id=e.id) }}" class="inline-form" data-confirm="Delete this expense?">` containing `<button type="submit" class="btn-delete">Delete</button>`.
- `style.css`: `.inline-form { display: inline; margin: 0; }` and `.btn-delete` (danger text, no background, `--danger-light` on hover, cursor pointer, body font). Variables only.
- `main.js`: one `submit` listener (event delegation on `document`) for forms with `data-confirm`; `if (!confirm(message)) event.preventDefault();`.

## 6. Tests — `tests/test_delete_expense.py`

| Group | Cases |
|-------|-------|
| Unit | `delete_expense`: own row removed and returns 1; wrong user returns 0 and the row remains; missing id returns 0 and the database is unchanged; other rows stay |
| Auth | POST unauthenticated redirects to `/login` and deletes nothing |
| Route | Own expense: 302 to `/profile`, row gone, "Expense deleted." shown; other user's expense: 404 and the row remains; missing id: 404; deleting the same id twice gives 302 then 404; only the target row is removed; the deleted row no longer appears on `/profile`; totals update |
| Methods | GET gives 405 for a logged-in user, a guest and a missing id; PUT and DELETE give 405 |
| UI | Every profile row has an Edit link and a delete form with action `/expenses/<id>/delete`, `class="btn-delete"` and `data-confirm`; no `onsubmit` and no `style=` attribute anywhere in `profile.html`; `main.js` contains the confirm listener |
| Security | The session cookie has `SameSite=Lax`; the helper is reached as `queries.delete_expense`, so the view name does not shadow it |

## 7. Definition of Done mapping

| Spec item | Covered by |
|-----------|-----------|
| Logged out POST redirects | Auth test |
| Non-existent or foreign expense gives 404 | Route tests |
| GET gives 405 | Methods tests |
| Confirming removes the expense | Route test; the confirm dialog itself is a browser behaviour covered by the `data-confirm` and `main.js` checks |
| Redirect to `/profile` without the deleted row | Route test |
| Cancelling the dialog leaves the expense | `main.js` prevents the submit on cancel (listener test); not clickable in an automated browser here |
| Edit and Delete on every row | UI test |

## 8. Implementation order

1. Add `delete_expense` to `queries.py`.
2. Update `app.py` (cookie setting and the POST-only route).
3. Update `profile.html`, `style.css` and `main.js`.
4. Write the tests and run `python -m pytest tests -q`.
5. Re-run the earlier scratch scripts.
6. Real-server check with `curl` against a scratch copy of `spendly.db`: GET gives 405, delete expense 3, a second delete gives 404, the profile no longer lists it. The live database is never written.
7. Add a dated update to `Review/09-delete-expense-review.md`.

## 9. Risks

- **Confirm needs JavaScript:** with JavaScript off the form submits without a prompt. Accepted; the same applies to the spec's inline `onsubmit`.
- **Residual CSRF:** `SameSite=Lax` helps in current browsers, but there is no token. Recorded.
- **Not browser-tested:** the confirm and cancel behaviour is checked through the markup and script, not by clicking in a browser.
