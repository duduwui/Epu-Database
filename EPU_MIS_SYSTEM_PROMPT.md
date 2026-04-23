# EPU MIS — Complete System Context Prompt
# For AI Agents: Everything you need to understand this project A–Z
# Version: Current as of April 2026

---

## ROLE AND PURPOSE

You are working on the **EPU MIS** (Erbil Polytechnic University — Management
Information System). This is a production-targeted internal academic management
platform built in Python/Flask + PostgreSQL. It manages the full academic
lifecycle of a university department: student enrollment, attendance, grading,
exam eligibility, semester promotion, and result publishing — across multiple
user roles (superadmin, admin, teacher, student).

The project is currently in active development. It is **not a demo**. Real
students and teachers at EPU's MIS department are the intended users. The
developer is Mazear, a freelance developer in Erbil, Kurdistan Region, Iraq.

---

## TECH STACK — EXACT VERSIONS

| Layer        | Technology                             |
|--------------|----------------------------------------|
| Language     | Python 3.8+                            |
| Framework    | Flask 3.0.0                            |
| Database     | PostgreSQL 17 (local Windows install)  |
| DB Driver    | psycopg 3 (psycopg[binary] >= 3.1.0)  |
| Connection   | psycopg_pool (connection pool min=2, max=20) |
| Auth         | Werkzeug password hashing + Flask session cookies |
| Encryption   | cryptography (Fernet) for plain_password column |
| Caching      | Redis (optional, graceful degradation) |
| Frontend     | HTML + Bootstrap 5 + Bootstrap Icons + vanilla JS |
| Templating   | Jinja2 (server-rendered, no SPA)       |
| i18n         | Custom i18n.py (English, Kurdish Sorani, Arabic + RTL) |
| Compression  | Gzip via after_request hook            |
| Config       | python-dotenv (.env file)              |
| Server       | Flask dev server (app.run), host=0.0.0.0, port=5000 |

---

## PROJECT FILE STRUCTURE

```
MIS/
├── app.py                  # App factory — registers blueprints, gzip, i18n context
├── config.py               # ENV-based config (DB, SECRET_KEY, FERNET_KEY)
├── db.py                   # ALL database queries (~95 KB, single-file DAO layer)
├── i18n.py                 # Translation engine + Kurdish/Arabic dictionaries (38 KB)
├── init_db.py              # DB initialization script
├── requirements.txt        # 8 dependencies
├── .env                    # DB credentials + secret keys (not in git)
│
├── blueprints/
│   ├── auth.py             # Login, logout, decorators, language switch
│   ├── admin.py            # All admin routes (~79 KB — largest blueprint)
│   ├── teacher.py          # Teacher routes (40 KB)
│   └── student.py          # Student routes (26 KB)
│
├── templates/
│   ├── base.html           # Master layout (RTL support, Bootstrap, nav)
│   ├── login.html          # Login page (email + password)
│   ├── admin/              # 24 admin templates
│   ├── teacher/            # 15 teacher templates
│   └── student/            # 8 student templates
│
├── database/
│   ├── schema.sql          # Base schema (10 core tables)
│   ├── migrate_to_majors.sql # Multi-major migration (seeds 72 majors)
│   ├── seed_epu_departments.sql # EPU college/department structure
│   └── *.sql               # 17 other migration patches
│
├── static/css/             # Custom styles
└── uploads/                # Teacher-uploaded files (local disk, max 50 MB)
```

---

## DATABASE SCHEMA — COMPLETE TABLE MAP

### Core Tables (base schema)

```sql
users (
  id, username UNIQUE, password_hash, full_name,
  role CHECK IN ('admin','teacher','student'),
  email, plain_password,  -- plain_password is Fernet-encrypted
  major_id FK→majors,
  created_at
)

classes (
  id, name, description,
  year CHECK IN (1,2),
  semester CHECK IN (1,2,3,4),
  section CHECK IN ('A','B','C'),
  shift CHECK IN ('morning','night'),
  major_id FK→majors,
  is_active BOOLEAN,
  UNIQUE(year, semester, section, shift)  -- NOTE: needs major_id added for EPU-wide uniqueness
)

teachers (
  id, user_id UNIQUE FK→users CASCADE,
  department, phone, created_at
)

students (
  id, user_id UNIQUE FK→users CASCADE,
  class_id FK→classes SET NULL,
  student_number UNIQUE,
  year, semester, shift, section,  -- denormalized from class for direct queries
  phone, created_at
)

subjects (
  id, name, semester,
  credits DEFAULT 6,
  description,
  results_published BOOLEAN DEFAULT false,  -- controls student Results tab visibility
  major_id FK→majors,
  created_at
)

grade_components (
  id, subject_id FK→subjects CASCADE,
  component_type CHECK IN ('homework','quiz','report','project','exam',
                           'midterm','final','lab_report','activity','seminar'),
  component_name, max_score, weight_percentage,
  display_order, pair_group,  -- pair_group: links Report+Seminar as averaged pair
  created_at
)

grades (
  id, student_id FK→students CASCADE,
  subject_id FK→subjects CASCADE,
  teacher_id FK→teachers SET NULL,
  grade_type, title, score, max_score,
  component_id FK→grade_components,
  published BOOLEAN DEFAULT false,  -- teacher publish gate
  date, notes, created_at
)

attendance (
  id, student_id, subject_id, teacher_id,
  date DATE, status CHECK IN ('present','absent','late','excused'),
  notes,
  UNIQUE(student_id, subject_id, date)
)

homework (
  id, class_id, subject_id, teacher_id,
  title, description, due_date,
  filename, file_path, file_type, file_size
)

weekly_topics (
  id, class_id, subject_id, teacher_id,
  week_number, topic, description, date_covered,
  note_type DEFAULT 'exam',  -- repurposed: 'exam','quiz','report','seminar'
  UNIQUE(class_id, subject_id, week_number)
)

timetable (
  id, class_id, subject_id, teacher_id,
  day_of_week, start_time, end_time, room
)
```

### Extended Tables (added via migrations)

```sql
departments (id, name, code, description)  -- EPU colleges/institutes

majors (
  id, name,
  code VARCHAR(6) UNIQUE,  -- 6-digit numeric code, part of EPU email format
  department_id FK→departments,
  description, created_at
)
-- 72 majors seeded across 13 EPU colleges

student_enrollments (
  id, student_id FK→students, subject_id FK→subjects,
  enrolled_at TIMESTAMP DEFAULT NOW()
)  -- student self-enrollment during active enrollment period

teacher_assignments (
  id, teacher_id FK→teachers, subject_id FK→subjects,
  class_id FK→classes, shift, teacher_type,
  UNIQUE(teacher_id, subject_id, class_id)
)

enrollment_periods (
  id, semester, start_date, end_date, description, created_by FK→users
)  -- admin-controlled window for student subject enrollment

exam_periods (
  id, semester, period_type CHECK IN ('final','second_round'),
  start_date, end_date, description, created_by FK→users
)  -- admin-controlled window for exam signups

exam_signups (
  id, student_id, subject_id,
  exam_type CHECK IN ('final','second_round'),
  signed_up_at,
  UNIQUE(student_id, subject_id, exam_type)
)

class_schedules (
  id, major_id FK→majors, semester, shift, section,
  schedule_data JSONB,  -- visual timetable as JSON
  updated_at,
  UNIQUE(major_id, semester, shift, section)
)

lecture_files (
  id, subject_id, teacher_id, class_id,
  title, description, file_name, file_path,
  file_size, file_type, week_number, uploaded_at
)

upgrade_history (
  id, student_id FK→students CASCADE,
  from_semester, to_semester, from_year, to_year,
  status CHECK IN ('passed','failed','graduated'),
  details JSONB, upgraded_at, upgraded_by FK→users
)

system_settings (key, value, description, updated_at)
-- Stores: current_cycle (1 or 2), controls which semesters are active
```

---

## USER ROLES AND PERMISSION MODEL

### Role Hierarchy

```
Superadmin
  └── Major Admin (one per major)
        ├── Teachers (many per major)
        └── Students (many per major)
```

### Superadmin
- Email: `admin@epu.edu.iq` (no major code in email → major_id = NULL)
- Can access: everything across ALL majors
- Unique pages: Majors management, Departments management
- Identified by: `session.role == 'admin' AND session.major_id IS NULL`
- Entry point after login: `/admin/majors`

### Major Admin
- Email format: `firstname_lastnameMIS######@epu.edu.iq`
  - The 6-digit code (`######`) identifies the major
  - Example: `ali_ahmedmis562781@epu.edu.iq` → major code `562781` → MIS department
- Can access: only their major's data (scoped by major_id in all queries)
- Manages: users, students, teachers, classes, subjects, grade components,
           enrollment periods, exam periods, schedules, attendance records,
           grade publishing, results publishing, semester upgrades
- Entry point after login: `/admin/dashboard`

### Teacher
- Assigned to subjects via `teacher_assignments` table
- Can access: only subjects assigned to them (verified by teacher_id ownership)
- Capabilities: take attendance, enter grades, publish grades for their subjects,
               create homework, upload lecture files, manage exam notes/topics,
               view schedule
- One subject can have TWO teachers: theory teacher + practical teacher

### Student
- Belongs to exactly one major (via `users.major_id`)
- Has year, semester, shift, section fields (denormalized)
- Capabilities:
  - Enroll in subjects (during active enrollment_period)
  - Sign up for final exam (if 60% marks ≥ 20/60 threshold)
  - Sign up for second_round exam (if results published and failed)
  - View My Grades (60% portion, excludes 'final' component)
  - View Results/Transcript (100%, only after admin publishes)
  - View attendance, homework, schedule, lecture files

---

## AUTHENTICATION FLOW

### Login Process (step by step)
1. User submits email + password to POST `/login`
2. `db.get_user_by_email(email)` fetches user row
3. `check_password_hash(user['password_hash'], password)` verifies
4. Session stores: user_id, username, full_name, role
5. **Major detection from email:**
   - Email local part before `@` is split on last `.`
   - Example: `ali_ahmedmis562781@epu.edu.iq` → code = `562781`
   - `db.get_major_by_code('562781')` → major row
   - `db.assign_major_to_user(user_id, major_id)` persists it
   - Session stores: major_id, major_code, major_name
6. `auth.dashboard` route redirects based on role:
   - superadmin → `/admin/majors`
   - major admin → `/admin/dashboard`
   - teacher → `/teacher/dashboard`
   - student → `/student/dashboard`

### Decorators (defined in auth.py, imported by all blueprints)
```python
@login_required      # any logged-in user
@admin_required      # role == 'admin' (any admin)
@superadmin_required # role == 'admin' AND major_id IS NULL
@teacher_required    # role in ('admin', 'teacher')
# NOTE: @student_required does NOT exist — student routes do manual role check
```

### Language Switching
- `/set-language/<lang>` — stores lang in session, safe redirect validation
- Supported: `en` (English), `ku` (Kurdish Sorani, RTL), `ar` (Arabic, RTL)
- RTL detection: `is_rtl(lang)` → injected into every template via context processor
- Auto-translates JSON API response fields via `after_request` hook

---

## GRADING SYSTEM — COMPLETE LOGIC

### The 60/40 Split
Every subject is graded out of 100 total:
- **60% (continuous assessment):** Homework, quizzes, reports, seminars, midterm
  - This is what the **My Grades** tab shows (final component excluded)
  - This is what determines **exam eligibility**
- **40% (final exam):** Single 'final' type component
  - Added by teacher after final exam
  - The **Results** tab shows the full 100% total (60% + 40%)

### Grade Components
Admin assigns a grading rubric to each subject via `grade_components` table.
Each component has: type, name, max_score, weight_percentage, display_order.

**Special: Paired Components (pair_group)**
Report + Seminar can be linked with same `pair_group` integer.
When paired, their scores are averaged (avg-of-avgs), not summed.
This allows a Report+Seminar pair to count as one component's weight.

### The Canonical Grade Calculator (`db._calc_grade_totals(rows)`)
This is the **single source of truth** used in all three grade-display locations.
Rules:
- `midterm` type → **SUM** (Midterm Practical + Midterm Theoretical = total)
- All other types (quiz, homework, etc.) → **AVERAGE** across entries
- Paired components (same pair_group) → **average of per-type averages**

```python
# Example: 3 quizzes scored 3/11, 5/11, 7/11
# Quiz average = (3+5+7)/3 = 5.0 / 11.0  ← shown as "Quiz Avg 5.0/11.0"

# Example: Midterm Practical 15/15 + Midterm Theoretical 8/10
# Midterm total = 15+8 = 23.0 / 25.0     ← shown as "Midterm Total 23.0/25.0"
```

### Grade Publishing — Two Stages
**Stage 1 — Teacher publish** (grades.published flag)
- Teacher enters grades → saved as `published=FALSE` (draft)
- Teacher clicks "Publish Grades" → sets `published=TRUE` for their class
- Students can now see grades in **My Grades** tab
- Route: `POST /teacher/grades/publish/<subject_id>/<class_id>`
- DB: `publish_grades_for_subject(subject_id, class_id)`

**Stage 2 — Admin publish results** (subjects.results_published flag)
- Admin clicks "Publish Results" for a subject or whole semester
- Sets `results_published=TRUE` on the `subjects` row
- Students can now see **Results/Transcript** tab with full 100% scores
- Route: `POST /admin/publish-semester-results/<semester>`
- DB: `publish_semester_results(semester)`

**IMPORTANT KNOWN BUG:** `results_published` is on the shared subject row,
not per-enrollment. Publishing for one cohort leaks to future students
enrolled in the same subject. This is a known issue to be fixed.

### Exam Eligibility Check (Signup Tab)
For **final exam** signup (during active exam_period):
```python
# Student must have at least 20/60 in the 60% portion
midterm = get_student_midterm_score(student_id, subject_id)
normalized = midterm['total_score'] / midterm['total_max'] * 60
eligible = normalized >= 20
```

For **second_round exam** signup:
- Results must be published for the subject
- Student must have scored < 60% overall
- Student can then redo only the final exam (40%)

---

## SEMESTER LIFECYCLE — FULL WORKFLOW

```
[ADMIN] Open enrollment period for Semester 1
    ↓
[STUDENT] Enroll in subjects (enrollment period active)
    ↓
[TEACHER] Take attendance throughout semester
[TEACHER] Enter grades for all components (draft)
[TEACHER] Publish grades → students see 60% in My Grades
    ↓
[ADMIN] Open final exam period
    ↓
[STUDENT] Sign up for final exam (if ≥20/60 eligible)
[TEACHER] Enter final exam grades
[TEACHER] Publish final grades
    ↓
[ADMIN] Publish semester results → students see 100% in Results tab
    ↓
[ADMIN] Run Semester Upgrade Preview (upgrade_preview page)
    → System calculates: does student pass ALL subjects at ≥60%?
    → "Passing Students" list → promoted to Semester 2
    → "Failed Students" list → must do second round
    ↓
[ADMIN] Open second_round exam period for failed students
    ↓
[STUDENT] Failed students sign up for second_round exam
[TEACHER] Enter second round final grades, publish
    ↓
[ADMIN] Execute Semester Upgrade → students.semester updated
    → Passing students: semester+1, year updated, new class_id assigned
    → Graduated (Sem 4): semester=NULL
    → upgrade_history record created for each student
    ↓
[SEM 2] Students now enrolled in Sem 2 subjects
    Previous Sem 1 enrollments remain in student_enrollments (for history)
    Results tab shows BOTH semesters (historical view)
```

---

## ADMIN FEATURES — COMPLETE LIST

### Dashboard
- Total students, teachers, subjects counts
- Breakdown by semester (1-4) × shift (morning/night)

### User Management (`/admin/users`)
- Create/edit/delete users (admin, teacher, student)
- Auto-generate EPU email: `firstname_lastname{major_abbrev}{6digits}@epu.edu.iq`
- Store encrypted plain_password (Fernet) for admin visibility
- Bulk student creation

### Student Management (`/admin/students`)
- View all students with filters (semester, shift, section, search)
- Edit student: class assignment syncs year/semester/shift/section
- Student number auto-generation

### Teacher Management (`/admin/teachers`)
- View all teachers
- Assign teachers to subjects/classes (theory or practical type)

### Classes (`/admin/classes`)
- Create classes: year × semester × section × shift × major_id
- Toggle active/inactive

### Subjects (`/admin/subjects`)
- Create subjects per semester with credits
- Assign theory + practical teachers per class via teacher_assignments
- Toggle results_published per subject
- Bulk publish/unpublish entire semester results

### Grade Components (`/admin/subjects/<id>/grading`)
- Define grading rubric for each subject
- Add components: homework, quiz, midterm (single or split practical/theoretical), final, etc.
- Set max_score and weight_percentage
- Add paired Report+Seminar components (shared pair_group)
- Total weight validation (must not exceed 100%)
- Drag-to-reorder display order

### Enrollment Periods (`/admin/enrollment-periods`)
- Create start/end date windows per semester
- Major-scoped (only students in this major can enroll)
- Students can only enroll when period is active

### Exam Periods (`/admin/exam-periods`)
- Create final and second_round exam windows per semester
- Controls when exam signup tab is visible to students

### Schedule Builder (`/admin/dashboard` → schedule section)
- Visual timetable builder (AJAX API)
- Stores schedule as JSONB in class_schedules table
- Per major × semester × shift × section

### Attendance Records & Summary (`/admin/attendance-records`, `/admin/attendance-summary`)
- View all teacher attendance submissions
- Filter by date, subject, shift, section
- Per-student attendance summary

### Semester Upgrade (`/admin/upgrade/preview/<semester>`)
- Preview: shows all students in that semester with pass/fail per subject
- Execute: promotes passing students, records failed students
- Filter by shift/section/search in template

### Departments & Majors (Superadmin only)
- `/admin/departments` — manage EPU college structure
- `/admin/majors` — manage 72 majors across colleges, create major admins

---

## TEACHER FEATURES — COMPLETE LIST

### Dashboard (`/teacher/dashboard`)
- List of all assigned subjects grouped by subject name
- Shows classes per subject, homework list

### Attendance (`/teacher/attendance`)
- List of subjects → select class → take attendance
- `GET /teacher/attendance/take/<subject_id>/<class_id>` → date picker
- Records: present, absent, late, excused per student
- `POST` saves with upsert (ON CONFLICT updates existing record)
- View logs with date/status filters

### Grades (`/teacher/grades`)
- List subjects → select class → grade entry form
- Modal per student showing all grade components
- Enter score per component, save as draft
- `POST /teacher/grades/add/<subject_id>/<class_id>`
- Publish button: marks all grades as published for that class
- View grades table

### Homework (`/teacher/homework`)
- Create homework with title, description, due date
- Attach file (PDF, DOC, etc.)
- Assign to multiple classes at once
- Students see due homework on their dashboard

### Exam Notes / Topics (`/teacher/topics`)
- Create exam/quiz/seminar/report notes (repurposed weekly_topics table)
- Displays as upcoming events for students

### Files (`/teacher/files`)
- Upload lecture files per subject/class
- Organize by week number
- Students download from their Files tab

### Schedule (`/teacher/schedule`)
- View their own timetable from class_schedules JSONB

---

## STUDENT FEATURES — COMPLETE LIST

### Dashboard (`/student/dashboard`)
- Quick stats: upcoming homework, recent attendance
- Class schedule display
- Recent grades

### Signups (`/student/signups`)
- **Subjects tab** (during enrollment period):
  - See all subjects for their semester+major
  - Enroll/unenroll per subject
  - Shows teacher names (theory + practical)
- **Exams tab** (during exam period):
  - Final exam: shows eligible/ineligible subjects with midterm_normalized/60 score
  - Second round: shows failed subjects after results published
  - Sign up / cancel per subject

### My Grades (`/student/grades`)
- Semester selector (shows only enrolled semesters)
- Subject selector
- Breakdown table:
  - Each component row (Quiz 1: 3/11, Quiz 2: 5/11, etc.)
  - Subtotal rows per type (Quiz Avg: 5.0/11.0)
  - Midterm rows (Practical: 15/15, Theoretical: 8/10, Total: 23/25)
  - Paired group rows (Report+Seminar combined average)
- Summary cards: Weighted Score, Total Marks (e.g. 52.0/60), Grade Status letter

### Results (`/student/results`)
- Only visible if `subjects.results_published = TRUE`
- Shows final transcript per semester
- Per subject: percentage, letter grade (A+ through F), pass/fail
- Weighted score = percentage × credits / 100
- Semester total weighted score
- Grand total across all semesters

### Files (`/student/files`)
- Grouped by subject
- Download lecture files uploaded by teachers

### History (`/student/history`)
- Historical view of past semester enrollments
- Driven by upgrade_history table

---

## i18n SYSTEM

### How It Works
- Custom `i18n.py` — no third-party library
- Dictionaries for Kurdish Sorani (ku) and Arabic (ar) keyed by English strings
- `translate(text, lang)` — looks up in dictionary, falls back to English
- `is_rtl(lang)` → True for 'ku' and 'ar' → adds `dir="rtl"` to HTML
- Injected into templates via `context['t'] = lambda text: translate(text, lang)`
- Usage in templates: `{{ t('My Grades') }}` → 'نمرەکانم' in Kurdish

### JSON API Translation
`app.py` `after_request` hook intercepts JSON responses:
- Translates fields named: message, error, title, label, hint, status_text, toast, description, detail
- Only runs if `lang != 'en'`

### Language Switching
`GET /set-language/<lang>` → stores in session → validates redirect is same-origin

---

## DB.PY ARCHITECTURE

### Two-Tier Pattern
**Tier 1 — Low-level helpers:**
```python
execute_query(query, params, fetch_one, fetch_all)  # main workhorse
execute_insert_returning(query, params)              # INSERT ... RETURNING id
get_db_connection()                                  # pulls from pool
return_connection(conn)                              # returns to pool
row_to_dict(cursor, row)                             # tuple → dict
```

**Tier 2 — Domain functions:**
Hundreds of named functions grouped by domain:
- `get_user_by_email`, `create_user`, `update_user_password`
- `get_students_by_class`, `create_student_with_semester`
- `get_subjects_by_teacher`, `get_grade_components_by_subject`
- `record_attendance`, `get_attendance_by_student`
- `upsert_grade`, `publish_grades_for_subject`
- `get_exam_eligible_subjects`, `signup_for_exam`
- `get_semester_upgrade_preview`, `execute_semester_upgrade`
- etc.

### Redis Cache (Optional)
```python
# Graceful degradation: if Redis not running, falls through to PostgreSQL
_cache_get(key)          # returns None on miss or Redis unavailable
_cache_set(key, val, ttl)  # silently skips if Redis down
_cache_delete(*keys)     # called on mutations

# Cached: grade_components (5 min), classes:all (10 min), majors, departments
```

### Password Encryption (Fernet)
```python
encrypt_plain_password(plain: str) → str   # encrypts for DB storage
decrypt_plain_password(encrypted: str) → str  # decrypts for admin display
# FERNET_KEY loaded from config, graceful None if not set
```

---

## KNOWN BUGS AND OPEN ISSUES

### Critical (must fix before production)
1. **results_published leaks to new students:** The flag is on the shared
   `subjects` row, not per-enrollment. If Sem 1 results are published and
   new students are added, they immediately see phantom "0%" results.
   Fix approach: add `results_published_at` timestamp + check `enrolled_at <= published_at`

2. **Upgrade preview shows wrong semester subjects:** `get_semester_upgrade_preview`
   fetches ALL enrollments for a student (no semester filter). A Sem 2 student
   with Sem 1 history sees both semesters' subjects in the preview.
   Fix: add `AND sub.semester = %s` to the enrolled subjects query inside preview.

3. **publish/upgrade not scoped by major_id:** `publish_semester_results`,
   `unpublish_semester_results`, `get_semester_upgrade_preview` do not filter
   by major_id, so in a multi-major system one admin can affect another major.

### Security (to fix before any external access)
4. **No CSRF protection** on any POST form
5. **SECRET_KEY has weak fallback** in config.py
6. **.env committed to git** (plain_password and DB credentials exposed)
7. **Open redirect** in set_language route (partially fixed)
8. **Login has no rate limiting**

### Architecture / Code Quality
9. **admin.py is 79 KB** — too many responsibilities in one file
10. **Inline SQL in admin blueprint** — some routes bypass db.py layer
11. **N+1 query in attendance_records** — one query per submission
12. **classes UNIQUE constraint** too narrow — doesn't include major_id
    (two different majors can't have same year/semester/section/shift)
13. **@student_required decorator missing** — student routes do manual role check

---

## MULTI-MAJOR ARCHITECTURE

### How Major Scoping Works
Every admin operation is scoped by `major_id` from `session.major_id`:
```python
# Example: admin can only see their own major's students
users = db.get_all_users(dept_id)  # dept_id = session.get('major_id')
```

Superadmin has `major_id = NULL` → sees everything.

### Email = Identity
The email format encodes the major:
```
firstname_lastname{MAJOR_ABBREV}{6DIGITS}@epu.edu.iq
Example: ali_ahmedmis562781@epu.edu.iq
         └─ name ─┘└─abbrev─┘└─ code ─┘
```
- `MAJOR_ABBREV` = lowercase initials of major name (e.g. 'mis', 'ce', 'ai')
- 6-digit code = unique identifier from `majors.code`
- Login detects major from email → assigns major_id to user

### Seeded Data
`migrate_to_majors.sql` seeds 72 majors across 13 EPU colleges including:
- College of Health Sciences, College of Engineering, College of Computer Engineering
- College of Technology, College of Administration & Economics
- Technical Institutes (Koya, Choman, Mergasor, Khabat, Soran, Shaqlawa)

---

## SCHEDULE SYSTEM

### Storage
Schedule stored as JSONB in `class_schedules`:
- Key: `(major_id, semester, shift, section)`
- Value: array of schedule entries with subject, teacher, day, time, room, lectureType

### lectureType
- `'theory'` → uses `theoryStartTime` / `theoryEndTime`
- `'practical'` → uses `practicalStartTime` / `practicalEndTime`

### Teacher Schedule View
`get_teacher_schedule_from_builder(teacher_name, major_id)`:
- Searches all class_schedules JSONB for entries matching teacher name
- Returns day, time, subject, section info

---

## PERFORMANCE FEATURES

- **Connection pooling:** psycopg_pool (min=2, max=20, idle close after 5 min)
- **Gzip compression:** after_request, compresses text/HTML/JSON > 1.4 KB
- **Redis caching:** grade_components (5 min TTL), classes, majors, departments
- **Indexes:** attendance(student_id), attendance(date), grades(student_id/subject_id),
               students(class_id), subjects(class_id), majors(code), users(major_id)

---

## DEPLOYMENT NOTES

- Currently runs on Windows (developer's machine)
- Hardcoded `C:\Program Files\PostgreSQL\17\bin` path in db.py for libpq
- Uploads stored locally in `/uploads/` directory
- Not yet deployed to server
- Production would need: proper SECRET_KEY, FERNET_KEY, HTTPS, CSRF

---

## WHAT THIS SYSTEM IS NOT

- NOT a public website / CMS
- NOT an LMS (no video lectures, online quizzes, content delivery) — that's Moodle
- NOT a ministry ERP integration
- NOT a research registration system
- NOT a journal/publication system
- NOT a student admissions system (admin creates accounts manually)

It sits between Moodle (content delivery) and Bologna/ECTS (academic records)
filling the operational gap: attendance, grading workflow, exam eligibility,
semester progression — none of which EPU currently has in a running system.

---

## QUICK REFERENCE: KEY ROUTES

```
# Auth
GET/POST /login                           → login
GET      /logout                          → logout
GET      /dashboard                       → role-based redirect
GET      /set-language/<lang>             → switch UI language

# Admin
GET      /admin/dashboard                 → stats + schedule builder
GET/POST /admin/users                     → user management
GET/POST /admin/students                  → student management
GET/POST /admin/subjects                  → subject + teacher assignment
GET      /admin/subjects/<id>/grading     → grade component rubric editor
POST     /admin/subjects/<id>/toggle-results → toggle results_published
POST     /admin/publish-semester-results/<sem> → bulk publish results
GET/POST /admin/enrollment-periods        → enrollment window management
GET/POST /admin/exam-periods              → exam window management
GET      /admin/upgrade/preview/<sem>     → pass/fail preview
POST     /admin/upgrade/execute/<sem>     → execute promotion
GET      /admin/attendance-records        → all attendance submissions
GET      /admin/attendance-summary        → per-student attendance

# Teacher
GET      /teacher/dashboard               → subjects + homework list
GET      /teacher/attendance              → subject list
GET/POST /teacher/attendance/take/<sub>/<cls> → take/save attendance
GET      /teacher/grades                  → grade entry list
GET/POST /teacher/grades/add/<sub>/<cls>  → enter grades modal
POST     /teacher/grades/publish/<sub>/<cls> → publish grades
GET      /teacher/homework                → homework list
GET/POST /teacher/homework/add            → create homework
GET      /teacher/files                   → file list
GET/POST /teacher/files/upload            → upload lecture file
GET      /teacher/schedule                → view timetable
GET      /teacher/topics/<sub>/<cls>      → exam notes list

# Student
GET      /student/dashboard               → overview
GET      /student/signups                 → subjects + exam signup (tabbed)
GET      /student/grades                  → grade breakdown per subject
GET      /student/results                 → final transcript
GET      /student/files                   → lecture files
POST     /student/subjects/enroll/<id>    → enroll in subject (AJAX)
POST     /student/exams/signup/<id>/<type> → exam signup (AJAX)
```

---

## EXAMPLE: COMPLETE GRADING FLOW

**Setup:** Admin creates subject "Database Systems" for Sem 1, MIS major.
Admin adds grade components:
- Homework x3 (weight 15%), Quiz x3 (weight 11%), Seminar (weight 8%),
  Report (weight 8%), Midterm split: Practical (weight 15%) + Theoretical (weight 10%),
  Final (weight 33%)

**Teacher enters grades for student Ali:**
- Homework: 8/10, 9/10, 7/10 → saved as draft
- Quiz: 3/11, 5/11, 7/11 → saved as draft
- Seminar: 8/8
- Report: 7/8
- Midterm Practical: 15/15
- Midterm Theoretical: 8/10
→ Teacher publishes → Ali can now see My Grades tab

**Ali's My Grades calculation (excluding 'final'):**
- Homework Avg: (8+9+7)/3 = 8.0/10.0
- Quiz Avg: (3+5+7)/3 = 5.0/11.0
- Seminar: 8.0/8.0 (paired with Report)
- Report: 7.0/8.0 (paired with Report) → Paired avg = avg(8.0,7.0)/avg(8.0,8.0) = 7.5/8.0
- Midterm Total (SUM): 15+8 = 23.0/25.0
- Total Marks: 8.0 + 5.0 + 7.5 + 23.0 = 43.5 / 54.0
  (displayed as approximately the correct total out of the 60% components defined)

**Exam eligibility:**
- normalized = 43.5/54.0 × 60 = 48.3/60 → ≥20 → ELIGIBLE for final exam

**After final exam:** Teacher enters Final: 35/40 → publishes
**Admin publishes results** → Ali's Results tab shows:
- Total: 43.5 + 35 = 78.5/94 → ~83.5% → Grade: B

---

## HOW TO ONBOARD / RUN

```bash
# 1. Clone repo
git clone https://github.com/mazear21/MIS.git
cd MIS

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup PostgreSQL
# Create database: mis_system
# Run: database/schema.sql
# Run: database/migrate_to_majors.sql (for multi-major support)
# Run: database/seed_epu_departments.sql

# 5. Configure .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mis_system
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=generate_with_secrets.token_hex(32)
FERNET_KEY=generate_with_Fernet.generate_key()

# 6. Run
python app.py
# → http://localhost:5000
# Default login: admin@epu.edu.iq / admin123
```

---

## CONTEXT FOR AI AGENTS

When working on this project:

1. **Always check db.py first** for existing query functions before writing new SQL
2. **All SQL belongs in db.py**, not in blueprint route handlers
3. **major_id scoping is mandatory** — every admin query must filter by major_id
4. **_calc_grade_totals is the canonical calculator** — never duplicate grade logic
5. **Templates use Jinja2 + Bootstrap 5** — no React, no SPA framework
6. **The `t()` function is available in all templates** for i18n
7. **Redis is optional** — always write code that works without it
8. **`results_published` bug is known** — flag it but don't fix without confirming approach
9. **Student routes need manual role check** — no @student_required decorator yet
10. **The app runs on Windows with a hardcoded PG path** in db.py line ~8

When reading files, start with: app.py → blueprints/auth.py → db.py (first 200 lines)
→ then the specific blueprint you're working on.
