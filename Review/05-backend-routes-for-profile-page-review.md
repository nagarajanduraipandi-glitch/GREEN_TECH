# Review Report — 05-backend-routes-for-profile-page.md vs Spec_05-backend-routes-for-profile-page_prompt.md

- **Spec reviewed:** `.claude/specs/05-backend-routes-for-profile-page.md`
- **Source prompt:** `Spec_05-backend-routes-for-profile-page_prompt.md`
- **Related files checked:** `database/` and `tests/` listings, `app.py`, Specs 01, 06 and 08 for cross-step consistency
- **Date:** 2026-10-30

## Verdict

The spec complies with the prompt. All 11 sections are present, in order, with the exact names and no numbering, and the content matches the prompt line for line, including the test table and the ₹ rule. No requirement is missing or contradicted. The findings below are gaps the prompt leaves open, mostly around test setup, seed data, and number and date handling.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only) |
| Bullet lists throughout | Pass |
| Table for the unit test cases | Pass (Function / Input / Expected output, 8 rows) |
| Checkbox list for Definition of Done | Pass |
| Section names exact, no numbers | Pass |
| Saved at `.claude/specs/05-backend-routes-for-profile-page.md` | Pass |

## 2. Section-by-section compliance

| Section | Result | Notes |
|---------|--------|-------|
| Overview | Pass | All 4 points, including the subagent statement |
| Depends on | Pass | Steps 01–04 with the stated reasons |
| Routes | Pass | No new routes; /profile modified in place |
| Database changes | Pass | None; column list as given |
| Templates | Pass | ₹ rule and "no structural changes" |
| Files to change | Pass | `app.py`, `profile.html` |
| Files to create | Pass | `database/queries.py` with the four helpers and their return shapes |
| New dependencies | Pass | None |
| Rules for implementation | Pass | All 11 rules |
| Tests to write | Pass | 8 unit rows; route tests incl. all 9 seed-user assertions |
| Definition of done | Pass | All 8 items, same wording |

## 3. Additions beyond the prompt

- Title line `# Spec 05 — Backend Routes for Profile Page`.
- The unit test inputs are shortened ("Valid user_id" for "get_user_by_id with valid user_id"); the meaning is unchanged.

Neither contradicts the prompt.

## 4. Findings

### High

1. **Test isolation is not specified.** `get_db()` opens `spendly.db` in the project root (Spec 01). The spec's tests need a seeded user, a user with no expenses, and another user, but it does not say how tests get a separate database. As written they would run against, and possibly modify, the real `spendly.db`. State that tests use a temporary database. *Resolved:* the Tests section of `05-backend-routes-for-profile-page.md` now says so.
2. **Seed values are not guaranteed.** The route tests and Definition of Done require total 346.24, 8 transactions, top category Bills, and 7 categories. Spec 01 does not pin the seed amounts, so a valid Step 01 implementation can fail this step. Pin the seed in Spec 01 or restate it here as a requirement on the seed data.

### Medium

3. **`member_since` cannot be tested with a fixed value.** It comes from `users.created_at`, which Spec 01 sets with a current-timestamp default. The seeded demo user is therefore created at the moment of seeding, so the expected month changes. The spec's "correct member_since" assertion has no stable expected value.
4. **Float rounding of money.** Seed amounts are REAL, so a sum can come back as 346.2400000001. The spec requires "₹346.24" but does not say to round to two decimals in the helper or in the template.
5. **Empty-case types are inconsistent.** `total_spent` is the integer 0 in the unit test but the page must show "₹0.00". The spec does not say who formats it. `top_category` is "—" for no expenses but the tie rule for equal totals is undefined.
6. **Missing user is unhandled.** `get_user_by_id` returns None for an unknown id, but the route behaviour when the session holds an id that no longer exists is unspecified (the template would fail on None).
7. **"Never raise exceptions" wording (withdrawn as a conflict).** The rule applies to a user who has no expenses, which `get_user_by_id` handles normally; its None result is for a user id that does not exist. There is no contradiction, but the missing-user case is still open under finding 6.
8. **Order ties.** "Newest-first" has no tiebreaker for expenses on the same date, which can make the transaction-order test flaky.

### Low

9. **Subagent wording.** "Three parallel subagents" is a process note rather than a requirement, and there are four helpers, not three concerns. It is not verifiable from the Definition of Done.
10. **Limit versus counts.** `get_recent_transactions` defaults to `limit=10`, while "Transaction count" counts every expense. For users with more than 10 expenses the table and the count differ; the spec does not say that is intended.
11. **No `id` in transactions.** The fields list omits `id`, which Spec 08 later adds. Harmless, but it forces a change to an existing helper.
12. **Route tests need a login helper.** The spec does not say how an authenticated session is established in tests (for example setting the session directly vs posting to /login).

## 5. Repo state

- `database/queries.py` does not exist; `database/` holds only `__init__.py` and `db.py`.
- `tests/` does not exist.
- `/profile` in `app.py` is still the stub string, and `database/db.py` is a 5-line comment stub.
- The step has therefore not been built, although later prompts describe it as complete.

## 6. Recommended actions

- [x] State that tests run against a temporary database, not `spendly.db` — finding 1 (done in `05-backend-routes-for-profile-page.md`)
- [x] Pin the seed amounts in Spec 01 or restate the expected totals as seed requirements — finding 2 (done in `01-database-setup.md`)
- [x] Replace the `member_since` assertion with a format check — finding 3 (done in `05-backend-routes-for-profile-page.md`)
- [x] Specify two-decimal rounding — finding 4 (done); who formats ₹0.00 (finding 5) is still open
- [x] Who formats ₹0.00 — finding 5 (done: template formats, helpers return numbers); tie rule for equal category totals is still open
- [x] Missing user and same-date ordering — findings 6 and 8 (done in `05-backend-routes-for-profile-page.md`); finding 7 withdrawn
- [ ] Reword or drop the subagent line — finding 9
- [ ] Confirm Steps 01–04 and this step are really implemented before relying on "complete" statuses — section 5
