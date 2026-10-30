# Review Report — 07-add-expense.md vs Spec_07-add-expense_prompt.md

- **Spec reviewed:** `.claude/specs/07-add-expense.md`
- **Source prompt:** `Spec_07-add-expense_prompt.md`
- **Related files checked:** `app.py`, `database/` and `tests/` listings, `templates/base.html`, Specs 05, 06 and 08 for cross-step consistency
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 11 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line, including the test table and all 4 validation rules. There is one deliberate deviation (section 3). The findings below are gaps the prompt leaves open, mainly date and amount validation, and the pieces other steps assume.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only) |
| Bullet lists throughout | Pass |
| Table for the unit test cases | Pass (Function / Input / Expected output, 2 rows) |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/07-add-expense.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass | All 5 points |
| Depends on | Pass | Steps 01, 03, 04/05 |
| Routes | Pass | GET and POST /expenses/add, logged-in only |
| Database changes | Pass | None; column list as given |
| Templates | Pass, with one deviation | `add_expense.html` fields, button, error block; `profile.html` and `base.html` changes |
| Files to change | Pass | `app.py`, `queries.py`, `profile.html`, `base.html` |
| Files to create | Pass | `templates/add_expense.html` |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 13 rules, including the 4 numbered validation rules |
| Tests to write | Pass | 2 unit rows; 10 route tests |
| Definition of done | Pass | All 10 items, same wording |

## 3. Deviations and additions

- **Deliberate deviation:** the prompt writes the form action as `/expenses/add` and the cancel link as `/profile`, which contradicts its own rule to use `url_for()` for every internal link. The spec writes both as `url_for`-generated. The "Add Expense" button on `profile.html` still names `/expenses/add` in its description, which is a destination rather than a hardcoded link.
- Title line `# Spec 07 — Add Expense`.
- Unit-test inputs written as "Valid user_id, ..." instead of "insert_expense with valid user_id, ...".

None change the requirements.

## 4. Findings

### High

1. **Dates can be stored in a non-ISO form.** `datetime.strptime` with `%Y-%m-%d` accepts values such as `2026-3-5`. If the parsed value is not re-formatted before saving, the stored text sorts and compares incorrectly, which breaks newest-first ordering (Step 05) and BETWEEN filtering (Step 06). The spec should require saving the re-formatted ISO string, not the raw input.
2. **`float()` accepts values that are not usable amounts.** `float("inf")` and `float("1e999")` are positive and pass the "greater than 0" check; `nan` is rejected only by accident. The spec does not require rejecting non-finite values or setting a maximum, and does not say to round to two decimals.

### Medium

3. **Flashed or error messages have no display mechanism.** The spec asks for a "flash/error message block" inside `add_expense.html`, but does not say whether errors are passed as a template variable or flashed. No existing template calls `get_flashed_messages`. Tests only check that "an error message" appears, with no expected text.
4. **Description limit is client-side only.** The 200-character cap is described on the input but not enforced by the server rules, so a direct POST can store longer text. Whitespace-only descriptions becoming NULL are covered by rule 4 but not tested.
5. **The new expense may not appear in the list.** The Definition of Done says the new expense "appears in the transaction list", but the list is capped at 10 newest-first rows (Step 05), and an old date would fall outside it. An active date filter (Step 06) could also hide it.
6. **`insert_expense` contract is thin.** The return value (new id or nothing), commit, and connection closing are not stated, although Step 05 requires helpers to close their own connections.
7. **Navbar link depends on an unowned logged-in navbar.** `base.html` currently has no session branch, and no earlier step adds one (see the Step 03 and 04 reviews).
8. **Test isolation and login helper are not specified**, same as the Step 05 review: tests need a temporary database and a way to set `session["user_id"]`.

### Low

9. **No CSRF protection.** The POST form has no token. Acceptable for this project stage, but worth recording as an accepted risk.
10. **Test gaps.** No unit test for a user_id that does not exist (foreign key failure), no route test that the saved row belongs to the session user and not a posted `user_id`, and no test for a description over 200 characters.
11. **Re-render details.** The spec does not say the selected category must be re-selected after an error, only that values are "pre-filled".
12. **Default date.** "Defaults to today's date" does not say whether the server or the browser supplies it.
13. **Currency display.** The amount field has no ₹ label, although the ₹ rule is listed.

## 5. Repo state

- `/expenses/add` in `app.py` is still the placeholder stub with a single GET handler.
- `database/queries.py`, `templates/add_expense.html` and `tests/` do not exist.
- `templates/base.html` has no session-based navbar branch.
- The step has therefore not been built, although the later prompts describe it as complete.

## 6. Recommended actions

- [ ] Require saving a re-formatted ISO date string, not the raw input — finding 1
- [ ] Reject non-finite amounts, set a maximum, and round to 2 decimals — finding 2
- [ ] Say how errors reach the template and what the test should look for — finding 3
- [ ] Enforce the 200-character description limit on the server — finding 4
- [ ] Soften the "appears in the transaction list" check or require the row to be within the current view — finding 5
- [ ] State the return value, commit and close behaviour of `insert_expense` — finding 6
- [ ] Assign the logged-in navbar to a step — finding 7
- [ ] Specify the temporary-database and session-login approach for tests — finding 8
- [ ] Add tests for foreign key failure, ownership, and long descriptions — finding 10
- [ ] Confirm Steps 01–06 and this step are really implemented before relying on "complete" statuses — section 5
