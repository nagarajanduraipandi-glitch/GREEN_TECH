# Review Report — 03-login_logout.md vs Spec_03_login_logout_prompt.md

- **Spec reviewed:** `.claude/specs/03-login_logout.md`
- **Source prompt:** `Spec_03_login_logout_prompt.md`
- **Related files checked:** `templates/login.html`, `templates/base.html`, `app.py`, `Spec 04` and `Spec 07` for cross-step consistency
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 10 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line. No requirement is missing or contradicted. The findings below are gaps the prompt leaves open, mainly around the navbar and later steps that rely on this one.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only; backticks on identifiers only) |
| Bullet lists throughout | Pass |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/03-login_logout.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass | All 4 points, including the three sub-bullets |
| Depends on | Pass | Steps 01 and 02 |
| Routes | Pass | GET and POST /login, GET /logout, all public |
| Database changes | Pass | `get_user_by_email` with all 3 behaviours, kept in `database/db.py` |
| Templates | Pass | All 4 template changes |
| Files to change | Pass | `app.py`, `database/db.py`, `login.html` |
| Files to create | Pass | None |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 11 rules, including the exact error string |
| Definition of done | Pass | All 7 items, same wording |

## 3. Additions beyond the prompt

- Title line `# Spec 03 — Login and Logout`.
- Backticks around routes, field names and functions.

Neither contradicts the prompt.

## 4. Findings

### High

1. **No navbar change for logged-in state, but later steps require it.** Spec 04's Definition of Done says "The navbar shows the logged-in state (username + logout link)". `templates/base.html` currently shows only "Sign in" and "Get started", and no spec in 01–09 assigns the navbar change. Spec 03 is the natural owner: it is the step that creates the session. Add `base.html` to Files to change, with a logged-in branch that shows the user and a logout link.

### Medium

2. **Redirect target conflicts with later steps.** Spec 03 sends a successful login to the landing page "until a dashboard exists". Spec 04 adds `/profile` but never says to change the login redirect, so users still land on `/`. Decide whether Step 04 or a later step updates it.
3. **Existing `login.html` already has a form.** The prompt calls it a stub with no form action, but the file already has a `POST` form pointing at a hardcoded `/login`, an `error` variable block instead of flashed messages, and a register link already generated with `url_for`. The spec said to "add" each of these, which would create duplicates. *Resolved:* the Templates section of `03-login_logout.md` now says to update the existing form, replace the hardcoded action and the `error` block, and keep the register link.
4. **`secret_key` is not mentioned.** Sessions need `app.secret_key`. Spec 02 sets it, but Spec 03 did not list it as a dependency, and `app.py` has none today. *Resolved:* the Depends on section now notes it.
5. **Logout uses GET.** `GET /logout` changes state, so any page or image can log a user out. The prompt requires GET, so the spec cannot change this, but it should be recorded as an accepted risk.

### Low

6. **No check for an already logged-in user.** Visiting `/login` while logged in just shows the form again; the spec does not say whether to redirect.
7. **Email handling unspecified.** No trimming or lowercasing of the submitted email before lookup, which can cause failed logins for emails registered in different case.
8. **No session lifetime or `session.permanent` guidance.** The default browser-session cookie applies.
9. **No flash for logout.** The user gets no confirmation after logging out.
10. **Definition of done does not cover empty fields or the `get_user_by_email` return value** (`None` for unknown email).

## 5. Repo state

- `app.py` still has `/login` and `/logout` as stubs (`login()` just renders the template, with no `session`, no POST handling and no `secret_key`).
- `database/db.py` is still a 5-line comment stub, so `get_user_by_email` and `create_user` do not exist, although the prompt describes Steps 01 and 02 as complete.
- This step has therefore not been built, and its dependencies are unmet in this working tree.

## 6. Recommended actions

- [ ] Add `base.html` to Files to change, with a logged-in navbar (username + logout link) — finding 1
- [ ] State which step moves the post-login redirect to `/profile` — finding 2
- [x] Say to modify the existing `login.html` form and replace the `error` block with flashed messages — finding 3 (done in `03-login_logout.md`)
- [x] List `app.secret_key` as a dependency on Step 02 — finding 4 (done in `03-login_logout.md`)
- [ ] Record the GET-logout risk as accepted — finding 5
- [ ] Decide email normalisation and logged-in `/login` behaviour — findings 6 and 7
- [ ] Confirm Steps 01 and 02 are really implemented before building this step — section 5
