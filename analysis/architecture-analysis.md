# MIS — Architecture Analysis

**Phase 1 · Codebase Analysis**

---

## System Architecture Pattern

**Monolithic Flask app with blueprint-based role separation.**

The app uses a single PostgreSQL database accessed through a single
monolithic query file (`db.py`). Routes are split by role into four
Flask blueprints. Templates are server-rendered Jinja2 HTML with
Bootstrap 5 for styling.

```
Browser
  └─ Flask App (app.py — factory)
       ├─ auth blueprint      → /login, /logout, /dashboard
       ├─ admin blueprint     → /admin/*
       ├─ teacher blueprint   → /teacher/*
       └─ student blueprint   → /student/*
            └─ All blueprints call db.py functions
                  └─ psycopg3 connection pool → PostgreSQL
```

---

## Authentication & Authorization Flow

1. User POSTs email + password to `/login`
2. `db.get_user_by_email()` fetches user row
3. Werkzeug `check_password_hash` verifies — OR plain-text fallback (`plain_password` column)
4. Role + major info stored in **Flask session** (cookie-based)
5. Every protected route uses a decorator: `@login_required`, `@admin_required`, `@teacher_required`
6. Superadmin is identified by `major_id = None` — not a separate role field

**Major detection logic (login):**
Email format `name.XXXXXX@epu.edu.iq` → 6-digit code → lookup in `majors` table.
Superadmin email `admin@epu.edu.iq` has no dot → `major_id = None`.

---

## i18n (Multilingual) Architecture

- Custom `i18n.py` with dictionaries for **English, Kurdish (Sorani), Arabic**
- RTL layout support via `is_rtl(lang)` → injected into every template
- Language stored per-session (`session['lang']`)
- Switched via `/set-language/<lang>` route
- JSON API responses are auto-translated via `after_request` hook in `app.py`
- Template translations via `{{ t('text') }}` filter

---

## File Upload Architecture

- Files stored on **local disk** in `/uploads/` directory
- Allowed types: pdf, doc, docx, ppt, pptx, xls, xlsx, txt, zip, rar, jpg, jpeg, png, gif
- Max size: **50 MB** per file
- No cloud storage — local only

---

## Performance Features

- **Gzip compression**: `after_request` hook compresses text/HTML/JSON responses >1.4 KB
- **Connection pooling**: `psycopg_pool` for PostgreSQL connections
- **Performance indexes**: Defined in `database/add_performance_indexes.sql`

---

## Identified Architecture Issues

### 🔴 Critical

| Issue | Location | Detail |
|---|---|---|
| Plain-text password fallback | `auth.py` login + `add_plain_password.sql` | `plain_password` column stores raw passwords alongside hashes |
| Hardcoded default credentials | `app.py` `init_admin()` | `admin123` in source code, also in README |
| Weak secret key fallback | `config.py` | Falls back to `'mis-system-secret-key-change-in-production'` if env not set |

### 🟡 Design Concerns

| Issue | Location | Detail |
|---|---|---|
| Monolithic `db.py` (107 KB) | `db.py` | All SQL in one file — hard to maintain as system grows |
| Monolithic `admin.py` (79 KB) | `blueprints/admin.py` | Single blueprint file for all admin routes |
| No CSRF protection | All POST routes | No Flask-WTF or CSRF token visible in requirements |
| Local file storage | `/uploads/` | Not suitable for multi-server deployment |
| Schema via patches | `database/*.sql` (18 files) | No migration tool (Alembic/Flyway) — manual SQL patches |
| Redis in requirements but unused | `requirements.txt` | `redis>=5.0.0` listed but no Redis usage found in app.py |

### 🟢 Good Practices Found

- Blueprint-based role separation ✅
- Environment variable configuration via `.env` ✅
- Werkzeug password hashing ✅
- psycopg3 connection pooling ✅
- Gzip compression ✅
- RTL/i18n support ✅
- Role-based decorators cleanly defined ✅

---

*Next: Phase 2 — deep dive into blueprints and db.py patterns.*
