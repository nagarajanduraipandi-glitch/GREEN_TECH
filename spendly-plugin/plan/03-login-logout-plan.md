# Implementation Plan — 03 Login and Logout (reconciliation)

- **Inputs:** `Review/03-login-logout-review.md` (2026-10-30), `.claude/specs/03-login_logout.md`, and the live `spendly.db`
- **Why a reconciliation plan:** Step 03 was already built in this working tree from the earlier plan (the one that was saved at `.claude/plan/01-database-setup-plan_2.md`). This plan records the current state, finds what is still open, and closes it. It does not rebuild working code.

## 1. State of the inputs

**Live `spendly.db` (inspected 2026-11-02)**
- `users` has 1 row: id 1, `Demo User`, `demo@spendly.com`, scrypt hash, `created_at` `2026-11-02 16:11:14`.
- `expenses` has 8 rows. Nothing has changed since Step 01; the Step 02 and 03 checks ran against scratch copies.

**Code already in place**
- `database/db.py`: `get_user_by_email`, `get_user_by_id`, `create_user`.
- `app.py`: `app.secret_key`, a `current_user` context processor, `login()` (GET and POST, generic error, session set, logged-in redirect) and `logout()` (clears the session, redirects to `/`).
- `templates/login.html`: POST form with `url_for('login')`, flash block, pre-filled email, `url_for('register')` link.
- `templates/base.html` and `static/css/style.css`: logged-in navbar with the user's name and a "Sign out" link.

## 2. Review findings versus the code

| # | Finding | Status |
|---|---------|--------|
| 1 | Logged-in navbar | Done in `base.html` |
| 2 | Redirect target vs Step 04 | Decided: redirect to `/` now; Step 04 moves it to `/profile` |
| 3 | Existing form duplicated | Done: the existing form was updated, not duplicated |
| 4 | `secret_key` | Done (set in `app.py`) |
| 5 | Logout uses GET | Accepted risk: the prompt requires GET |
| 6 | Logged-in user visits `/login` | Done: redirects to `/` |
| 7 | Email normalisation | Done: stripped and lowercased |
| 8 | Session lifetime | Accepted: default browser-session cookie |
| 9 | Logout flash | Deferred: the landing page has no flash block to show it |
| 10 | Empty fields / `None` return | Done: same generic error; `get_user_by_email` returns `None` for an unknown email |
| §5 | Repo state: stubs, Steps 01 and 02 unbuilt | Stale: all built |

## 3. What is still open

1. **Review report is out of date.** Its section 5 says `app.py` and `db.py` are stubs, and its recommended actions are mostly unticked.
2. **Real server not exercised.** The earlier checks used Flask's test client. A real HTTP login with a cookie jar, against the server still running on port 5001, has not been done. Login only reads the database, so it is safe on the real `spendly.db`.

## 4. Implementation

1. **Real-server check** (port 5001, `curl` with a cookie jar):

   | # | Request | Expected |
   |---|---------|----------|
   | a | `GET /login` | 200, form with `email` and `password` |
   | b | `POST /login` with `demo@spendly.com` / `demo123` | 302 to `/`, a session cookie is set |
   | c | `GET /` with the cookie | Contains "Demo User" and a `/logout` link |
   | d | `POST /login` wrong password | 200, "Invalid email or password." |
   | e | `GET /logout` with the cookie | 302 to `/` |
   | f | `GET /` after logout | Guest navbar ("Get started"), no "Demo User" |

2. **Regression:** re-run the scratch-DB login and registration scripts.
3. **Update `Review/03-login-logout-review.md`:** add a dated "Update 2026-11-02" section with the current repo state and a decision for each open finding (table in section 2), and tick the recommended actions that are now done. Leave the 2026-10-30 text unchanged.
4. **Confirm** the real `spendly.db` still has 1 user and 8 expenses, and that `git status` does not list it.

## 5. Done when

- [ ] Real-server steps a–f behave as expected
- [ ] Scratch-DB login and registration scripts pass
- [ ] The review report records the current state and a decision on every finding
- [ ] `spendly.db` unchanged (1 user, 8 expenses) and not in `git status`

## 6. Notes

- The Definition of Done in the spec maps to the earlier checks: valid login and session key (2, 3), generic failure message (4–7), logout clears the session (10, 11), stub string gone (10).
- Out of scope: CSRF tokens, rate limiting, lockout, "remember me", password reset, logout flash.
