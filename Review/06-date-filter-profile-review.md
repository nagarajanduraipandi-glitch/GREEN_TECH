# Review Report — 06-date-filter-profile.md vs Spec_06-date-filter-profile_prompt.md

- **Spec reviewed:** `.claude/specs/06-date-filter-profile.md`
- **Source prompt:** `Spec_06-date-filter-profile_prompt.md`
- **Related files checked:** `templates/` (flash usage), `static/css/` listing, `app.py`, Specs 04 and 05 for cross-step consistency
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 10 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line. No requirement is missing or contradicted. The findings below are gaps the prompt leaves open, mainly the missing tests section, flash display, and the definition of the date windows.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only) |
| Bullet lists throughout | Pass |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/06-date-filter-profile.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass | All 4 points |
| Depends on | Pass | Steps 01, 04, 05 with the stated reasons |
| Routes | Pass | No new routes; `date_from` / `date_to` described; fallback rule kept |
| Database changes | Pass | None; BETWEEN note kept |
| Templates | Pass | Filter bar with presets, custom form, active state |
| Files to change | Pass | `app.py` (6 points), `queries.py` (3 helpers), `profile.html`, `profile.css` |
| Files to create | Pass | None |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 12 rules |
| Definition of done | Pass | All 11 items, same wording |

## 3. Additions beyond the prompt

- Title line `# Spec 06 — Date Filter for Profile Page`.

It does not contradict the prompt.

## 4. Findings

### High

1. **No "Tests to write" section.** Steps 05, 07, 08 and 09 each define tests, but this step does not, and the prompt does not ask for one. The filter has the most edge cases in the project (reversed range, malformed dates, one-sided range, empty range), so the Definition of Done cannot be checked automatically. This is a prompt-level gap that the spec inherits.
2. **Flashed messages are not displayed anywhere.** The spec requires flashing "Start date must be before end date.", but no template contains `get_flashed_messages` (checked in all six existing templates, including `base.html`). Unless Step 02 or 03 adds a flash block to `base.html` or `profile.html`, the message never appears. Add a flash block to Files to change.

### Medium

3. **The date windows are undefined.** "Last 3 Months" and "Last 6 Months" are described as windows "ending today", but the spec does not say whether that means 90 and 180 days, or calendar months back (for example 15 Jul to today). `datetime` has no month arithmetic of its own (it needs the `calendar` module or a third-party library), and no new dependency is allowed, so the choice affects the implementation.
4. **"This Month" upper bound is undefined.** It could end on today or on the last day of the month. Future-dated expenses behave differently under each.
5. **Custom range form method is not stated.** The sub-form must use GET so the dates arrive in `request.args`. The spec says only "sub-form", and a POST form would never reach the filter. State `method="get"` and the target via `url_for("profile")`.
6. **One-sided ranges are silently ignored.** The Routes section says that if either date is absent or malformed the route falls back to All Time, so supplying only `date_from` shows everything. This is consistent with the prompt, but it is poor behaviour for a user who fills in one box. Record it as an accepted limitation or define open-ended ranges.
7. **Active-state rules are ambiguous.** If a custom range happens to equal a preset's dates, both the preset and the custom fields could be highlighted. The spec does not say which wins.
8. **Dynamic SQL risk.** Adding "AND date BETWEEN ? AND ?" only when both dates are present means building the query conditionally. The "never string-format" rule still applies; the spec should say the conditional fragment must be a fixed string, with only the bound values passed as parameters.

### Low

9. **Flash wording versus behaviour.** The message says "must be before", but the rule only rejects `date_from > date_to`, so equal dates are accepted. Fine, but the wording is slightly misleading.
10. **Filter is lost after other actions.** Steps 07–09 redirect to a plain `/profile`, so an active filter is dropped after adding, editing or deleting an expense. Not covered by any step.
11. **`limit=10` interacts with the filter.** The transaction table is capped at 10 rows, while the count in the stats covers the whole range; the page can show 10 rows against a larger count.
12. **Depends on omits Step 03.** Flash and session handling come from Steps 02–03, which are not listed.

## 5. Repo state

- `/profile` in `app.py` is still the stub string; no `date_from` / `date_to` handling and no `datetime` import.
- `database/queries.py`, `templates/profile.html` and `static/css/profile.css` do not exist; `static/css/` holds only `landing.css` and `style.css`.
- No template contains a flash block.
- The step has therefore not been built, and its Step 05 dependency is unmet in this working tree.

## 6. Correction to an earlier statement

- In an earlier chat summary of this spec I said it did not define what happens when only one of the two dates is valid. That was wrong: the Routes section says that if either parameter is absent or malformed the route falls back to the unfiltered view. Finding 6 above is the accurate version.

## 7. Recommended actions

- [ ] Add a "Tests to write" section covering reversed, malformed, one-sided and empty ranges — finding 1
- [x] Add a flash display block — finding 2 (done in the Templates section of `06-date-filter-profile.md`)
- [x] Define the "Last 3 Months", "Last 6 Months" and "This Month" windows exactly — findings 3 and 4 (done: calendar months via the standard library; This Month ends today)
- [x] State that the custom range form uses GET via `url_for("profile")` — finding 5 (done)
- [ ] Decide whether one-sided ranges are accepted or supported — finding 6
- [ ] Specify which control is highlighted when a custom range equals a preset — finding 7
- [x] State that the conditional SQL fragment must be fixed text with bound parameters — finding 8 (done)
- [x] Add Step 03 to Depends on — finding 12 (done)
- [ ] Confirm Steps 01–05 and this step are really implemented before relying on "complete" statuses — section 5
