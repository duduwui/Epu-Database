# MIS — Technical Recommendations

**Phase 3 · Prioritized Action Plan**

---

## Priority 1 — Security (Fix Before Any Deployment)

### 1.1 Remove plain-text password storage

**Problem:** The `plain_password` column stores raw passwords in the database.
The login in `auth.py` accepts either the hash OR the raw password as valid.

**Fix — Three steps:**

Step A: Remove the fallback from auth.py login:
  # DELETE this entire OR branch:
  # (user.get('plain_password') and user['plain_password'] == password)
  # Keep only:
  if user and check_password_hash(user['password_hash'], password):

Step B: Remove plain_password from create_user() in db.py:
  # Remove the plain_password parameter and column from all INSERT statements

Step C: Drop the column from the database:
  ALTER TABLE users DROP COLUMN IF EXISTS plain_password;

Also delete: database/add_plain_password.sql (migration that added it)

---

### 1.2 Rotate the SECRET_KEY

**Problem:** config.py falls back to a public literal string if SECRET_KEY env var is not set.
Anyone who reads the repo can forge Flask session cookies with this key.

**Fix:**
  # config.py — remove the fallback literal
  SECRET_KEY = os.environ.get('SECRET_KEY')
  if not SECRET_KEY:
      raise RuntimeError("SECRET_KEY environment variable must be set")

Generate a strong key for .env:
  python -c "import secrets; print(secrets.token_hex(32))"

---

### 1.3 Add CSRF protection

**Problem:** All POST forms (login, add user, take attendance, submit grades)
have no CSRF token. A malicious site can submit forms on behalf of a logged-in user.

**Fix — Use Flask-WTF:**
  pip install Flask-WTF

  # config.py
  WTF_CSRF_ENABLED = True

  # app.py create_app()
  from flask_wtf.csrf import CSRFProtect
  csrf = CSRFProtect(app)

  # Every HTML form — add inside <form>:
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

Add flask-wtf to requirements.txt.

---

### 1.4 Remove hardcoded default credentials

**Problem:** app.py init_admin() creates admin with password 'admin123' hardcoded in source.
README publishes these credentials.

**Fix:**
  def init_admin():
      admin = db.get_user_by_username('admin')
      if not admin:
          import secrets
          temp_password = secrets.token_urlsafe(16)
          password_hash = generate_password_hash(temp_password)
          db.create_user('admin', password_hash, 'System Administrator', 'admin', 'admin@epu.edu.iq')
          print(f"[SETUP] Admin created. Temporary password: {temp_password}")
          print("[SETUP] Change this password immediately after first login.")

---

### 1.5 Add login rate limiting

**Problem:** No protection against brute-force password attacks.

**Fix — Use Flask-Limiter:**
  pip install Flask-Limiter

  # app.py
  from flask_limiter import Limiter
  from flask_limiter.util import get_remote_address
  limiter = Limiter(app, key_func=get_remote_address)

  # auth.py login route
  @auth_bp.route('/login', methods=['GET', 'POST'])
  @limiter.limit("10 per minute")
  def login():
      ...

---

## Priority 2 — Code Quality (Fix in Next Sprint)

### 2.1 Move inline SQL from blueprints into db.py

**Problem:** admin.py dashboard fetches student/subject counts using raw
get_db_connection() + cursor directly in the route function.

**Fix:** Create two functions in db.py:
  def get_total_student_count(major_id=None): ...
  def get_total_subject_count(major_id=None): ...

Then in admin.py dashboard():
  total_students = db.get_total_student_count(dept_id)
  total_subjects = db.get_total_subject_count(dept_id)

Same rule applies to any other inline SQL found in blueprints.

---

### 2.2 Fix the N+1 query in attendance_records

**Problem:** One query per attendance submission = 51 queries for 50 submissions.

**Fix:** Fetch all student-level attendance in one query, then group in Python:
  all_details = execute_query("""
      SELECT a.date, a.subject_id, a.teacher_id,
             st.id, u.full_name, a.status, a.notes
      FROM attendance a
      JOIN students st ON a.student_id = st.id
      JOIN users u ON st.user_id = u.id
      WHERE (a.date, a.subject_id) IN (
          SELECT DISTINCT date, subject_id FROM attendance
      )
      ORDER BY a.date DESC, u.full_name
  """, fetch_all=True)

  Then group by (date, subject_id, teacher_id) using a defaultdict.

---

### 2.3 Add @student_required decorator

**Problem:** Student routes manually check role instead of using a decorator.

**Fix — Add to auth.py:**
  def student_required(f):
      @wraps(f)
      def decorated_function(*args, **kwargs):
          if 'user_id' not in session:
              flash('Please log in to access this page.', 'warning')
              return redirect(url_for('auth.login'))
          if session.get('role') != 'student':
              flash('Access denied. Student account required.', 'danger')
              return redirect(url_for('auth.dashboard'))
          return f(*args, **kwargs)
      return decorated_function

Then in student.py:
  from blueprints.auth import student_required

  @student_bp.route('/student/dashboard')
  @student_required          # replaces @login_required + manual role check
  def dashboard():
      ...

---

### 2.4 Fix class name string parsing in teacher.py

**Problem:** Class name is split by ' - ' to extract year/semester/section.
Breaks silently if the format changes.

**Fix:** Update the DB query in db.py get_subjects_by_teacher() to return
year, semester, section, and shift as individual columns alongside the
display name. Then read them directly:
  year = s.get('year')
  semester = s.get('semester')
  section = s.get('section')
  shift = s.get('shift')

---

### 2.5 Remove hardcoded PostgreSQL path from db.py

**Problem:**
  _pg_bin = r"C:\Program Files\PostgreSQL\17\bin"
This is a Windows-specific path that belongs in .env, not source code.

**Fix:** Remove the block entirely, or make it .env-configurable:
  _pg_bin = os.environ.get('PG_BIN_PATH', '')
  if _pg_bin and os.path.isdir(_pg_bin):
      os.environ["PATH"] = _pg_bin + os.pathsep + os.environ.get("PATH", "")

---

## Priority 3 — Architecture (Plan for Future)

### 3.1 Split admin.py into sub-modules

admin.py at 79 KB is responsible for too many things.
Suggested split:

  blueprints/
    admin/
      __init__.py        # registers all sub-blueprints
      dashboard.py       # stats only
      users.py           # user + student + teacher CRUD
      subjects.py        # subjects + grade components
      attendance.py      # attendance records + summary
      schedule.py        # timetable builder AJAX API
      periods.py         # enrollment + exam periods
      upgrade.py         # semester upgrade logic

---

### 3.2 Adopt a migration tool

Currently: 18 manual SQL patch files with no tracking of what has been applied.

**Fix:** Add Alembic (Flask-Migrate):
  pip install Flask-Migrate

  # app.py
  from flask_migrate import Migrate
  migrate = Migrate(app, db)  # requires SQLAlchemy model layer

Or keep raw SQL but add a migrations tracking table:
  CREATE TABLE applied_migrations (
      filename VARCHAR(100) PRIMARY KEY,
      applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

---

### 3.3 Store uploaded files outside project root

**Problem:** Files are stored in /uploads/ inside the project directory.
On deployment this gets deleted on redeploy. Not compatible with multi-server setup.

**Fix:** Move upload path to an absolute path outside the project:
  UPLOAD_FOLDER = os.environ.get('UPLOAD_PATH', '/var/mis/uploads')

Or use object storage (MinIO for self-hosted, or S3-compatible).

---

## Quick Reference: Issue Severity Table

| Issue                              | Severity | Effort | Fix Location |
|------------------------------------|----------|--------|--------------|
| plain_password column + login      | Critical | Low    | auth.py, db.py, DB |
| Weak SECRET_KEY fallback           | Critical | Low    | config.py |
| No CSRF protection                 | Critical | Medium | app.py + all forms |
| Hardcoded admin123 password        | High     | Low    | app.py |
| No brute-force rate limiting       | High     | Low    | auth.py |
| N+1 attendance query               | Medium   | Medium | admin.py |
| Inline SQL in admin blueprint      | Medium   | Medium | admin.py → db.py |
| Missing @student_required          | Low      | Low    | auth.py, student.py |
| Class name string parsing          | Low      | Low    | teacher.py, db.py |
| Hardcoded Windows PG path          | Low      | Low    | db.py |
| admin.py too large                 | Low      | High   | refactor to modules |
| No migration tool                  | Low      | High   | new tooling |
| Local file storage                 | Low      | High   | infrastructure |
