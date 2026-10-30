# Review Report — 04-profile.md vs Spec_04_Profilepage_prompt.md

- **Spec reviewed:** `.claude/specs/04-profile.md`
- **Source prompt:** `Spec_04_Profilepage_prompt.md`
- **Related files checked:** `app.py`, `templates/` and `static/css/` listings, `templates/base.html`, Specs 05 and 07 for cross-step consistency
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 10 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line. No requirement is missing or contradicted. The findings below are gaps the prompt leaves open, mainly styling, the navbar, and currency.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only) |
| Bullet lists throughout | Pass |
| Numbered list for the four template sections | Pass (items 1–4 under Templates) |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/04-profile.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass | All 4 points |
| Depends on | Pass | Steps 01, 02, 03 with the stated reasons |
| Routes | Pass | GET /profile, logged-in only, redirect to /login |
| Database changes | Pass | None; no queries |
| Templates | Pass | `profile.html` plus the four numbered sections with their fields and minimum row/category counts |
| Files to change | Pass | `app.py` with the guard and four context variables |
| Files to create | Pass | `templates/profile.html` only |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 9 rules |
| Definition of done | Pass | All 8 items, same wording |

## 3. Additions beyond the prompt

- Title line `# Spec 04 — Profile Page (Hardcoded UI Data)`.

It does not contradict the prompt.

## 4. Findings

### High

1. **No file is assigned for the page's styles.** The spec requires CSS variables, no inline styles, and CSS-class category badges, but Files to create lists only `templates/profile.html`. The only stylesheets in `static/css/` are `landing.css` and `style.css`. Spec 06's structure later shows `static/css/profile.css` as already existing, and no step before it creates it, so Step 04 must be the step that does. *Resolved:* `static/css/profile.css` is now in Files to create in `04-profile.md`, loaded from `profile.html` via `url_for`.
2. **The logged-in navbar has no owner.** The Definition of Done requires the navbar to show "username + logout link", but Files to change lists only `app.py`. `templates/base.html` currently shows only "Sign in" and "Get started", with no session check. The same gap exists in Spec 03. Either add `base.html` to this step or assign it to Step 03.

### Medium

3. **No currency rule.** The page shows amounts, but the spec does not say how. Spec 05 later requires the ₹ symbol (and says to "confirm" it is already used), so a Step 04 template built with `$` or no symbol would need rework. *Resolved:* the ₹ rule is now in Rules for implementation in `04-profile.md`.
4. **Hardcoded data is not tied to the seed data.** Spec 05 expects "Demo User", demo@spendly.com, a 346.24 total, 8 transactions and 7 categories. If the Step 04 placeholders differ, Step 05 changes the visible page for no design reason. Say that the hardcoded values should mirror the seed data.
5. **Avatar initials source is not stated.** Initials could be hardcoded or derived from the name; "all hardcoded values" suggests hardcoded, but this is not explicit.
6. **Category badge classes are not named.** The rule says "use a CSS class", but not whether there is one class per category or one shared class, nor where they are defined.
7. **Navbar username source.** The page needs the username for the navbar, but only a `user` dict for the profile is passed to the template. The spec does not say which variable `base.html` reads.

### Low

8. **Empty-state is not covered.** No behaviour is described for empty transaction or category lists, which Step 05 needs for new users.
9. **"At least 3 rows" is a minimum with no maximum.** Fine for a placeholder, but Spec 05's 8-row expectation suggests 8.
10. **Member-since format is not specified.** Spec 05 requires "Month YYYY".

## 5. Repo state

- `/profile` in `app.py` is still the stub returning "Profile page — coming in Step 4": no session guard, no context data.
- `templates/profile.html` does not exist, and `static/css/` has no `profile.css`.
- The step has therefore not been built, although later prompts describe it as complete.

## 6. Recommended actions

- [x] Add `static/css/profile.css` to Files to create and say how it is loaded — finding 1 (done in `04-profile.md`)
- [ ] Assign the logged-in navbar change to a file (`base.html`) and name the variable it reads — findings 2 and 7
- [x] State the ₹ currency rule — finding 3 (done in `04-profile.md`)
- [x] Say hardcoded values should mirror the Step 01 seed data — finding 4 (done in `04-profile.md`)
- [x] Specify the member-since format — finding 10 (done in `04-profile.md`)
- [ ] Specify the badge class naming — finding 6 (open: one shared class vs one class per category)
- [ ] Confirm Steps 01–03 and this step are really implemented before relying on "complete" statuses — section 5
