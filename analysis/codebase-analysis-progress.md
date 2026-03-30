# MIS — Codebase Analysis Progress

## Status: COMPLETE (All 3 Phases Done)

---

## Files Generated

  MIS/analysis/
  ├── project-overview.md          Phase 1 — tech stack, file map, DB tables
  ├── architecture-analysis.md     Phase 1 — system flow, auth, i18n, Redis
  ├── component-deep-dive.md       Phase 2 — blueprint internals, db.py patterns
  └── technical-recommendations.md Phase 3 — prioritized fix list with code examples

---

## Summary of Findings

### Critical (fix before any deployment)
1. plain_password column — raw passwords stored in DB and accepted at login
2. SECRET_KEY fallback — weak literal key in source code, can forge sessions
3. No CSRF tokens — all POST forms are vulnerable to cross-site request forgery
4. Hardcoded admin123 — default credentials in source code and README

### High
5. No login rate limiting — brute-force attack is possible

### Medium
6. N+1 query in attendance_records (51 queries for 50 submissions)
7. Inline SQL in admin.py routes (bypasses db.py layer)

### Low / Architecture
8. Missing @student_required decorator
9. Class name string parsing in teacher.py (fragile)
10. Hardcoded Windows PostgreSQL path in db.py
11. admin.py (79 KB) handles too many responsibilities
12. No DB migration tooling (18 manual SQL patches)
13. Local file storage in /uploads/

---

## How to Continue Analysis

To analyze specific areas in a new chat:
"Continue MIS codebase analysis — read MIS/analysis/codebase-analysis-progress.md
then deep-dive into [topic e.g. i18n system / grade calculation logic / template security]"
