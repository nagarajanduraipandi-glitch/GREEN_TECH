# Implementation Plan — 06 Date Filter for the Profile Page

- **Inputs:** `Review/06-date-filter-profile-review.md` (2026-10-30), `.claude/specs/06-date-filter-profile.md`, and the live `spendly.db`
- **Files to change:** `app.py`, `database/queries.py`, `templates/profile.html`, `static/css/profile.css`
- **Files to create:** `tests/test_date_filter.py` (the spec has no tests section; review finding 1)
- **New dependencies:** none (standard library `datetime` and `calendar`). **Database changes:** none.

## 1. State of the inputs

**Live `spendly.db` (inspected 2026-11-03, today is 2026-11-03)**

| Item | Value |
|------|-------|
| Users / expenses | 1 user (`demo@spendly.com`), 8 expenses, total 346.24 |
| Expense dates | 2026-11-01, 03, 05, 08, 12, 15, 18, 22 |

The seed dates run to 22 November, but today is 3 November. So "This Month" (first of month through today) will show only the 1 Nov and 3 Nov rows (Bills 120.00 and Food 30.50) on the live data. That is correct under the spec's "ending today" rule, and it is the live example for the manual check.

**Code in place:** Steps 01–05 are built. The three query helpers exist and are wired to `/profile`; `profile.html` and `profile.css` exist. No flash block exists in `profile.html` yet (`login.html` and `register.html` have one). The review's section 5 is stale for Steps 01–05.

## 2. Decisions on the review findings

| # | Finding | Decision |
|---|---------|----------|
| 1 | No tests section | Write `tests/test_date_filter.py`: reversed, malformed, one-sided, empty range, presets, clamping, active state. Uses a temporary database and a patchable "today". |
| 2 | Flash not displayed | Add a flash block above the filter bar in `profile.html` (spec already says so). Reuse the global `.auth-error` style. |
| 3, 4 | Date windows | Per the spec: "This Month" is the 1st of the current month through today. "Last 3/6 Months" is the same day 3 or 6 calendar months earlier (clamped to month end) through today. Month arithmetic uses `calendar.monthrange`. |
| 5 | Custom form method | `method="get"`, action `url_for("profile")` (already in the spec). |
| 6 | One-sided range | Accepted limitation: if either date is missing or malformed the view is unfiltered, exactly as the spec says. No flash for this case. |
| 7 | Highlight conflicts | A preset wins. If the validated range equals a preset's range, only that preset is highlighted. The custom fields are highlighted only when no preset matches. "All Time" is active when there is no filter. |
| 8 | Dynamic SQL | One helper returns a fixed text fragment (`" AND date BETWEEN ? AND ?"`) plus the two bound values, or an empty fragment and no values. No dates are formatted into SQL. |
| 9 | Equal dates | `date_from == date_to` is valid (a single day). Only `date_from > date_to` is rejected. The flash text stays as the spec words it. |
| 10 | Filter lost after add/edit/delete | Out of scope; Steps 07–09 will redirect to a plain `/profile`. Recorded. |
| 11 | Limit of 10 vs the count | Accepted: the table shows at most 10 rows of the range, the count covers the whole range. |
| 12 | Depends on omits Step 03 | Already added to the spec. |

## 3. `database/queries.py`

- Private helper `_date_filter(date_from, date_to)` returns `(" AND date BETWEEN ? AND ?", (date_from, date_to))` when both are given, otherwise `("", ())`.
- `get_summary_stats(user_id, date_from=None, date_to=None)`, `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)` and `get_category_breakdown(user_id, date_from=None, date_to=None)` append the fragment to their `WHERE user_id = ?` clause and extend the parameter tuple.
- With both dates `None` the SQL and results are identical to Step 05.
- Ordering, the limit, rounding and the percentage logic are unchanged. An empty range returns the same empty shapes as a user with no expenses.

## 4. `app.py`

1. Imports: `calendar`, `date` and `datetime` from `datetime`.
2. `get_today()` returns `date.today()`. Tests replace it with a fixed date.
3. `add_months(d, months)` moves a date back by whole months and clamps the day to the last day of the target month.
4. `parse_date(value)` returns the ISO string if `datetime.strptime(value, "%Y-%m-%d")` succeeds, otherwise `None` (also for `None` or empty).
5. `build_presets(today)` returns `{"This Month": (first of month, today), "Last 3 Months": (add_months(today, 3), today), "Last 6 Months": (add_months(today, 6), today)}` as ISO strings.
6. In `profile()`, after the session and user checks:
   - Read and validate `date_from` and `date_to`. If either is `None`, set both to `None`.
   - If `date_from > date_to`: flash "Start date must be before end date." (category `error`) and set both to `None`.
   - Build the preset links with `url_for("profile", date_from=..., date_to=...)`; the "All Time" link is `url_for("profile")` with no parameters.
   - Mark the active control: a preset whose range equals the validated range, "All Time" when there is no filter, otherwise custom.
   - Pass the three helper calls the validated dates, and pass `presets` (label, url, active), `date_from`, `date_to` and `custom_active` to the template.

## 5. `templates/profile.html` and `static/css/profile.css`

- Above the stats row, add the flash loop (error and success styles) and then the filter bar: four preset links (class `filter-btn`, plus `filter-btn-active` when active) and the custom form (`method="get"`, `action="{{ url_for('profile') }}"`, two `type="date"` inputs named `date_from` and `date_to`, prefilled with the validated values, and an "Apply" button). The form gets `filter-custom-active` when a custom range is active.
- No structural change to the other sections. No inline styles, no hex values, no hardcoded paths.
- CSS: `.filter-bar`, `.filter-presets`, `.filter-btn`, `.filter-btn-active`, `.filter-custom`, `.filter-custom-active`, `.filter-input`, small-screen stacking. Variables only.

## 6. Tests — `tests/test_date_filter.py`

Temporary database (as in `test_backend_connection.py`), `app.get_today` patched to 2026-11-15, and a user with expenses on fixed dates (for example 2026-05-31, 2026-08-15, 2026-09-10, 2026-11-01, 2026-11-15, 2026-11-20).

| Group | Cases |
|-------|-------|
| Presets | `add_months` clamping (31 May minus 3 months is 28 Feb 2026; 31 Mar minus 1 month); preset ranges for the fixed today |
| Query helpers | Filtered stats, transactions and breakdown for a range; inclusive bounds; no dates equals unfiltered; empty range gives zeros and empty lists |
| Route | No params equals Step 05 data; each preset link; "All Time" has a clean URL; a valid custom range; reversed range gives the flash and the unfiltered view; malformed date gives the unfiltered view without a flash; one-sided range gives the unfiltered view; equal dates work; empty range shows ₹0.00, 0, no breakdown |
| Active state | Matching preset is highlighted and the custom form is not; custom range highlights the form and no preset; no params highlights All Time |
| Rendering | Every amount keeps `₹`; no `$` or `£`; the custom form is GET and posts to `/profile` |

## 7. Definition of Done mapping

| Spec item | Covered by |
|-----------|-----------|
| No params equals Step 05 | route test |
| This Month / 3 Months / 6 Months / All Time | preset route tests |
| Valid custom range | route test + helper tests |
| Reversed range: flash and fallback | route test |
| Malformed date: silent fallback | route test |
| Active state visible | active-state tests |
| ₹ everywhere | rendering test |
| Empty range: ₹0.00, 0, empty breakdown | route test |

## 8. Implementation order

1. Update `database/queries.py`.
2. Update `app.py`.
3. Update `profile.html` and `profile.css`.
4. Write the tests and run `python -m pytest tests -q`.
5. Re-run the login, registration and profile scratch scripts.
6. Real-server check with `curl` against the live data: unfiltered, `This Month` (expect 2 rows), a custom range, a reversed range, a malformed date. Confirm `spendly.db` is unchanged.
7. Add a dated update to `Review/06-date-filter-profile-review.md`.

## 9. Risks

- **Live "This Month" looks small:** the seed dates run past today, so the preset shows only 1 Nov and 3 Nov rows today. This is correct, not a bug.
- **Server date:** presets use the server's local date, not the user's timezone.
- **Existing tests:** the Step 05 tests call the helpers without dates and must still pass unchanged.
