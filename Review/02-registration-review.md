# Review Report — 02-registration.md vs Spec_02_Registration.prompt.md

- **Spec reviewed:** `.claude/specs/02-registration.md`
- **Source prompt:** `Spec_02_Registration.prompt.md`
- **Related files checked:** `templates/register.html`, `templates/base.html`, `app.py`, `database/db.py`
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 10 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line. No requirement is missing or contradicted. The findings below are gaps the prompt itself leaves open or conflicts with the current repo.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only; backticks used on identifiers only) |
| Bullet lists throughout, no tables | Pass |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/02-registration.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass | All 4 points present |
| Depends on | Pass | Step 01 only |
| Routes | Pass | GET and POST /register, both public |
| Database changes | Pass | `create_user` with all 4 behaviours, including `IntegrityError` |
| Templates | Pass | All 4 template changes |
| Files to change | Pass | `app.py`, `database/db.py`, `register.html` |
| Files to create | Pass | None |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 11 rules; validation order kept as 1-2-3 |
| Definition of done | Pass | All 7 items, same wording |

## 3. Additions beyond the prompt

- Title line `# Spec 02 — User Registration`.
- Backticks around routes, field names and functions.
- The three validation steps are written as a nested list that keeps the numbering "1. 2. 3." inside bullets.

None contradict the prompt.

## 4. Findings

### High

1. **The template has no `confirm_password` input.** The Templates section says to add `name` attributes to all four inputs, but `templates/register.html` only has name, email and password (zero matches for `confirm_password`). The spec inherits this: the prompt asks only for `name` attributes, so the field itself is never added, and the "passwords do not match" check cannot work. Add a line to the Templates section requiring a Confirm password input.

### Medium

2. **Flash display is not wired in the template.** The current template shows an `error` variable, not flashed messages. The spec says to add a flash block but does not say to remove the old `error` block, so two mechanisms could exist. The success flash is shown on `/login`; Spec 03 adds the flash block to `login.html`, so this step depends on Step 03 for the message to be visible, which the spec does not state.
3. **Hardcoded path in the current template (resolved by the spec).** `register.html` currently uses `action="/register"`; the spec correctly replaces it with `url_for('register')`. `base.html` already uses `url_for()` for every link, so no other change is needed. Not a spec defect.
4. **`abort(405)` rule is redundant.** Flask already returns 405 for methods not declared on the route. The spec requires `abort(405)` without saying which methods the route declares.
5. **Validation is incomplete for real use.** Nothing covers whitespace-only values, email format, case or surrounding whitespace in email (`A@x.com` vs `a@x.com`), or a minimum password length, although the template placeholder says "Min. 8 characters".

### Low

6. **Dev secret key is hardcoded.** The prompt allows it "for now"; the spec carries it with no note to replace it later.
7. **No flash categories.** Error and success messages cannot be styled differently without categories.

A previously listed finding about a "race on duplicate email" was withdrawn: the spec correctly relies on catching `IntegrityError` and does not require a separate pre-check query.

## 5. Repo state

- `app.py` still has `/register` as a plain stub: no `secret_key`, no `flash`, `redirect`, `url_for` or `abort` imports, and no `create_user`. The prompt's structure claims `get_db()`, `init_db()` and `seed_db()` are implemented, but `database/db.py` is still a 5-line comment stub.
- The step has therefore not been built, and its dependency on Step 01 is unmet in this working tree.

## 6. Recommended actions

- [x] Require a Confirm password input in the Templates section — finding 1 (done in `02-registration.md`)
- [x] State that the old `error` block is replaced by the flash block — finding 2 (done in `02-registration.md`); success flash visibility on `/login` relies on Step 03
- [ ] State the methods declared on the route so `abort(405)` has a defined role — finding 4
- [ ] Decide on whitespace, email normalisation and minimum password length rules — finding 5
- [ ] Add flash categories (error/success) — finding 7
- [ ] Confirm Step 01 is actually implemented in `database/db.py` before building this step — section 5
