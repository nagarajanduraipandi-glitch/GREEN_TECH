# Review Report — 08-edit-expense.md vs Spec_08-edit-expense_prompt.md

- **Spec reviewed:** `.claude/specs/08-edit-expense.md`
- **Source prompt:** `Spec_08-edit-expense_prompt.md`
- **Related files checked:** `app.py`, `database/` and `tests/` listings, Specs 05, 06, 07 and 09 for cross-step consistency
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 11 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line, including the 5-row unit test table, the 13 route tests and the ownership rules. There are two deliberate deviations (section 3). The findings below are gaps the prompt leaves open, mainly what happens when an update changes nothing, and expenses that cannot be reached from the profile list.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only) |
| Bullet lists throughout | Pass |
| Table for the unit test cases | Pass (Function / Input / Expected output, 5 rows) |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/08-edit-expense.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass | All 6 points |
| Depends on | Pass | Steps 01, 03, 05, 07 |
| Routes | Pass | GET and POST `/expenses/<int:id>/edit`, logged-in only |
| Database changes | Pass | None; column list as given |
| Templates | Pass, with deviations | `edit_expense.html` fields and buttons; `profile.html` Actions column and Edit link |
| Files to change | Pass, with a deviation | `queries.py` (3 changes), `app.py`, `profile.html` |
| Files to create | Pass | `templates/edit_expense.html` |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 14 rules, including both ownership guards |
| Tests to write | Pass | 5 unit rows; 13 route tests |
| Definition of done | Pass | All 10 items, same wording |

## 3. Deviations and additions

- **Hardcoded paths replaced.** The prompt writes the form action as `/expenses/{{ expense.id }}/edit`, the cancel link as `/profile`, and the Edit link as `/expenses/{{ tx.id }}/edit`, which contradicts its own rule to use `url_for()` for every internal link. The spec describes all three as `url_for`-generated.
- **Decorator code removed.** The prompt gives the decorator as literal code, which conflicts with "No code" for the spec. The spec says the route must accept GET and POST.
- Title line `# Spec 08 — Edit Expense`.

None change the requirements.

## 4. Findings

### High

1. **Older expenses cannot be edited.** The only entry point is the Edit link in the profile table, and that table shows the 10 newest rows (Step 05 `limit=10`, and Step 06 can narrow it further). Expenses outside that view have no link, so they cannot be reached from the interface. Raise or remove the limit for this table, add pagination, or accept the limitation explicitly.
2. **Updates that match no row look like success.** `update_expense` is specified to be silent when no row is affected (the unit test even requires "0 rows affected, no error"). The route is not told to check the result, so if the expense is deleted between the form load and the submit, the user is redirected to `/profile` as if it had been saved. The helper should report whether a row changed, and the route should return 404 when it did not.

### Medium

3. **Inherited validation gaps from Step 07.** The rules are "identical to Step 07", so the same weaknesses apply: non-ISO dates such as `2026-3-5` accepted by `strptime`, and non-finite amounts such as `inf`, with no maximum or rounding. See the Step 07 review, findings 1 and 2.
4. **Return type is inconsistent.** `get_expense_by_id` is tested as returning "a dict-like object", while Step 05 helpers return plain dicts. The template reads `expense.id`, which works for both, but the spec should name one shape.
5. **Category list source is undefined.** The route passes "categories list" to the template, but the spec does not say where the 7 categories are defined. Steps 07 and 08 would otherwise each define their own copy.
6. **Filter and page state are lost.** After a successful save the user is sent to a plain `/profile`, dropping any active date filter from Step 06.
7. **Error display mechanism is unspecified**, same as Steps 06 and 07: no template displays flashed messages, and tests only check for "an error message" with no expected text.
8. **Test isolation and login helper are not specified**, same as the Step 05 review.

### Low

9. **Missing test coverage.** No test covers the Edit link on the profile page (it has a Definition of Done item but no test), the select keeping the submitted category after a failed save, or a user trying to change `user_id` through form fields.
10. **Duplicated template.** `edit_expense.html` is described as identical to `add_expense.html`, which suggests a shared partial; the spec does not mention one.
11. **No CSRF protection**, as in Step 07.
12. **Non-integer ids.** `/expenses/abc/edit` is handled by Flask's int converter and returns 404; the spec does not list it, but behaviour is correct.

## 5. Repo state

- `/expenses/<int:id>/edit` in `app.py` is still the placeholder stub.
- `database/queries.py`, `templates/profile.html`, `templates/edit_expense.html` and `tests/` do not exist; `database/db.py` is a 5-line comment stub.
- The step has therefore not been built, although later prompts describe it as complete.

## 6. Recommended actions

- [ ] Make older expenses reachable (higher limit, pagination, or an explicit accepted limitation) — finding 1
- [ ] Have `update_expense` report affected rows and return 404 from the route when none changed — finding 2
- [ ] Apply the Step 07 fixes (ISO date normalisation, finite and bounded amounts) to this step — finding 3
- [ ] Name one return shape for `get_expense_by_id` — finding 4
- [ ] Define one shared category list — finding 5
- [ ] Decide whether the date filter is preserved after saving — finding 6
- [ ] Add tests for the Edit link, category re-selection on error and tampered `user_id` — finding 9
- [ ] Specify the temporary-database and session-login approach for tests — finding 8
- [ ] Confirm Steps 01–07 and this step are really implemented before relying on "complete" statuses — section 5
