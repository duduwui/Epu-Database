# MIS Project — GitHub Copilot Workspace Instructions

This is a **Flask-based Management Information System (MIS)** for a university/college.
Always read and follow these conventions before generating or editing any code.

---

## Tech Stack

| Layer    | Technology                                                             |
| -------- | ---------------------------------------------------------------------- |
| Backend  | Python 3.13.6, Flask 3.0.0, Jinja2                                     |
| Database | PostgreSQL 17, psycopg (psycopg3) — driver uses `%s` placeholders      |
| Frontend | Bootstrap 5.3.2 + Bootstrap Icons (`bi bi-*`)                          |
| Auth     | `werkzeug.security` — `generate_password_hash` / `check_password_hash` |
| Sessions | Flask `session` dict                                                   |

---

## Project Structure

```
app.py          — Main application and Flask routing initialization (Blueprints)
blueprints/     — Organized Flask Blueprints (admin.py, auth.py, student.py, teacher.py)
db.py           — All database functions (NO SQL in app.py or templates)
config.py       — DB connection config (reads from env vars)
templates/
  base.html     — Base layout with Bootstrap 5.3.2
  admin/        — Admin-only templates
  teacher/      — Teacher-only templates
  student/      — Student-only templates
static/css/style.css
database/       — SQL migration files (*.sql)
```

---

## User Roles & Auth Decorators

Three roles: `admin`, `teacher`, `student`.
Route decorators defined in `app.py`:

- `@admin_required` — only admins
- `@teacher_required` — only teachers
- `@student_required` — only students

Always apply the correct decorator. Never serve one role's data to another.

---

## Database Layer Rules (db.py)

- **All DB access goes through `db.py`**. No raw SQL in `app.py` or templates.
- **Always use parameterized queries** — never string-format user input into SQL.
  ```python
  # CORRECT
  execute_query("SELECT * FROM users WHERE id = %s", (user_id,), fetch_one=True)
  # WRONG — never do this
  execute_query(f"SELECT * FROM users WHERE id = {user_id}")
  ```
- The helper is `execute_query(query, params=None, fetch_one=False, fetch_all=False)`.
- Functions return `dict`-like rows (psycopg `Row` objects accessible by column name).
- Return `None` or `[]` on failure — callers use `or []` / `or {}` defensively.

### Key DB Functions

| Function                             | Purpose                                                         |
| ------------------------------------ | --------------------------------------------------------------- |
| `get_all_users()`                    | All users                                                       |
| `get_subjects_grouped_by_semester()` | Returns `total_weight`, `component_count` per subject           |
| `_calc_grade_totals(rows)`           | **Canonical** pair-aware grade calculator — use this everywhere |
| `add_paired_components(...)`         | Creates Report + Seminar pair with shared `pair_group`          |
| `get_next_pair_group(subject_id)`    | Next available pair group integer                               |

---

## Grade System

- `grade_components` table has a `pair_group INTEGER NULL` column.
- Paired components (Report + Seminar) share the same `pair_group` value.
- `_calc_grade_totals(rows)` handles pairing: averages paired scores, sums non-paired.
- **Always use `_calc_grade_totals()`** for final grade calculation — never re-implement manually.
- `get_subject_total_weight()` uses ROW_NUMBER to count paired components as 1× weight.

---

## Flask Routes (Blueprints)

- Routes are organized into Blueprints under the `blueprints/` directory (e.g., `admin.py`, `student.py`, `teacher.py`, `auth.py`).
- Route functions call `db.*` functions — no business logic in templates.
- Flash messages use Bootstrap alert categories: `success`, `danger`, `warning`, `info`.
- JSON responses use `jsonify({"success": True/False, "message": "..."})`.
- File uploads stored under `uploads/` — always validate file type and sanitize filename with `secure_filename`.

---

## Frontend Conventions (Templates)

### Bootstrap Usage

- Use Bootstrap 5.3.2 classes. No custom CSS unless absolutely necessary.
- Form inputs: use `form-control form-control-sm` and `form-select form-select-sm` for compact forms.
- Spacing: prefer `mb-2` over `mb-3` in compact card forms.
- Buttons: `btn btn-sm` in tables/cards.
- Tooltips: `data-bs-toggle="tooltip" data-bs-placement="top"` — always initialize with:
  ```js
  document
    .querySelectorAll('[data-bs-toggle="tooltip"]')
    .forEach((el) => new bootstrap.Tooltip(el));
  ```

### Brand Colors

- Primary brand: `#1C0770` (EPU deep purple)
- Use `style="background: #1C0770;"` or `style="background: linear-gradient(135deg, #1C0770 0%, #150558 100%)"` for headers.
- Class `text-navy` maps to `#1C0770`.

### HTML Entities in Jinja Templates

- Always use HTML entities for symbols — never paste Unicode emoji directly.
  - Checkmark: `&#10003;` (✓)
  - Warning: `&#9888;` (⚠)
  - Middle dot: `&middot;`

### Jinja2 Syntax

- Equality comparison: `{% if var == "value" %}` — **never** `{% if var="value" %}`
- Filter chain example: `users | selectattr('role', 'equalto', 'admin') | list | length`

---

## Security Rules (OWASP-aligned)

1. **SQL Injection** — always parameterized queries (`%s`), no exceptions.
2. **XSS** — Jinja2 auto-escapes by default; never use `| safe` on user-provided data.
3. **Access Control** — every route has `@admin_required` / `@teacher_required` / `@student_required`; never skip.
4. **Passwords** — `generate_password_hash` for storage, `check_password_hash` for verification; never store plain text (except in `plain_password` field for admin reset purposes).
5. **File Uploads** — always `secure_filename()`; validate MIME type; store outside web root or under `uploads/`.
6. **Secrets** — DB credentials in `config.py` read from env vars or local config; never hardcode.
7. **Debug mode** — `app.run(debug=True)` only in development; use env-flag check in production.

---

## Python Style

- Follow PEP 8. 4-space indentation. Max line length ~100 chars (this project's convention).
- Type hints encouraged for new functions.
- Descriptive function/variable names.
- DB functions: one responsibility per function.
- No bare `except:` — catch specific exceptions or at minimum `except Exception as e`.

---

## Common Patterns

### Adding a new admin route

```python
@app.route('/admin/something', methods=['GET', 'POST'])
@admin_required
def admin_something():
    data = db.get_something() or []
    return render_template('admin/something.html', data=data)
```

### DB function template

```python
def get_something(param):
    query = """
        SELECT col1, col2
        FROM table
        WHERE id = %s
    """
    return execute_query(query, (param,), fetch_all=True)
```

### Bootstrap tooltip on a button (Jinja)

```html
<a
  href="..."
  class="btn btn-sm btn-outline-primary"
  data-bs-toggle="tooltip"
  data-bs-placement="top"
  title="Your tooltip text"
>
  <i class="bi bi-icon-name"></i>
</a>
```
