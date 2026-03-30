# MIS Codebase Audit Report
An extensive technical audit of the MIS GitHub repository (`https://github.com/mazear21/MIS.git`).

## 1. Tech Stack Summary
- **Backend framework:** Flask (Python)
- **Database:** PostgreSQL (using `psycopg` connection pool)
- **Caching:** Redis
- **Templating:** Jinja2 (Flask default)
- **Authentication:** `Werkzeug.security` (password hashing), custom session-based role management ([user_id](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#693-703), `role`, `major_id`)
- **Environment Management:** `python-dotenv`
- **File Uploads:** Werkzeug `secure_filename`, stored locally in `app.config['UPLOAD_FOLDER']`
- **Internationalization (i18n):** Basic session-based language switching ([en](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#701-725), `ku`, [ar](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/auth.py#161-178)) via a context processor.

## 2. Architecture Overview
The application follows a standard Flask Blueprints architecture:
- **[app.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/app.py):** The application factory setting up the database connection pool, Redis cache, Jinja environment, request hooks, and registering three main blueprints (auth, admin, teacher, student).
- **[config.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/config.py):** Configuration classes handling environment variables (Base, Dev, Prod).
- **[db.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py):** A massive centralized Database Access Object (DAO) pattern mapping. Contains ~2900 lines of raw SQL queries mapped to Python functions. Implements a primitive caching layer wrapping DB calls.
- **Blueprints (`auth`, [admin](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/app.py#147-156), [teacher](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#466-477), [student](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#701-725)):** Route handlers organized by user role. They interact heavily with [db.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py) for data operations.
- **Role-Based Access Control (RBAC):** Handled via custom decorators (`@login_required`, `@admin_required`, `@teacher_required`, `@superadmin_required`).

**Data Flow:** Client Request -> Blueprint Route -> `@role_required` check -> [db.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py) function -> Execute SQL -> Return JSON/Template.

## 3. Database Schema Summary
The database is a highly interconnected relational schema (PostgreSQL):
- **Core Entities:** [users](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#357-377), [departments](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#2442-2451), [majors](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#1503-1514), [classes](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#629-638), [subjects](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#949-955).
- **User Roles:** [teachers](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#466-477) and [students](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#701-725) act as extension tables uniquely linking to `users.id` (1-to-1).
- **Academic Tracking:** `student_enrollments` manages which student takes which subject. [grade_components](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#1321-1342) establishes a rubric per subject.
- **Operations:**
  - [attendance](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/teacher.py#56-91): Daily tracking of `student_id` for a `subject_id`.
  - [grades](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/teacher.py#191-234): Scores for a specific `student_id`, `subject_id`, and [grade_component](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#1104-1240).
  - [weekly_topics](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#2068-2081), [homework](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/teacher.py#434-473), [lecture_files](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#2198-2210): Course material tracking.
  - `class_schedules`: Semi-structured schedule data stored as JSONB.
  - [upgrade_history](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#2853-2863): Audit trail for student semester promotion/failure.
- **System States:** [enrollment_periods](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#1348-1369) and [exam_periods](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#1414-1419) control temporal access to features.

## 4. Security Issues

### CRITICAL: Plaintext Password Storage
**Location:** [db.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py) ([create_user](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#374-382)), [blueprints/auth.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/auth.py) ([login](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/auth.py#86-137)), [database/schema.sql](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/database/schema.sql) (if `plain_password` existed, though seemingly removed in SQL schema but logic persists in Python)
**Issue:** [create_user](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#374-382) accepts both a `password_hash` and `plain_password`, storing the plaintext password in the database. The [auth.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/auth.py) login route even falls back to checking the plaintext password.
```python
# db.py
def create_user(username, password_hash, full_name, role, email=None, plain_password=None, major_id=None):
    # INSERTS plain_password into DB
    query = """
    INSERT INTO users (username, password_hash, full_name, role, email, plain_password, major_id)
    ...
```
**Fix:** Remove the `plain_password` column entirely. Rely *strictly* on `check_password_hash`.
```python
# auth.py (Fix example)
if user and check_password_hash(user['password_hash'], password):
    # Success...
else:
    flash('Invalid username or password.', 'danger')
# Remove the fallback condition:
# elif user and user.get('plain_password') == password:
```

### CRITICAL: Secrets Committed in Source Control
**Location:** [.env](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/.env), [config.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/config.py)
**Issue:** [.env](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/.env) containing production `DB_PASSWORD` and `SECRET_KEY` is committed. [config.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/config.py) has a fallback `SECRET_KEY` that is static.
**Fix:** Add [.env](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/.env) to [.gitignore](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/.gitignore). In [config.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/config.py), mandate that `SECRET_KEY` is set in production without fallbacks that could be exploited.

### HIGH: Open Redirect Vulnerability
**Location:** [app.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/app.py) ([set_language](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/auth.py#149-159) route), [blueprints/auth.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/auth.py) ([logout](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/auth.py#139-147) and multiple role-redirects)
**Issue:** The app frequently redirects users to the `request.referrer`. This is vulnerable to Open Redirect attacks if an attacker tricks a user into clicking a link that sets the referrer inappropriately.
```python
# app.py
@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('auth.login'))
```
**Fix:** Validate that the referrer is a relative path or belongs to the application's domain. Tools like `flask_login.utils.is_safe_url` are designed for this.

### HIGH: Hardcoded Executable Paths
**Location:** [db.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py) (Backup/Restore functionality)
**Issue:** `_pg_bin = r"C:\\Program Files\\PostgreSQL\\17\\bin"` is hardcoded. This will fail on Linux deployments (standard for production) or different Windows configurations.
**Fix:** Store the path to PostgreSQL binoculars in an environment variable or rely on system PATH.

## 5. Bug Report

### HIGH: [get_student_semester_results](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/db.py#2882-2922) Division by Zero Potential
**Location:** `db.py:2905`
**Issue:** Calculates percentage as [(total_score / total_max * 100) if total_max > 0 else 0](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/admin.py#357-377). However, if `total_max` is exactly `0`, the student automatically receives 0% (F), even if the teacher assigned no graded components yet.

### MEDIUM: Local File Inclusion / Path Traversal Vector
**Location:** [blueprints/teacher.py](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/teacher.py) ([view_file](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/teacher.py#669-695), [download_file](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/teacher.py#641-667))
**Issue:** Files are served using `send_from_directory` with `os.path.basename`, which is generally safe. However, when files are uploaded ([upload_file](file:///C:/Users/DATA%20FORCE/.gemini/antigravity/scratch/MIS-audit/blueprints/teacher.py#848-932)), `secure_filename` is used, which is good, but earlier iterations or manually inserted DB records might contain traversal paths (`../../`).
**Fix:** Ensure strict validation on the DB layer for `file_path`.

### LOW: ID Generation Race Condition
**Location:** `blueprints/admin.py:add_student_ajax`
**Issue:** ID is generated by querying the max `student_number` and incrementing:
`"SELECT student_number FROM students ... ORDER BY student_number DESC LIMIT 1"`
Under heavy concurrent load, two admins adding students simultaneously could get the exact same ID, resulting in a database UNIQUE constraint violation and a failed request (500 error) for one user.
**Fix:** Use PostgreSQL sequences combined with formatting (`nextval`), or implement a robust retry mechanism on insertion failure.

## 6. Performance Issues

### HIGH: Monolithic `db.py` File Size
**Location:** `db.py` (2900+ lines)
**Issue:** The entire database interaction layer is a single file. While not strictly a runtime performance issue, it's a massive maintenance and cognitive load bottleneck. Python parser has to load the entire module.
**Fix:** Refactor into a `/models` directory (e.g., `models/users.py`, `models/grades.py`).

### MEDIUM: Connection Pool Exhaustion in Admin Routes
**Location:** `blueprints/admin.py` (`api_get_teachers_subjects_by_semester`)
**Issue:** Some routes manually grab a connection from the pool (`conn = db.get_db_connection()`) and close it inside a finally block. While acceptable, if an exception happens outside the `try/finally` before it's caught, or if the thread dies, connections leak. `db.py` already defines `execute_query` which handles connection lifecycle safely via Python context managers (`with pool.connection() as conn:`). Admin routes bypass this safe wrapper.
**Fix:** Replace all manual `conn.cursor()` logic in Blueprints with calls to `db.execute_query`.

### MEDIUM: N+1 Query Problems
**Location:** `db.py:get_semester_upgrade_preview`
**Issue:** For *every* student in a semester (N students), it executes a query for enrolled subjects, and then for *every* subject, it executes a query for grades. If 100 students take 6 subjects, that is 1 + 100 + 600 = 701 queries just to generate the preview.
**Fix:** Use JOINs and `GROUP BY` to fetch all necessary grade data in 1 or 2 bulk queries, then process the data structures in Python.

## 7. Code Quality Issues

### HIGH: Business Logic inside Database Layer
**Issue:** `db.py` is filled with complex business logic (e.g., grading calculations, promotion logic, scheduling algorithms). The DAO layer should only interface with the DB.
**Fix:** Extract logic into a `services/` layer (`services/grading.py`, `services/scheduling.py`).

### MEDIUM: Exception Swallowing
**Location:** Throughout codebase (e.g., `blueprints/admin.py:856`)
**Issue:** Naked `except Exception as e:` blocks are used frequently, often just printing the error to console and returning a generic 500 JSON.
**Fix:** Implement a global error handler in Flask (`@app.errorhandler`), log errors professionally using `logging`, and avoid catching base `Exception` everywhere unless strictly as a top-level fallback.

## 8. Recommended Fixes (Implementation Strategy)

### Phase 1: Security Criticals (Immediate)
1. **Remove Plaintext Passwords:** Drop the `plain_password` column from users (if it exists) and strip all references in `create_user` and `login`.
2. **Environment Variables:** Remove `.env` from git tracking (`git rm --cached .env`), rotate passwords, and use secure secrets.

### Phase 2: Fix Production Deployment Blockers
3. **Database Paths:** Refactor `db.py` backup/restore to use environment variables for PostgreSQL bin paths. `DB_BIN_DIR = os.getenv('PG_BIN_DIR', '')`.

```python
# Modified db.py Database Backup
import subprocess
def backup_database():
    pg_dump = os.path.join(os.getenv('PG_BIN_DIR', ''), 'pg_dump')
    # Use array for parameters, not shell=True for security against injection
    cmd = [pg_dump, '-U', user, '-h', host, '-d', dbname, '-F', 'c', '-f', backup_file]
    subprocess.run(cmd, env=dict(os.environ, PGPASSWORD=password), check=True)
```

### Phase 3: Architectural Refactoring
4. **Service Layer Separation:** Move logic out of Blueprints and `db.py` into distinct python modules.
5. **ORM Adoption:** Consider migrating from raw `psycopg` queries to SQLAlchemy. Managing an evolving schema with thousands of lines of raw SQL strings is highly error-prone and severely limits refactoring ability.

## Summary: What is Working Well
- **Excellent Feature Completeness:** The system ambitiously covers the entire lifecycle of an academic institute (scheduling, grading rubrics, attendance, exam registrations).
- **Caching Mechanism:** The manual Redis caching wrapper around frequent lookup tables (departments, majors) is a very smart inclusion for performance.
- **Connection Pooling:** Utilizing `psycopg_pool` is the technically correct approach for high-concurrency Python DB applications.
- **Role Scoping at DB Level:** Queries frequently check both the ID and the `major_id`, protecting against cross-department data leakage.
