# Implementation Plan — 05 Backend Routes for Profile Page

- **Inputs:** `Review/05-backend-routes-for-profile-page-review.md` (2026-10-30), `.claude/specs/05-backend-routes-for-profile-page.md`, and the live `spendly.db`
- **Files to create:** `database/queries.py`, `tests/test_backend_connection.py`
- **Files to change:** `app.py` (`profile()` view), `templates/profile.html` (variable names only)
- **New dependencies:** none (`pytest` 8.3.5 is already installed). **Database changes:** none.

## 1. State of the inputs

**Live `spendly.db` (inspected 2026-11-03)** — the values the page must now show:

| Item | Value |
|------|-------|
| User | id 1, `Demo User`, `demo@spendly.com`, `created_at` `2026-11-02 16:11:14` (member since November 2026) |
| Expenses | 8 rows, total 346.24, dates `2026-11-01` to `2026-11-22` |
| Category totals | Bills 120.00, Shopping 58.00, Food 45.50, Other 36.00, Transport 32.00, Health 28.75, Entertainment 25.99 |
| Rounded percentages | 35, 17, 13, 10, 9, 8, 8 — sum 100 |

**Code in place:** Steps 01–04 are built. `/profile` has the session guard and hardcoded dicts in `app.py`; `profile.html` already renders the four sections. `database/queries.py` and `tests/` do not exist. The review's section 5 is stale for Steps 01–04.

## 2. Decisions on the review findings

| # | Finding | Decision |
|---|---------|----------|
| 1 | Test isolation | Tests point `database.db.DB_PATH` at a temporary file before importing `app`, and rebuild it for every test. `spendly.db` is never opened. |
| 2 | Seed values | Pinned in Step 01 and checked against the live DB (section 1). The route tests assert them. |
| 3 | `member_since` | Format check in tests (`Month YYYY`), derived from `created_at`. |
| 4 | Float rounding | Helpers round `total_spent` and each category amount to 2 decimals. |
| 5 | Empty values and ties | Helpers return plain numbers (`0`); the template formats `₹0.00`. Equal category totals are broken alphabetically, so results are deterministic. Empty `top_category` is `"—"`. |
| 6 | Missing user | If `queries.get_user_by_id` returns `None`, the route clears the session and redirects to `/login`. |
| 8 | Same-date order | `ORDER BY date DESC, id DESC`. |
| 9 | Subagent wording | A process note, not a requirement. The four helpers are written directly; no subagents. |
| 10 | Limit vs count | Accepted as in the spec: the table shows at most 10 rows, the transaction count covers all expenses. |
| 11 | No `id` in transactions | Follow the spec's field list; Step 08 adds `id`. |
| 12 | Login helper in tests | Set `session["user_id"]` directly with `session_transaction()`. Registration is tested through the real `/register` route. |
| 7 | "Never raise" wording | Withdrawn in the review; no action. |

Two naming points:
- `database/db.py` already has `get_user_by_id` (returns a `Row`, used by the navbar). The new `database/queries.py` has its own `get_user_by_id` returning a dict. `app.py` imports the new module as `queries` and calls `queries.get_user_by_id`, so the two do not collide.
- The helpers call `get_db()` from `database.db` and close their connection before returning. No Flask imports.

## 3. `database/queries.py`

| Function | Behaviour |
|----------|-----------|
| `get_user_by_id(user_id)` | `SELECT name, email, created_at FROM users WHERE id = ?`. Returns `{"name", "email", "member_since"}` with `member_since` as `%B %Y` from the date part of `created_at`. `None` if no row. |
| `get_summary_stats(user_id)` | `SUM(amount)` and `COUNT(*)` for the user, and the category with the highest total (`GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1`). Returns `{"total_spent": round(total, 2), "transaction_count": n, "top_category": name}`. No expenses: `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}`. |
| `get_recent_transactions(user_id, limit=10)` | `ORDER BY date DESC, id DESC LIMIT ?`. List of `{"date", "description", "category", "amount"}`. Empty list if none. |
| `get_category_breakdown(user_id)` | Per-category `SUM(amount)` ordered by amount descending (category ascending as tiebreak). Each item `{"name", "amount": round(, 2), "pct"}`. `pct = floor(amount / total * 100 + 0.5)`; any remainder from `100 - sum(pct)` goes to the first (largest) category. Empty list if none. |

All SQL uses `?` placeholders. A `None` description is returned as `""`.

## 4. `app.py` — `profile()`

1. Keep the session guard (redirect to `/login`).
2. `user = queries.get_user_by_id(session["user_id"])`; if `None`: `session.clear()` and redirect to `/login`.
3. Add `user["initials"]` from the name (first letters of up to two words, uppercased). This is presentation, not a query, so it is built here, not in the helper.
4. `stats = queries.get_summary_stats(user_id)`, `expenses = queries.get_recent_transactions(user_id)`, `breakdown = queries.get_category_breakdown(user_id)`.
5. Render `profile.html` with the same four context names as before. Remove all hardcoded data.

## 5. `templates/profile.html`

No structural change. Only the variable names in the breakdown rows change to match the helper: `b.category` becomes `b.name`, `b.percent` becomes `b.pct` (also in the `<progress>` value and the `%` text). Amounts keep the `₹` and two-decimal format; the `₹` is already used for every amount. Dates now display as stored (`YYYY-MM-DD`).

## 6. `tests/test_backend_connection.py`

Setup: create a temp directory at module level and set `database.db.DB_PATH` before importing `app`. An autouse fixture deletes and rebuilds the temp database (`init_db()` + `seed_db()`) for each test.

**Unit tests** (the 8 rows of the spec table), plus: remainder goes to the largest category, a tie in category totals resolves alphabetically, same-date rows come back by id descending, and money values are rounded.

**Route tests**
- `GET /profile` unauthenticated: 302 to `/login`.
- Authenticated as the seed user: 200; contains "Demo User", "demo@spendly.com", `₹`; total `₹346.24`; count 8; top category "Bills"; transactions newest first; all 7 categories in the breakdown; percentages sum to 100.
- Newly registered user (through `/register` then `/login`): `₹0.00`, 0 transactions, no breakdown rows, no error.
- Session with an id that does not exist: cleared and redirected to `/login`.
- Another user's expenses do not appear on the seed user's page.

## 7. Definition of Done mapping

| Spec item | Covered by |
|-----------|-----------|
| Demo User / email from the database | route test, seed user |
| Total ₹346.24 | route test |
| Count 8 | route test |
| Top category Bills | route test |
| 8 rows newest first | route test + unit test |
| 7 categories, percentages sum to 100 | route test + unit test |
| ₹ on all amounts | route test (no `$` or `£`) |
| New user: ₹0.00, 0, empty breakdown | route test, registered user |

## 8. Implementation order

1. Write `database/queries.py`.
2. Update `app.py` and `profile.html`.
3. Write the tests and run `python -m pytest tests -q`.
4. Re-run the login, registration and profile scratch scripts. The profile script's hardcoded expectations (such as `November 2026`, 7 progress bars) should still pass on real data. Adjust the script only where the old data was hardcoded.
5. Confirm the real `spendly.db` is unchanged and, with a real server, that `curl` login then `/profile` shows the live figures.
6. Add a dated update to `Review/05-backend-routes-for-profile-page-review.md`.

## 9. Risks

- **Two `get_user_by_id` functions:** the dict-returning one in `queries.py` and the Row-returning one in `db.py`. Kept apart by importing `queries` as a module; the review notes it.
- **`created_at` is UTC:** `member_since` is the UTC month. A user created near midnight on the last day of a month could show the next month's name in another timezone. Accepted.
- **Table limit of 10:** users with more than 10 expenses see only the latest 10 rows against a full count.
