# Review Report — 09-delete-expense.md vs Spec_09-delete-expense_prompt.md

- **Spec reviewed:** `.claude/specs/09-delete-expense.md`
- **Source prompt:** `Spec_09-delete-expense_prompt.md`
- **Related files checked:** `app.py` (placeholder routes), `static/css/style.css` (CSS variables), `database/` and `tests/` listings, Specs 05, 07 and 08 for cross-step consistency
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 11 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line, including the 3-row unit test table, the 5 route tests and the ownership rules. There are three deviations (section 3). The findings below include one concrete naming conflict with the existing `app.py`, plus gaps the prompt leaves open around CSRF and tests.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only) |
| Bullet lists throughout | Pass |
| Table for the unit test cases | Pass (Function / Input / Expected output, 3 rows) |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/09-delete-expense.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass, with a deviation | All 6 points; confirm() wording differs |
| Depends on | Pass | Steps 01, 03, 05, 08 |
| Routes | Pass | POST-only route; GET returns 405 |
| Database changes | Pass | None |
| Templates | Pass, with a deviation | Delete form, confirm, `btn-delete`, Edit link kept |
| Files to change | Pass, with a deviation | `queries.py`, `app.py`, `profile.html`, `style.css` |
| Files to create | Pass | None |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 13 rules, including the inline-style exception |
| Tests to write | Pass | 3 unit rows; 5 route tests |
| Definition of done | Pass | All 7 items, same wording |

## 3. Deviations and additions

- **Overview wording.** The prompt's Overview says the confirm() dialog is "in the button's onclick handler", but its own Templates section puts it in `onsubmit` on the `<form>`. The spec's Overview says "the form's onsubmit handler", matching the Templates section. This changes an Overview sentence from the prompt, so it is a deviation, made to remove a contradiction.
- **Hardcoded path replaced.** The prompt writes the form action as `/expenses/{{ tx.id }}/delete`, which contradicts its own rule to use `url_for()` for every internal link. The spec describes it as `url_for`-generated.
- **Decorator code removed.** The prompt gives the decorator as literal code, which conflicts with "No code" for the spec. The spec says the route must allow the POST method only.
- Title line `# Spec 09 — Delete Expense`.

## 4. Findings

### High

1. **Name collision with the existing view function.** `app.py` already defines a view function named `delete_expense` for this route. The spec tells the implementer to import `delete_expense` from `database.queries`, so the import would be shadowed (or would overwrite the view) and the route would call itself or fail. Rename the view (for example `delete_expense_view`) or import the helper under an alias. The other steps avoid this because their helpers are named `insert_expense`, `get_expense_by_id` and `update_expense`.
2. **No CSRF protection on a destructive POST.** Any other site can submit a hidden form to `/expenses/<id>/delete` for a logged-in user and delete expenses. Steps 07 and 08 have the same gap, but deletion is irreversible. Add a token requirement or record it as an accepted risk.

### Medium

3. **Most Definition of Done items have no automated test.** The browser-confirm, cancel-confirm and "shows both Edit and Delete" items have no matching test. Add a route test that the profile page contains the delete form with the correct URL and the `btn-delete` class.
4. **Redundant lookup, no result from the delete.** The route calls `get_expense_by_id` and then `delete_expense`, and the delete helper returns nothing. If the row disappears between the two calls, the user is still redirected as if it succeeded. Having `delete_expense` return the affected row count lets the route return 404 and removes the extra query.
5. **Inline script and inline style.** The spec allows `style="display:inline"` and an inline `onsubmit` handler. Both can be replaced by a CSS class and a listener in `static/js/main.js` (which `base.html` already loads), keeping the "no inline styles" rule without an exception. At minimum the exception is a one-off that later steps could copy.
6. **No confirmation after deletion.** There is no flash message, and no template currently displays flashed messages (see the Step 06 review). The user sees only a refreshed list.
7. **Unauthenticated GET versus POST.** The route is POST-only, so an unauthenticated GET returns 405, not a redirect to `/login`. This is correct per the prompt, but the Definition of Done says only that GET returns 405 without noting it applies to logged-out users too.

### Low

8. **`.btn-delete` location.** The spec adds it to `style.css`, while profile page styles live in `profile.css` (Steps 05–06). The `--danger` and `--danger-light` variables already exist in `style.css`, so the rule is satisfiable; the spec should name which variable to use.
9. **Filter and page state are lost** after deletion, because the redirect goes to a plain `/profile` (same as Step 08).
10. **Test isolation and login helper are not specified**, same as the Step 05 review.
11. **Permanent deletion with no undo or soft delete.** Accepted by the prompt, but worth recording.

## 5. Repo state

- `/expenses/<int:id>/delete` in `app.py` is still the placeholder stub with a single GET handler named `delete_expense`, which is what causes finding 1.
- `database/queries.py`, `templates/profile.html` and `tests/` do not exist; `.btn-delete` is not in `style.css`.
- `static/css/style.css` already defines `--danger` and `--danger-light`.
- The step has therefore not been built, although the prompt describes Steps 01–08 as complete.

## 6. Recommended actions

- [ ] Rename the view function or alias the helper import to avoid the `delete_expense` collision — finding 1
- [ ] Add a CSRF token requirement or record the risk as accepted — finding 2
- [ ] Add a route test that the profile page renders the delete form with the correct URL and class — finding 3
- [ ] Have `delete_expense` return the affected row count, and return 404 from the route when it is 0 — finding 4
- [ ] Consider moving the confirm handler and display style into `main.js` and CSS — finding 5
- [ ] Decide whether to flash a confirmation message — finding 6
- [ ] Name the CSS variable for `.btn-delete` (`--danger`) — finding 8
- [ ] Specify the temporary-database and session-login approach for tests — finding 10
- [ ] Confirm Steps 01–08 and this step are really implemented before relying on "complete" statuses — section 5
