# Review Report — 01-database-setup.md vs Spec_01_database_setup_prompt.md

- **Spec reviewed:** `.claude/specs/01-database-setup.md`
- **Source prompt:** `Spec_01_database_setup_prompt.md`
- **Related files checked:** `.gitignore`, `app.py`, `Spec_05`–`Spec_09` prompts; `database/db.py` is still a 5-line comment stub, so no implementation was available to check

## Verdict

The spec **fully complies** with the prompt: all 14 sections, in order, correct format rules. No requirement is missing or contradicted. The findings below are gaps the prompt itself leaves open, which will cause problems in later steps.

## 1. Format rules

| Rule | Result |
|------|--------|
| Output only the Markdown spec | Pass |
| No code, no prose outside the spec sections | Pass (one title line only) |
| Tables for schema definitions | Pass |
| Checkbox list for Definition of Done | Pass |
| Sections numbered exactly as listed | Pass (1–14, same names) |
| Saved at `.claude/specs/01-database-setup.md` | Pass |

## 2. Section-by-section compliance

| # | Section | Result | Notes |
|---|---------|--------|-------|
| 1 | Overview | Pass | States purpose, foundational role; names auth, profile, expense tracking |
| 2 | Depends on | Pass | "None, first step" |
| 3 | Routes | Pass | No new routes; placeholders unchanged |
| 4 | Database Schema | Pass | Both tables, all columns in the requested order, type + constraints per column, `date` notes `YYYY-MM-DD` |
| 5 | Functions | Pass | `get_db`, `init_db`, `seed_db` behaviour matches the prompt (spendly.db, Row factory, FK pragma, idempotent seed, demo user, 8 expenses, 7 categories) |
| 6 | Changes to app.py | Pass | Import, `app.app_context()` startup calls, DB ready before routes |
| 7 | Files to Change | Pass | `database/db.py`, `app.py` only |
| 8 | Files to Create | Pass | None |
| 9 | Dependencies | Pass | No new packages; sqlite3 + werkzeug.security |
| 10 | Categories | Pass | All 7 as a bullet list |
| 11 | Rules | Pass | All 7 rules present |
| 12 | Expected Behavior | Pass | Covers all three functions and DB constraints |
| 13 | Error Handling | Pass | All 3 cases |
| 14 | Definition of Done | Pass | All 8 items, verbatim |

## 3. Additions beyond the prompt

- `description` marked nullable (prompt gave no constraint).
- Section 12 adds: rows accessible by column name, `created_at` auto-filled.
- Section 13 names `sqlite3.IntegrityError` for both constraint failures.
- Section 4 notes category must be one of the fixed list.

All are reasonable and consistent with the prompt; none contradict it.

## 4. Findings

### High

1. **`spendly.db` is not git-ignored, and the spec forbids the fix.** `.gitignore` lists `expense_tracker.db`. Sections 7 and 8 restrict changes to `db.py` and `app.py`, so the database file (containing the demo password hash) could be committed. The prompt creates this conflict, and the spec inherits it.
2. **Seed data is not pinned, but Spec 05 depends on it.** Spec 05 expects total 346.24, 8 transactions, top category Bills, all 7 categories. Spec 01 only says "8 expenses across 7 categories", so a valid implementation can fail Spec 05's tests.

### Medium

3. **No enforcement mechanism for categories.** Section 10 says these are the only valid values, but sections 12–13 do not say whether an SQL `CHECK` or app-level validation enforces it.
4. **Database path is ambiguous.** "`spendly.db` in project root" is not anchored; a relative path creates a second database if the app starts from another working directory.
5. **Connection lifecycle undefined.** Nothing says who commits or closes connections. Specs 05–09 have helpers closing their own connections, so this should be stated.

### Low

6. **Timestamp format unspecified.** `created_at` default is "current timestamp"; Spec 05 formats it as "Month YYYY", so the stored format should be named.
7. **Seed dates vary by month.** "Spread across the current month" makes data non-deterministic, which may complicate Spec 06 date-filter tests.
8. **No `ON DELETE` behaviour** stated for `expenses.user_id`.
9. **Email case-sensitivity:** `UNIQUE` is case-sensitive; `A@x.com` and `a@x.com` would be distinct users.
10. **`get_db` imported into `app.py` but unused** in this step; harmless but unexplained.

## 5. Cross-document consistency

- An earlier spec at `claude/spec/spec.md` was previously cited here. That file does not exist (`claude/spec/` is empty), so the comparison is withdrawn.
- The only remaining trace of an older database name is `expense_tracker.db` in `.gitignore`; `spendly.db` has now been added next to it.

## 6. Recommended actions

- [x] Add `spendly.db` to `.gitignore` — finding 1 (done)
- [ ] Pin seed amounts or state the Spec 05 totals as requirements — finding 2
- [ ] State how category validity is enforced — finding 3
- [ ] Anchor the DB path to the project root — finding 4
- [ ] Define connection ownership (commit/close) — finding 5
- [ ] Name the `created_at` format — finding 6
- [x] `claude/spec/spec.md` comparison withdrawn — section 5 (file does not exist)
