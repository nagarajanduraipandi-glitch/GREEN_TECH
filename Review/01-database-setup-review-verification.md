# Verification Report — 01-database-setup-review.md

- **Document verified:** `.claude/specs/01-database-setup-review.md`
- **Checked against:** `Spec_01_database_setup_prompt.md`, `.claude/specs/01-database-setup.md`, and the repository
- **Date:** 2026-10-30

## Verdict

The review is mostly accurate. Its compliance table and its two High findings hold up. One cross-document claim cannot be supported, and one "files checked" statement overstates what was possible.

## 1. Claims confirmed

| Review claim | Evidence | Result |
|--------------|----------|--------|
| Spec has all 14 sections, in order, with the prompt's names | Compared headings in `01-database-setup.md` to the prompt | Confirmed |
| Schema is in tables; Definition of Done is a checkbox list | Spec sections 4 and 14 | Confirmed |
| Definition of Done items are verbatim (8 of 8) | Compared against prompt lines 103–110 | Confirmed |
| Extra content is limited to a title line and inline code formatting | Spec lines 1 and throughout | Confirmed |
| Finding 1: `.gitignore` lists `expense_tracker.db`, not `spendly.db` | `.gitignore` line 1 | Confirmed |
| Finding 1: prompt sections 7 and 8 limit changes to `db.py` and `app.py`, so the spec cannot fix it | Prompt lines 69–73 | Confirmed |
| Finding 2: seed data is not pinned in Spec 01 | Spec section 5 says only "8 sample expenses ... 7 categories" | Confirmed |
| Finding 2: Spec 05 expects 346.24 total, 8 transactions, top category Bills | Spec 05 route tests and Definition of Done | Confirmed |
| Finding 7: "spread across the current month" makes seed dates vary | Prompt line 62 | Confirmed; comes from the prompt itself |

## 2. Claims not supported

| Review claim | Evidence | Result |
|--------------|----------|--------|
| Section 5: `claude/spec/spec.md` uses `expense_tracker.db`, CHECK constraints, an index and a teardown function | `claude/spec/` exists but is empty; no `spec.md` exists anywhere in the repo | Not supported. The file is missing or the source was wrong |
| Header: related files checked include `database/db.py` | `database/db.py` is a 5-line stub of comments, with no functions and no `spendly.db` reference | Overstated. Nothing in `db.py` could be checked beyond its being a stub |

## 3. Additional observation

- `database/db.py` is still the unimplemented stub, although later prompts describe Steps 01–09 as complete.
- Either the implementation lives elsewhere or the code is behind the specs.
- Until this is resolved, no "complete" status in the spec set can be trusted.

## 4. Review findings still valid

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | `spendly.db` not git-ignored; spec forbids the fix | High | Confirmed |
| 2 | Seed data not pinned; Spec 05 depends on it | High | Confirmed |
| 3 | No enforcement mechanism for categories | Medium | Valid (spec gap) |
| 4 | Database path not anchored to project root | Medium | Valid (spec gap) |
| 5 | Connection commit/close ownership undefined | Medium | Valid (spec gap) |
| 6 | `created_at` format unspecified | Low | Valid (spec gap) |
| 7 | Seed dates vary by month | Low | Confirmed; inherited from prompt |
| 8 | No `ON DELETE` behaviour for `expenses.user_id` | Low | Valid (spec gap) |
| 9 | Email uniqueness is case-sensitive | Low | Valid (spec gap) |
| 10 | `get_db` imported into `app.py` but unused | Low | Valid, harmless |

## 5. Recommended actions

- [x] Add `spendly.db` to `.gitignore` (finding 1) — done
- [x] State the Spec 05 totals as seed requirements (finding 2) — done in `01-database-setup.md` section 5 (sum 346.24, Bills highest)
- [x] Remove the `claude/spec/spec.md` comparison in the review — done (withdrawn in `01-database-setup-review.md` section 5)
- [x] Correct the review's "Related files checked" line to reflect that `db.py` is a stub — done
- [x] Verify the real state of `database/db.py` and `app.py` — done: `db.py` is a stub and `app.py` has no DB wiring; Steps 01–09 are not built in this working tree
- [ ] Address findings 3–6 in the spec, or record them as accepted gaps — left open; these are design decisions (category CHECK vs app validation, DB path anchoring, connection ownership, `created_at` format)
