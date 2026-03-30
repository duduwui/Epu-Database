# MIS — Component Deep Dive Analysis

**Phase 2 · Blueprint Internals & Database Layer**

---

## 1. `db.py` — Query Layer Analysis

### Architecture Pattern

All SQL lives in one 107 KB file. There are two tiers of functions:

**Tier 1 — Low-level helpers (used everywhere):**
- `get_db_connection()` — pulls from psycopg3 pool (min 2, max 20 connections)
- `execute_query(query, params, fetch_one, fetch_all)` — the main workhorse
- `execute_insert_returning(query, params)` — INSERT with RETURNING id
- `row_to_dict(cursor, row)` — converts psycopg tuple rows to dicts

**Tier 2 — Domain functions:**
Hundreds of named functions like `get_user_by_email`, `create_student_with_semester`,
`get_grades_by_student`, etc. Each calls the Tier 1 helpers.

### Redis Caching (Optional Layer)

Redis is connected at startup and degrades gracefully if unavailable:
- Cache hit → return JSON-deserialized object
- Cache miss or Redis down → fall through to PostgreSQL
- TTL SHORT: 5 minutes (grade components)
- TTL LONG: 10 minutes (departments, class list)
- Invalidation via `_cache_delete(*keys)` called on mutations

This is well-designed. The fallback means the app runs without Redis
in development with zero code changes.

### Issues Found in db.py

**CRITICAL — plain_password in create_user():**
The function signature and INSERT both include a plain_password parameter.
Raw passwords are written to the database on every user creation.
Any DB dump, backup, or SQL injection exposes all user passwords in plain text.

**CONCERN — Mixed connection management:**
Newer code uses execute_query() (safe, pooled).
Older code (including in admin.py routes) uses raw get_db_connection() + cursor directly.
The admin dashboard route fetches student/subject counts using raw connections,
bypassing the execute_query wrapper and risking un-returned pool connections
if an exception occurs mid-query.

**CONCERN — Hardcoded Windows path:**
  _pg_bin = r"C:\Program Files\PostgreSQL\17\bin"
This silently does nothing on Linux/Mac or non-standard Postgres installs.
It should be removed or guarded with a sys.platform check.

**CONCERN — get_all_users() returns plain_password column:**
The query explicitly selects password_hash and plain_password for every user
and passes them to admin UI templates. Even if not displayed, this increases
the blast radius of any template injection issue.

---

## 2. `blueprints/auth.py` — Authentication Analysis

### Decorator System

Four decorators protect routes:
- @login_required — any logged-in user
- @admin_required — role == 'admin'
- @superadmin_required — role == 'admin' AND major_id IS NULL
- @teacher_required — role in ('admin', 'teacher')

Clean and consistent. All four check session['user_id'] first before role.

### Login Flow Issues

**CRITICAL — Plain-text password fallback active in production:**
The login check accepts either the hashed password OR the plain_password column:
  check_password_hash(user['password_hash'], password)
  OR user['plain_password'] == password
This means a user can log in with their raw password even if the hash doesn't match.
Remove the plain_password fallback entirely.

**CONCERN — Major detection via email parsing on every login:**
Major is inferred by splitting the email local part at the last dot and
looking up the 6-digit code in the majors table. If a match is found,
the major_id is written back to the user row. This means:
- A user whose email format matches a valid major code gets that major assigned
- The write-back (assign_major_to_user) happens on every login until major_id is set
Should be stored permanently at user creation time.

**CONCERN — No brute-force protection:**
No rate limiting, no account lockout, no CAPTCHA on the login endpoint.
An attacker can submit unlimited POST requests with no throttling.

---

## 3. `blueprints/admin.py` — Admin Routes Analysis

### Email Generation System (Well Done)

_generate_epu_email() is well-implemented:
- Builds firstname_lastnameMIS######@epu.edu.iq format
- Checks existing emails to avoid collisions using LIKE + ESCAPE
- Falls back to sequential scan if 100 random attempts all collide
- Handles edge cases (single-word names, non-ASCII characters)

### Inline SQL in Blueprint Routes

The admin dashboard contains raw SQL that belongs in db.py:
  conn = db.get_db_connection()
  cur = conn.cursor()
  cur.execute("SELECT COUNT(*) FROM students s JOIN users u ON ...")
Two separate inline queries fetch total_students and total_subjects.
This SQL is untested, not reusable, and bypasses execute_query.

### N+1 Query Problem in Attendance Records

The attendance_records() route fires one aggregate GROUP BY query,
then loops over each result and fires a per-row detail query:
  for submission in submissions:
      cur.execute("SELECT ... WHERE date=%s AND subject_id=%s", ...)
      submission['students'] = [...]
With 50 submissions, this fires 51 queries. Should be a single JOIN
or a batch fetch grouped by (date, subject_id) in Python.

### File Size / Responsibility Overload

admin.py at 79 KB handles: dashboard stats, user CRUD, student management,
class management, subject management, grade components, attendance records,
attendance summary, enrollment periods, exam periods, departments,
schedule builder AJAX API, and semester upgrade logic.

This is too much for one file. Should be split into service modules
or sub-blueprints (e.g. admin_users, admin_grades, admin_schedule).

---

## 4. `blueprints/teacher.py` — Teacher Routes Analysis

### Authorization Pattern (Good)

Every teacher route correctly verifies subject ownership:
  teacher = db.get_teacher_by_user_id(session['user_id'])
  subjects = db.get_subjects_by_teacher(teacher['id'])
  subject = next((s for s in subjects if s['id'] == subject_id), None)
  if not subject:
      flash('Subject not found or access denied.')
      return redirect(...)

A teacher cannot access another teacher's subject data because subjects
are filtered through their own teacher ID before use.

### Fragile Class Name Parsing

Class info is stored as a single formatted display string, then split back apart:
  parts = class_name.split(' - ')
  year = parts[0].replace('Year ', '') if len(parts) > 0 else '?'
  semester = parts[1].replace('Sem ', '') if len(parts) > 1 else '?'

If the class name format changes or has unexpected separators, this
returns '?' silently. The DB query should return year, semester, section,
and shift as separate columns instead of relying on string parsing.

---

## 5. `blueprints/student.py` — Student Routes Analysis

### Missing Student Decorator (Inconsistent Auth Pattern)

The student blueprint uses @login_required then checks role manually:
  @login_required
  def dashboard():
      if session.get('role') != 'student':
          return redirect(url_for('auth.dashboard'))

Auth.py defines @admin_required and @teacher_required but no @student_required.
A @student_required decorator should be added to auth.py for consistency.

### Dashboard Data Loading (All At Once)

The student dashboard loads grades, homework, weekly topics, schedule,
and attendance in a single request. For students with long academic history
(2+ years of records), this will be slow. Attendance and grades in particular
should be paginated or lazy-loaded.

---

## 6. Patterns Summary

| Pattern                    | Status       | Detail |
|----------------------------|--------------|--------|
| SQL parameterization       | Good         | All queries use %s — no string formatting |
| Connection pooling         | Good         | psycopg3, min 2 / max 20 connections |
| Role-based decorators      | Good         | Clean for admin and teacher |
| Redis cache design         | Good         | Graceful degradation if Redis absent |
| Email generation           | Good         | Collision-safe, well-structured |
| Teacher subject auth       | Good         | Ownership verified before data access |
| Plain-text passwords       | Critical     | Stored in DB + accepted at login |
| CSRF protection            | Missing      | No tokens on any POST form |
| Student auth decorator     | Inconsistent | Manual role check instead of decorator |
| Raw SQL in blueprints      | Concern      | Admin dashboard bypasses db.py layer |
| N+1 attendance query       | Concern      | 50 submissions = 51 DB queries |
| Class name string parsing  | Fragile      | Breaks if display format changes |
| Hardcoded Windows path     | Concern      | db.py PostgreSQL bin path |

---

*See technical-recommendations.md for the prioritized fix list.*
