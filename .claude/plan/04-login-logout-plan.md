# Implementation Plan — 04 Profile Page (hardcoded UI data)

- **Inputs:** `Review/04-profile-review.md` (2026-10-30), `.claude/specs/04-profile.md`, and the live `spendly.db`
- **Note on the file name:** the requested name is `04-login-logout-plan.md`, but this plan implements Step 04 (profile page). It is kept at that path as asked.
- **Files to change:** `app.py`, `templates/base.html` (one navbar link)
- **Files to create:** `templates/profile.html`, `static/css/profile.css`
- **New dependencies:** none. **Database changes:** none, and the route runs no queries (spec rule).

## 1. State of the inputs

**Live `spendly.db` (inspected 2026-11-02)** — the data the hardcoded values must mirror:

| Item | Value |
|------|-------|
| User | id 1, `Demo User`, `demo@spendly.com`, created `2026-11-02` |
| Expenses | 8 rows, 7 categories, total 346.24, top category Bills |
| Category totals | Bills 120.00, Shopping 58.00, Food 45.50 (2 rows), Other 36.00, Transport 32.00, Health 28.75, Entertainment 25.99 |
| Dates | 2026-11-01 to 2026-11-22 |

**Code already in place:** Steps 01–03 are built. `base.html` already shows the logged-in navbar (name and Sign out, from `current_user`). `/profile` in `app.py` is still the stub string. `templates/profile.html` and `static/css/profile.css` do not exist.

## 2. Decisions on the review findings

| # | Finding | Decision |
|---|---------|----------|
| 1 | No file for styles | Create `static/css/profile.css`, loaded from `profile.html` through the `head` block and `url_for('static', ...)`. Already in the spec. |
| 2, 7 | Logged-in navbar owner and variable | Already done in Step 03: `base.html` reads `current_user` (set by a context processor from `session["user_id"]`). Only addition here: a "Profile" link in the logged-in navbar so the page can be reached. |
| 3 | Currency | `₹` everywhere; amounts formatted with two decimals. |
| 4 | Mirror seed data | The hardcoded dicts use the exact values in section 1. |
| 5 | Avatar initials | Hardcoded in the user dict (`"DU"`), as the spec's "all hardcoded values" implies. |
| 6 | Badge class naming | One shared `.badge` class plus one modifier per category (`.badge-food`, `.badge-transport`, `.badge-bills`, `.badge-health`, `.badge-entertainment`, `.badge-shopping`, `.badge-other`), all defined in `profile.css`. The template builds the class from the category name; no colour is set inline. |
| 8 | Empty state | The template shows a short message when the expenses or breakdown list is empty, so Step 05 works for new users without a redesign. |
| 9 | Row count | 8 rows, matching the seed data. |
| 10 | Member-since | `"November 2026"` (Month YYYY, from the seed user's creation month). |
| — | Post-login redirect | Left at `/`. Spec 04 does not change it. A later step can send users to `/profile`. |
| — | Progress bars without inline styles | Use `<progress max="100" value="...">` styled in `profile.css`, because an inline `width` is forbidden. |

Known limit of the spec: the page shows the Demo User's hardcoded data to whoever is logged in. The navbar still shows the real logged-in name. Step 05 replaces the data with real queries.

## 3. `app.py`

1. In the `/profile` view, replace the stub:
   ```python
   if not session.get("user_id"):
       return redirect(url_for("login"))
   ```
2. Build four hardcoded context values and call `render_template("profile.html", user=..., stats=..., expenses=..., breakdown=...)`:
   - `user = {"name": "Demo User", "email": "demo@spendly.com", "initials": "DU", "member_since": "November 2026"}`
   - `stats = {"total_spent": 346.24, "transaction_count": 8, "top_category": "Bills"}`
   - `expenses`: 8 dicts (`date`, `description`, `category`, `amount`), newest first, with the seed rows (22 Nov Gift 36.00 down to 1 Nov Electricity and internet 120.00).
   - `breakdown`: 7 dicts (`category`, `amount`, `percent`), largest first, with percent: Bills 34.7, Shopping 16.8, Food 13.1, Other 10.4, Transport 9.2, Health 8.3, Entertainment 7.5 (sums to 100.0).
3. No database call in this view.

## 4. `templates/profile.html`

Extends `base.html`; title block "Profile — Spendly"; `head` block loads `profile.css`. No inline styles, no hex colours, no hardcoded paths. Four sections:

1. **User info card:** avatar circle with initials, name, email, "Member since {{ user.member_since }}".
2. **Summary stats row:** three tiles — Total spent (`₹346.24`), Transactions (8), Top category (Bills).
3. **Transaction history table:** columns Date, Description, Category (badge), Amount (`₹`, right-aligned). Empty-state message if the list is empty.
4. **Category breakdown:** one row per category with the name, `₹` amount, percent and a `<progress>` bar. Empty-state message if empty.

## 5. `static/css/profile.css`

- Uses only existing CSS variables (`--paper-card`, `--border`, `--ink*`, `--accent*`, `--danger*`, `--radius-*`, `--font-*`, `--max-width`). No hex values.
- Layout classes for the page container, user card, avatar, stats grid, table, breakdown rows.
- Badge colours come from `color-mix()` of existing variables, so seven categories get distinct tones without new hex values.
- `progress` styled for both WebKit (`::-webkit-progress-bar`, `::-webkit-progress-value`) and Firefox (`::-moz-progress-bar`).
- A small-screen rule that stacks the stats grid and lets the table scroll.

## 6. `templates/base.html`

In the logged-in branch of the navbar, add `<a href="{{ url_for('profile') }}">Profile</a>` before "Sign out". Nothing else changes.

## 7. Verification

Flask test client against a scratch copy of the database (patch `database.db.DB_PATH` before importing `app`). Then one real-server check with `curl`.

| # | Check | Expected |
|---|-------|----------|
| 1 | `GET /profile` with no session | 302 to `/login` |
| 2 | `GET /profile` after login | 200 |
| 3 | User card | Contains "Demo User", "demo@spendly.com", "November 2026", "DU" |
| 4 | Stats | Contains `₹346.24`, `8`, `Bills` |
| 5 | Table | 8 body rows; each with a `badge badge-<category>` class and a `₹` amount |
| 6 | Breakdown | 7 rows, 7 `progress` elements |
| 7 | Navbar | Shows the user's name, a Profile link and a Sign out link |
| 8 | No `$` or `£` currency symbols | None in the response |
| 9 | No `style=` attribute and no hex colour in `profile.html` | Search the file: none |
| 10 | No hex colour in `profile.css` | Search the file: none |
| 11 | All internal links use `url_for` | No hardcoded paths in `profile.html` |
| 12 | CSS reachable | `GET /static/css/profile.css` returns 200 |
| 13 | Login/registration regression | Earlier scratch-DB scripts still pass |
| 14 | Real `spendly.db` afterwards | Still 1 user, 8 expenses |

## 8. Definition of Done mapping

| Spec item | Checks |
|-----------|--------|
| Redirect to `/login` when logged out | 1 |
| HTTP 200 when logged in | 2 |
| User card with name and email | 3 |
| At least three stat values | 4 |
| Table with at least three rows | 5 |
| Breakdown with at least three categories | 6 |
| Navbar shows username and logout link | 7 |
| No hex colours in `profile.html` | 9 |

## 9. Implementation order

1. Write `profile.css` and `profile.html`.
2. Update `app.py` and the `base.html` navbar link.
3. Run the section 7 checks and the regression scripts.
4. Update `Review/04-profile-review.md` with a dated section: current repo state and a decision for every finding, with the recommended actions ticked.

## 10. Risks

- **Hardcoded data for every user:** by the spec's design, a newly registered user sees the Demo User's figures on `/profile`. This is removed in Step 05.
- **`color-mix()`:** supported by current browsers; older ones fall back to the base text colour on the badge.
- **Stale statements in the review:** the repo-state section of the review predates Steps 01–03.
