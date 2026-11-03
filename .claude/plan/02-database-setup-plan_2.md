# Implementation Plan — 03 Login and Logout (built on Steps 01 and 02)

- **Inputs:** `Review/03-login-logout-review.md` (2026-10-30), `.claude/specs/03-login_logout.md`, and the live `spendly.db`
- **Note on the file name:** the requested name is `01-database-setup-plan_2.md`, but this plan implements Step 03. It replaces the Step 02 (registration) plan that was saved at this path earlier; that step is already built and its checks passed.
- **Files to change:** `app.py`, `database/db.py`, `templates/login.html`
- **Added beyond the spec's file list:** `templates/base.html` and `static/css/style.css` for the logged-in navbar (review finding 1)
- **Files to create:** none. **New dependencies:** none.

## 1. State of the inputs

**Live `spendly.db`**
- `users` holds 1 row: id 1, `Demo User`, `demo@spendly.com`, scrypt hash. Login with `demo@spendly.com` / `demo123` is the spec's main success case.
- Step 02 is built, so `create_user`, `app.secret_key`, the flash blocks and `.auth-success` already exist. Step 01 is built too.

**Review report**
- The report's section 5 ("repo state") is stale: `db.py` and `app.py` now contain Steps 01 and 02. `login()` and `logout()` in `app.py` are still stubs, and `login.html` still has the flash block only (no POST wiring).
- Findings 3 and 4 were fixed in the spec. Findings 1, 2, 5, 6, 7 and the Step 01/02 confirmation are open.

## 2. Decisions on the open findings

| # | Finding | Decision |
|---|---------|----------|
| 1 | No logged-in navbar | Add `base.html` to the change list. A context processor supplies `current_user` (the user row for `session["user_id"]`, or `None`). The navbar shows the name and a "Sign out" link when logged in, and "Sign in" / "Get started" otherwise. |
| 2 | Redirect target conflicts with Step 04 | Redirect to `url_for("landing")` as the spec says. Step 04 changes it to `/profile` when that route is built. |
| 5 | Logout uses GET | Accepted risk: the prompt requires GET. A third-party page can log a user out, which has no data impact. Recorded here. |
| 6 | Logged-in user visits `/login` | Redirect to `url_for("landing")`. |
| 7 | Email handling | Strip and lowercase the email before lookup (matches registration). |
| 8 | Session lifetime | Default browser-session cookie. `session.permanent` is not set. |
| 9 | No logout flash | Deferred: the landing page has no flash block, so a message would never show. Revisit when the dashboard exists. |
| 10 | Empty fields / `None` return | Empty email or password gives the same generic error. `get_user_by_email` returns `None` for an unknown email, and the route treats that as a failed login. |

Extra rules for the route:
- Failed login always flashes exactly `Invalid email or password.` whichever field is wrong, including unknown email and empty fields.
- For an unknown email, still run `check_password_hash` against a dummy hash, so response time does not reveal whether the email exists.
- On success call `session.clear()` first (drops stale data), then set `session["user_id"] = user["id"]` (integer).
- Stale session (the user row no longer exists): `current_user` is `None`, so the page shows the guest navbar.

## 3. `database/db.py`

Add two helpers (both open, query with `?` and close their own connection):

```
get_user_by_email(email) -> sqlite3.Row | None
get_user_by_id(user_id)  -> sqlite3.Row | None
```
- `get_user_by_email` lowercases and strips its argument.
- Both use `SELECT * FROM users WHERE ... = ?` and `fetchone()`.

## 4. `app.py`

1. Imports: add `session` and `check_password_hash` (from `werkzeug.security`); add `get_user_by_email`, `get_user_by_id` to the `database.db` import.
2. Context processor:
   ```python
   @app.context_processor
   def inject_current_user():
       user_id = session.get("user_id")
       return {"current_user": get_user_by_id(user_id) if user_id else None}
   ```
3. `login()` with `methods=["GET", "POST"]`:
   - Logged in already (`session.get("user_id")` set): redirect to `url_for("landing")`.
   - `GET`: render `login.html`.
   - `POST`: read `email` (stripped, lowercased) and `password`. Look up the user. If the user is missing, or the hash check fails, or a field is empty: flash `"Invalid email or password."` with category `error` and re-render (status 200, no redirect). Otherwise clear the session, set `session["user_id"]`, redirect to `url_for("landing")`.
   - Keep the typed email on re-render; never echo the password.
   - `abort(405)` defensive fallback, as in `register()`.
4. `logout()`: `session.clear()` then `redirect(url_for("landing"))`. Remove the stub string.

## 5. Templates and CSS

- **`login.html`:** form `method="post"` and `action="{{ url_for('login') }}"`; keep the flash loop already in place; pre-fill the email with `{{ email or '' }}`; keep the `url_for('register')` link.
- **`base.html`:** in `.nav-links`, `{% if current_user %}` show `<span class="nav-user">{{ current_user['name'] }}</span>` and `<a href="{{ url_for('logout') }}">Sign out</a>`; `{% else %}` keep the current two links.
- **`style.css`:** add `.nav-user` using existing variables only (`--ink-soft`).

## 6. Verification

Flask test client against a scratch copy of the database (patch `database.db.DB_PATH` before importing `app`), so the real `spendly.db` stays untouched. Script goes in the scratchpad.

| # | Check | Expected |
|---|-------|----------|
| 1 | `GET /login` | 200; email and password inputs; action `/login`; register link present |
| 2 | Valid login `demo@spendly.com` / `demo123` | 302 to `/`; `session["user_id"] == 1` (integer) |
| 3 | Email in other case / with spaces | Also logs in |
| 4 | Wrong password | 200; exactly "Invalid email or password."; no `user_id` in session |
| 5 | Unregistered email | Same 200 and same message |
| 6 | Empty email, empty password | Same message |
| 7 | Both failures render identical error text | Messages equal (no field is revealed) |
| 8 | Navbar when logged in | Shows "Demo User" and a link to `/logout`; no "Get started" |
| 9 | Navbar as guest | Shows "Sign in" and "Get started" |
| 10 | `GET /logout` | 302 to `/`; `user_id` no longer in session; not the raw stub string |
| 11 | Logout when not logged in | Still 302 to `/` |
| 12 | `GET /login` while logged in | 302 to `/` |
| 13 | Register then login with the new account | Works end to end |
| 14 | Stale session (user id 999) | Guest navbar, no error |
| 15 | `PUT /login` | 405 |
| 16 | `get_user_by_email` | Row for the demo user; `None` for an unknown email |
| 17 | Real `spendly.db` afterwards | Still 1 user, 8 expenses |

## 7. Definition of Done mapping

| Spec item | Checks |
|-----------|--------|
| `GET /login` renders email and password fields | 1 |
| Valid credentials set `session["user_id"]` and redirect to `/` | 2, 3 |
| Wrong password: generic flash, stays on login | 4 |
| Unregistered email: same generic flash | 5, 7 |
| `GET /logout` clears the session and redirects to `/` | 10, 11 |
| After logout `session["user_id"]` is gone | 10 |
| `/logout` no longer returns the stub string | 10 |

## 8. Implementation order

1. Add `get_user_by_email` and `get_user_by_id` to `database/db.py`.
2. Update `app.py` (imports, context processor, `login`, `logout`).
3. Update `login.html`, `base.html`, `style.css`.
4. Run the section 6 checks, plus the Step 02 registration script again to catch regressions.
5. Confirm `spendly.db` is unchanged and still ignored by git.

## 9. Risks

- **Running dev server:** a Flask debug server from earlier may still be listening on port 5001 against the real database. It reloads on file change. Verification uses the test client and a scratch DB, so it is unaffected.
- **One query per request:** the context processor reads the user on every render when a session exists. Acceptable for SQLite at this scale.
- **Signed cookies only:** the session is a client-side signed cookie, secured by `app.secret_key`. The dev fallback key must be replaced via `SECRET_KEY` before deployment.
- **Out of scope:** CSRF tokens, rate limiting, lockout, "remember me", password reset.
