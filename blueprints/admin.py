"""
Admin blueprint — all admin-facing routes, grade component management,
schedule builder API, AJAX editing endpoints, and semester upgrade.
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify)
from werkzeug.security import generate_password_hash
from datetime import datetime, date, time
import os
import re as _re
import random as _random
import db
from blueprints.auth import admin_required, superadmin_required, login_required

admin_bp = Blueprint('admin', __name__)


def _major_abbrev(major_id) -> str:
    """Return lowercase initials abbreviation for a major, e.g. 'mis', 'fa', 'ce'."""
    if not major_id:
        return 'epu'
    row = db.execute_query("SELECT name FROM majors WHERE id = %s", (major_id,), fetch_one=True)
    if not row or not row['name']:
        return 'epu'
    words = row['name'].split()
    return ''.join(w[0].lower() for w in words if w)


def _generate_epu_email(full_name: str, major_id) -> str:
    """Auto-generate EPU email: firstname_lastnameMIS######@epu.edu.iq
    Format: <name_part><major_abbrev><random6digits>@epu.edu.iq
    Random 6-digit number, collision-checked for uniqueness.
    """
    parts = full_name.lower().split()
    clean = [_re.sub(r'[^a-z0-9]', '', p) for p in parts]
    clean = [p for p in clean if p]
    if len(clean) >= 2:
        name_part = f"{clean[0]}_{clean[-1]}"
    elif clean:
        name_part = clean[0]
    else:
        name_part = "student"
    abbrev = _major_abbrev(major_id)
    # Find all existing emails with same name+abbrev prefix to avoid collision
    like_name = name_part.replace('_', '!_')
    like_pattern = f"{like_name}{abbrev}______@epu.edu.iq"
    rows = db.execute_query(
        "SELECT email FROM users WHERE email LIKE %s ESCAPE '!'",
        (like_pattern,), fetch_all=True
    ) or []
    used_numbers = set()
    for row in rows:
        m = _re.search(r'(\d{6})@epu\.edu\.iq$', row['email'])
        if m:
            used_numbers.add(m.group(1))
    # Generate a random 6-digit number not already in use
    for _ in range(100):
        num = f"{_random.randint(0, 999999):06d}"
        if num not in used_numbers:
            return f"{name_part}{abbrev}{num}@epu.edu.iq"
    # Fallback: sequential scan
    for n in range(1000000):
        num = f"{n:06d}"
        if num not in used_numbers:
            return f"{name_part}{abbrev}{num}@epu.edu.iq"
    return f"{name_part}{abbrev}000000@epu.edu.iq"


# =============================================
# ADMIN DASHBOARD
# =============================================

@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with semester statistics."""
    dept_id = session.get('major_id')
    users = db.get_all_users(dept_id) or []
    teachers = db.get_all_teachers(dept_id) or []

    conn = db.get_db_connection()
    cur = conn.cursor()
    if dept_id:
        cur.execute("SELECT COUNT(*) FROM students s JOIN users u ON s.user_id = u.id WHERE u.major_id = %s", (dept_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM students")
    row = cur.fetchone()
    total_students = row[0] if row else 0

    if dept_id:
        cur.execute("SELECT COUNT(DISTINCT s.name) FROM subjects s WHERE s.major_id = %s", (dept_id,))
    else:
        cur.execute("SELECT COUNT(DISTINCT name) FROM subjects")
    row = cur.fetchone()
    total_subjects = row[0] if row else 0
    cur.close()
    conn.close()

    semester_stats = db.get_student_counts_by_semester(dept_id)

    stats = {
        'total_users': len(users),
        'total_teachers': len(teachers),
        'total_students': total_students,
        'total_subjects': total_subjects,
        'semesters': semester_stats
    }

    return render_template('admin/dashboard.html', stats=stats)


# =============================================
# ADMIN - ATTENDANCE RECORDS
# =============================================

@admin_bp.route('/admin/attendance-records')
@admin_required
def attendance_records():
    """View all attendance records submitted by teachers."""
    conn = db.get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                a.date, s.id, s.name,
                c.id, c.name, c.shift, c.semester, c.year, c.section,
                a.teacher_id, u.full_name,
                COUNT(a.id),
                SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END),
                SUM(CASE WHEN a.status = 'absent'  THEN 1 ELSE 0 END),
                SUM(CASE WHEN a.status = 'late'    THEN 1 ELSE 0 END),
                SUM(CASE WHEN a.status = 'excused' THEN 1 ELSE 0 END),
                MAX(a.created_at)
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            JOIN students st ON a.student_id = st.id
            JOIN classes c ON st.class_id = c.id
            LEFT JOIN teachers t ON a.teacher_id = t.id
            LEFT JOIN users u ON t.user_id = u.id
            GROUP BY a.date, s.id, s.name,
                     c.id, c.name, c.shift, c.semester, c.year, c.section,
                     a.teacher_id, u.full_name
            ORDER BY a.date DESC, s.name
        """)
        rows = cur.fetchall()

        submissions = []
        for row in rows:
            submissions.append({
                'date': row[0], 'subject_id': row[1], 'subject_name': row[2],
                'class_id': row[3], 'class_name': row[4], 'shift': row[5],
                'semester': row[6], 'year': row[7], 'section': row[8],
                'teacher_id': row[9], 'teacher_name': row[10],
                'total_records': row[11], 'present_count': row[12],
                'absent_count': row[13], 'late_count': row[14],
                'excused_count': row[15], 'submitted_at': row[16]
            })

        for submission in submissions:
            cur.execute("""
                SELECT st.id, u.full_name, a.status, a.notes
                FROM attendance a
                JOIN students st ON a.student_id = st.id
                JOIN users u ON st.user_id = u.id
                WHERE a.date = %s AND a.subject_id = %s
                  AND a.teacher_id IS NOT DISTINCT FROM %s
                ORDER BY u.full_name
            """, (submission['date'], submission['subject_id'], submission['teacher_id']))
            submission['students'] = [
                {'id': r[0], 'student_name': r[1], 'status': r[2], 'notes': r[3]}
                for r in cur.fetchall()
            ]

        return render_template('admin/attendance_records.html', submissions=submissions)

    except Exception as e:
        flash(f'Error loading attendance records: {str(e)}', 'danger')
        return redirect(url_for('.dashboard'))
    finally:
        cur.close()
        conn.close()


# =============================================
# ADMIN - ATTENDANCE SUMMARY
# =============================================

@admin_bp.route('/admin/attendance-summary')
@admin_required
def attendance_summary():
    """View all students with filters + select one to see their attendance by subject."""
    conn = db.get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT DISTINCT semester FROM classes WHERE semester IS NOT NULL ORDER BY semester")
        semesters = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT shift FROM classes WHERE shift IS NOT NULL ORDER BY shift")
        shifts = [row[0] for row in cur.fetchall()]

        selected_semester = request.args.get('semester', type=int)
        selected_shift = request.args.get('shift')
        selected_section = request.args.get('section')

        query = """
            SELECT st.id, u.full_name, st.student_number,
                   c.name, c.semester, c.section, c.shift
            FROM students st
            JOIN users u ON st.user_id = u.id
            JOIN classes c ON st.class_id = c.id
        """
        params = []

        conditions = []
        if selected_semester:
            conditions.append("c.semester = %s")
            params.append(selected_semester)
        if selected_shift:
            conditions.append("c.shift = %s")
            params.append(selected_shift)
        if selected_section:
            conditions.append("c.section = %s")
            params.append(selected_section)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY u.full_name"

        cur.execute(query, params)
        students = [
            {'student_id': r[0], 'student_name': r[1], 'student_number': r[2],
             'class_name': r[3], 'semester': r[4], 'section': r[5], 'shift': r[6]}
            for r in cur.fetchall()
        ]

        sections = []
        if selected_semester or selected_shift:
            section_query = "SELECT DISTINCT section FROM classes"
            section_params = []
            section_conditions = []
            if selected_semester:
                section_conditions.append("semester = %s")
                section_params.append(selected_semester)
            if selected_shift:
                section_conditions.append("shift = %s")
                section_params.append(selected_shift)
            if section_conditions:
                section_query += " WHERE " + " AND ".join(section_conditions)
            section_query += " ORDER BY section"
            cur.execute(section_query, section_params)
            sections = [row[0] for row in cur.fetchall()]

        return render_template('admin/attendance_summary.html',
                               students=students, semesters=semesters, shifts=shifts,
                               sections=sections, selected_semester=selected_semester,
                               selected_shift=selected_shift, selected_section=selected_section)

    except Exception as e:
        flash(f'Error loading students: {str(e)}', 'danger')
        return redirect(url_for('.attendance_records'))
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/admin/api/subjects-by-semester/<int:semester>')
@admin_required
def api_subjects_by_semester(semester):
    """API: subjects for a specific semester."""
    conn = db.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, semester FROM subjects WHERE semester = %s ORDER BY name", (semester,))
        subjects = [db.row_to_dict(cur, row) for row in cur.fetchall()]
        return jsonify(subjects)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/admin/api/student-attendance/<int:student_id>/<subject_id>')
@admin_required
def api_student_attendance(student_id, subject_id):
    """API: attendance for a student in a subject (or all subjects)."""
    conn = db.get_db_connection()
    cur = conn.cursor()
    semester_filter = request.args.get('semester', type=int)

    try:
        if subject_id == 'all':
            if semester_filter:
                cur.execute("""
                    SELECT a.date, a.status, s.name, t.full_name, a.notes
                    FROM attendance a
                    JOIN subjects s ON a.subject_id = s.id
                    LEFT JOIN teachers te ON a.teacher_id = te.id
                    LEFT JOIN users t ON te.user_id = t.id
                    WHERE a.student_id = %s AND s.semester = %s
                    ORDER BY a.date DESC
                """, (student_id, semester_filter))
            else:
                cur.execute("""
                    SELECT a.date, a.status, s.name, t.full_name, a.notes
                    FROM attendance a
                    JOIN subjects s ON a.subject_id = s.id
                    LEFT JOIN teachers te ON a.teacher_id = te.id
                    LEFT JOIN users t ON te.user_id = t.id
                    WHERE a.student_id = %s
                    ORDER BY a.date DESC
                """, (student_id,))
        else:
            cur.execute("""
                SELECT a.date, a.status, s.name, t.full_name, a.notes
                FROM attendance a
                JOIN subjects s ON a.subject_id = s.id
                LEFT JOIN teachers te ON a.teacher_id = te.id
                LEFT JOIN users t ON te.user_id = t.id
                WHERE a.student_id = %s AND a.subject_id = %s
                ORDER BY a.date DESC
            """, (student_id, int(subject_id)))

        records = [
            {'date': r[0], 'status': r[1], 'subject_name': r[2], 'teacher_name': r[3], 'notes': r[4]}
            for r in cur.fetchall()
        ]

        total = len(records)
        present = sum(1 for r in records if r['status'] == 'present')
        absent = sum(1 for r in records if r['status'] == 'absent')
        late = sum(1 for r in records if r['status'] == 'late')
        excused = sum(1 for r in records if r['status'] == 'excused')

        return jsonify({
            'records': records,
            'summary': {
                'total': total, 'present': present, 'absent': absent,
                'late': late, 'excused': excused,
                'percentage': round((present / total) * 100, 1) if total > 0 else 0
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


# =============================================
# ADMIN - USER MANAGEMENT
# =============================================

@admin_bp.route('/admin/users')
@admin_required
def users():
    """Manage users."""
    all_users = db.get_all_users(session.get('major_id')) or []
    teachers_raw = db.get_all_teachers_with_subjects(session.get('major_id')) or []
    students_data = db.get_all_students_v2(session.get('major_id')) or []

    teachers_data = []
    for teacher in teachers_raw:
        teacher['subjects'] = db.get_subjects_by_teacher_id(teacher['teacher_id']) or []
        teachers_data.append(teacher)

    teacher_lookup = {t['user_id']: t for t in teachers_data}
    student_lookup = {s['user_id']: s for s in students_data}

    return render_template('admin/users.html',
                           users=all_users,
                           teacher_lookup=teacher_lookup,
                           student_lookup=student_lookup)


@admin_bp.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add new user."""
    classes = db.get_all_classes(session.get('major_id')) or []
    default_role = request.args.get('role', '')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', '')

        if not all([username, password, full_name, role]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('admin/add_user.html', classes=classes)

        email = _generate_epu_email(full_name, session.get('major_id'))

        if db.get_user_by_username(username):
            flash('Username already exists.', 'danger')
            return render_template('admin/add_user.html', classes=classes)

        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, password_hash, full_name, role, email, password, session.get('major_id'))

        if user_id:
            if role == 'teacher':
                department = request.form.get('department', '').strip()
                phone = request.form.get('phone', '').strip()
                db.create_teacher(user_id, department, phone)
            elif role == 'student':
                class_id = request.form.get('class_id')
                student_number = request.form.get('student_number', '').strip()
                phone = request.form.get('phone', '').strip()
                db.create_student(user_id, class_id if class_id else None, student_number, phone)

            flash(f'User "{username}" created successfully!', 'success')
            return redirect(url_for('.users'))
        else:
            flash('Error creating user.', 'danger')

    return render_template('admin/add_user.html', classes=classes, default_role=default_role)


@admin_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user."""
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('.users'))

    result = db.delete_user(user_id)
    flash('User deleted successfully.' if result else 'Error deleting user.', 'success' if result else 'danger')
    return redirect(url_for('.users'))


@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    """Edit user details."""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not full_name:
        flash('Full name is required.', 'warning')
        return redirect(url_for('.users'))

    result = db.update_user(user_id, full_name, email)

    if new_password:
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('.users'))
        db.update_user_password(user_id, generate_password_hash(new_password))

    flash('User updated successfully.' if result else 'Error updating user.', 'success' if result else 'danger')
    return redirect(url_for('.users'))


# =============================================
# ADMIN - TEACHER MANAGEMENT
# =============================================

@admin_bp.route('/admin/teachers')
@admin_required
def teachers():
    """View all teachers with their subjects."""
    all_teachers = db.get_all_teachers_with_subjects(session.get('major_id')) or []
    classes = db.get_distinct_student_groups() or []
    unique_subjects = db.get_unique_subjects_by_semester(session.get('major_id')) or []
    for teacher in all_teachers:
        teacher['subjects'] = db.get_subjects_by_teacher_id(teacher['teacher_id']) or []
    return render_template('admin/teachers.html',
                           teachers=all_teachers, classes=classes, unique_subjects=unique_subjects)


@admin_bp.route('/admin/teachers/<int:teacher_id>/assign-subject', methods=['POST'])
@admin_required
def assign_subject_to_teacher(teacher_id):
    """Quick assign a subject to a teacher for multiple classes."""
    subject_name = request.form.get('subject_name', '').strip()
    class_ids = request.form.getlist('class_ids')

    if not subject_name:
        flash('Please select a subject.', 'warning')
        return redirect(url_for('.teachers'))

    subjects_found = db.execute_query(
        "SELECT id, semester FROM subjects WHERE LOWER(name) = LOWER(%s)",
        (subject_name,), fetch_all=True
    ) or []

    if not subjects_found:
        flash(f'Subject "{subject_name}" not found.', 'danger')
        return redirect(url_for('.teachers'))

    if not class_ids:
        updated = 0
        for subj in subjects_found:
            db.execute_query("UPDATE subjects SET teacher_id = %s WHERE id = %s", (teacher_id, subj['id']))
            updated += 1
        flash(f'Subject "{subject_name}" assigned to teacher directly (no sections defined).' if updated else 'Error assigning subject.',
              'success' if updated else 'danger')
        return redirect(url_for('.teachers'))

    semester = subjects_found[0]['semester'] if subjects_found else None

    if semester:
        conn = db.get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM classes WHERE id = ANY(%s) AND semester != %s", (class_ids, semester))
            wrong_classes = cur.fetchall()
            cur.close()
            conn.close()
            if wrong_classes:
                flash(f'"{subject_name}" belongs to Semester {semester}. Only assign to Semester {semester} classes.', 'danger')
                return redirect(url_for('.teachers'))

    teacher_type = request.form.get('teacher_type', 'theoretical')
    success_count = 0
    for class_id in class_ids:
        subject_id = db.create_subject(subject_name, semester, major_id=session.get('major_id'))
        if subject_id:
            db.assign_teacher_to_subject(teacher_id, subject_id, class_id, teacher_type)
            success_count += 1

    flash(f'Subject "{subject_name}" assigned to {success_count} class(es) successfully!' if success_count else 'Error assigning subject.',
          'success' if success_count else 'danger')
    return redirect(url_for('.teachers'))


@admin_bp.route('/admin/teachers/unassign-subject/<int:assignment_id>', methods=['POST'])
@admin_required
def unassign_subject(assignment_id):
    """Remove a teacher assignment."""
    result = db.remove_teacher_assignment(assignment_id)
    flash('Subject unassigned successfully.' if result else 'Error unassigning subject.',
          'success' if result else 'danger')
    return redirect(url_for('.teachers'))


@admin_bp.route('/admin/teachers/unassign-subject-ajax/<int:assignment_id>', methods=['POST'])
@admin_required
def unassign_subject_ajax(assignment_id):
    """AJAX: Remove a teacher assignment."""
    result = db.remove_teacher_assignment(assignment_id)
    return jsonify({'success': True} if result is not None else {'success': False, 'error': 'Could not remove assignment'})


@admin_bp.route('/admin/teachers/unassign-subject-by-subject/<int:subject_id>', methods=['POST'])
@admin_required
def unassign_subject_by_subject(subject_id):
    """AJAX: Remove a direct teacher_id assignment from subjects table."""
    db.execute_query("UPDATE subjects SET teacher_id = NULL WHERE id = %s", (subject_id,))
    return jsonify({'success': True})


@admin_bp.route('/admin/teachers/<int:teacher_id>/assign-subject-ajax', methods=['POST'])
@admin_required
def assign_subject_ajax(teacher_id):
    """AJAX: Assign a subject to a teacher for selected student groups."""
    subject_name = request.form.get('subject_name', '').strip()
    group_keys = request.form.getlist('group_keys')

    if not subject_name:
        return jsonify({'success': False, 'error': 'Please select a subject.'}), 400

    subjects_found = db.execute_query(
        "SELECT id, semester FROM subjects WHERE LOWER(name) = LOWER(%s)",
        (subject_name,), fetch_all=True
    ) or []

    if not subjects_found:
        return jsonify({'success': False, 'error': f'Subject "{subject_name}" not found.'}), 400

    if not group_keys:
        for subj in subjects_found:
            db.execute_query("UPDATE subjects SET teacher_id = %s WHERE id = %s", (teacher_id, subj['id']))
        return jsonify({'success': True, 'count': len(subjects_found), 'assignments': []})

    teacher_type = request.form.get('teacher_type', 'theoretical')
    success_count = 0
    new_assignments = []
    for key in group_keys:
        parts = key.split('|')
        if len(parts) != 4:
            continue
        try:
            year, section, shift, semester = int(parts[0]), parts[1], parts[2], int(parts[3])
        except (ValueError, IndexError):
            continue

        class_id = db.find_or_create_class(year, semester, section, shift, session.get('major_id'))
        if not class_id:
            continue

        db.execute_query(
            """UPDATE students SET class_id = %s
               WHERE year = %s AND section = %s AND shift = %s AND semester = %s
                 AND (class_id IS NULL OR class_id != %s)""",
            (class_id, year, section, shift, semester, class_id)
        )

        subject_id = db.create_subject(subject_name, semester, major_id=session.get('major_id'))
        if not subject_id:
            continue

        assignment_id = db.assign_teacher_to_subject(teacher_id, subject_id, class_id, teacher_type)
        if assignment_id:
            success_count += 1
            new_assignments.append({
                'assignment_id': assignment_id, 'id': subject_id, 'name': subject_name,
                'year': year, 'section': section, 'shift': shift, 'semester': semester,
                'teacher_type': teacher_type,
            })

    if success_count > 0:
        return jsonify({'success': True, 'count': success_count, 'assignments': new_assignments})
    return jsonify({'success': False, 'error': 'Error assigning subject.'}), 400


# =============================================
# ADMIN - CLASS MANAGEMENT
# =============================================

@admin_bp.route('/admin/classes')
@admin_required
def classes():
    """Manage classes — shows all 4 semesters."""
    all_classes = db.get_all_classes(session.get('major_id')) or []
    class_counts, semester_totals = db.get_class_student_counts(session.get('major_id'))
    return render_template('admin/classes.html',
                           classes=all_classes, class_counts=class_counts,
                           semester_totals=semester_totals)


@admin_bp.route('/admin/semester/<int:semester>/<shift>/<section>')
@admin_required
def semester_students(semester, shift, section):
    """View students by Semester/Shift/Class."""
    students = db.get_students_by_semester(semester, shift, section) or []
    year = 1 if semester <= 2 else 2
    class_info = {'year': year, 'semester': semester, 'shift': shift, 'section': section}
    return render_template('admin/class_students.html', class_info=class_info, students=students)


@admin_bp.route('/admin/classes/add', methods=['GET', 'POST'])
@admin_required
def add_class():
    """Add new class."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        year = request.form.get('year', type=int)
        semester = request.form.get('semester', type=int)
        section = request.form.get('section', '').strip()
        shift = request.form.get('shift', '').strip()

        if not all([name, year, semester, section, shift]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('admin/add_class.html')

        if year == 1 and semester not in [1, 2]:
            flash('Year 1 can only have Semester 1 or 2.', 'danger')
            return render_template('admin/add_class.html')
        if year == 2 and semester not in [3, 4]:
            flash('Year 2 can only have Semester 3 or 4.', 'danger')
            return render_template('admin/add_class.html')

        class_id = db.create_class(name, year, semester, section, shift, description, session.get('major_id'))

        if class_id:
            flash(f'Class "{name}" created successfully!', 'success')
            return redirect(url_for('.classes'))
        else:
            flash('Error creating class. This class combination may already exist.', 'danger')

    return render_template('admin/add_class.html')


@admin_bp.route('/admin/classes/<int:class_id>/students')
@admin_required
def class_students(class_id):
    """View students in a class."""
    class_info = db.get_class_by_id(class_id)
    if not class_info:
        flash('Class not found.', 'danger')
        return redirect(url_for('.classes'))

    students = db.get_students_by_class(class_id) or []
    return render_template('admin/class_students.html', class_info=class_info, students=students)


# =============================================
# ADMIN - STUDENT MANAGEMENT
# =============================================

@admin_bp.route('/admin/students')
@admin_required
def students():
    """Manage students with filters."""
    year = request.args.get('year')
    semester = request.args.get('semester')
    shift = request.args.get('shift')
    section = request.args.get('section')

    all_students = db.get_all_students_v2(session.get('major_id')) or []

    if year:
        all_students = [s for s in all_students if s.get('year') == int(year)]
    if semester:
        all_students = [s for s in all_students if s.get('semester') == int(semester)]
    if shift:
        all_students = [s for s in all_students if s.get('shift') == shift]
    if section:
        if section == 'none':
            all_students = [s for s in all_students if not s.get('section')]
        else:
            all_students = [s for s in all_students if s.get('section') == section]

    return render_template('admin/students.html', students=all_students)


@admin_bp.route('/admin/students/assign-sections', methods=['GET', 'POST'])
@admin_required
def assign_sections():
    """Assign classes to students who don't have one."""
    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('section_') and value:
                student_id = int(key.replace('section_', ''))
                db.assign_student_section(student_id, value)
        flash('Classes assigned successfully!', 'success')
        return redirect(url_for('.students'))

    unassigned = db.get_students_without_section() or []
    grouped = {}
    for s in unassigned:
        key = f"Year {s.get('year', '?')} - {(s.get('shift') or 'unknown').title()}"
        grouped.setdefault(key, []).append(s)

    return render_template('admin/assign_sections.html', grouped_students=grouped)


@admin_bp.route('/admin/students/add', methods=['GET', 'POST'])
@admin_required
def add_student():
    """Add new student."""
    if request.method == 'POST':
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        semester = request.form.get('semester', type=int)
        shift = request.form.get('shift')
        section = request.form.get('section') or None
        phone = request.form.get('phone', '').strip() or None

        if not all([password, full_name, semester, shift]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('admin/add_student.html', major_abbrev=_major_abbrev(session.get('major_id')))

        email = _generate_epu_email(full_name, session.get('major_id'))
        year = 1 if semester <= 2 else 2

        import datetime as _dt
        current_year = _dt.datetime.now().year
        result = db.execute_query(
            "SELECT student_number FROM students WHERE student_number LIKE %s ORDER BY student_number DESC LIMIT 1",
            (f'MIS{current_year}%',), fetch_one=True
        )
        if result and result['student_number']:
            try:
                seq = int(result['student_number'][-5:]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1

        student_number = f"MIS{current_year}{seq:05d}"
        username = student_number.lower()

        if db.get_user_by_username(username):
            flash('Error generating unique student ID. Please try again.', 'danger')
            return render_template('admin/add_student.html', major_abbrev=_major_abbrev(session.get('major_id')))

        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, password_hash, full_name, 'student', email, password, session.get('major_id'))

        if user_id:
            db.create_student_with_semester(user_id, year, semester, shift, section, student_number, phone)
            flash(f'Student "{full_name}" added with ID: {student_number}!', 'success')
            return redirect(url_for('.students'))
        else:
            flash('Error creating student.', 'danger')

    return render_template('admin/add_student.html', major_abbrev=_major_abbrev(session.get('major_id')))


@admin_bp.route('/admin/students/add-ajax', methods=['POST'])
@admin_required
def add_student_ajax():
    """AJAX: Add student without page reload."""
    try:
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        semester = request.form.get('semester', type=int)
        shift = request.form.get('shift')
        section = request.form.get('section') or None
        phone = request.form.get('phone', '').strip() or None

        year = 1 if semester and semester <= 2 else 2

        if not all([password, full_name, semester, shift]):
            return jsonify({'success': False, 'message': 'Please fill in all required fields.'})

        email = _generate_epu_email(full_name, session.get('major_id'))

        import datetime as _dt
        current_year = _dt.datetime.now().year
        result = db.execute_query(
            "SELECT student_number FROM students WHERE student_number LIKE %s ORDER BY student_number DESC LIMIT 1",
            (f'MIS{current_year}%',), fetch_one=True
        )
        if result and result.get('student_number'):
            try:
                seq = int(result['student_number'][-5:]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1

        student_number = f"MIS{current_year}{seq:05d}"
        username = student_number.lower()

        if db.get_user_by_username(username):
            return jsonify({'success': False, 'message': 'Error generating unique student ID. Please try again.'})

        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, password_hash, full_name, 'student', email, password, session.get('major_id'))

        if user_id:
            db.create_student_with_semester(user_id, year, semester, shift, section, student_number, phone)
            return jsonify({
                'success': True,
                'message': f'Student "{full_name}" added with ID: {student_number}',
                'student': {
                    'name': full_name, 'student_number': student_number,
                    'email': email, 'semester': semester, 'shift': shift, 'section': section
                }
            })
        return jsonify({'success': False, 'message': 'Error creating student user account.'})
    except Exception as e:
        print(f"Error adding student: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})


@admin_bp.route('/admin/students/<int:student_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    """Edit student."""
    student = db.get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('.students'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        year = request.form.get('year')
        semester = request.form.get('semester')
        shift = request.form.get('shift')
        section = request.form.get('section') or None
        student_number = request.form.get('student_number', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not full_name or not year or not semester or not shift:
            flash('Please fill in all required fields.', 'warning')
            return render_template('admin/edit_student.html', student=student)

        db.update_student_v2(student_id, full_name, email, int(year), int(semester),
                             shift, section, student_number, phone)

        if password:
            db.execute_query("UPDATE users SET password_hash = %s WHERE id = %s",
                             (generate_password_hash(password), student['user_id']))

        flash('Student updated successfully!', 'success')
        return redirect(url_for('.students'))

    return render_template('admin/edit_student.html', student=student)


@admin_bp.route('/admin/students/<int:student_id>/edit-ajax', methods=['POST'])
@admin_required
def edit_student_ajax(student_id):
    """AJAX: Edit student."""
    student = db.get_student_by_id(student_id)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found.'})

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    year = request.form.get('year')
    semester = request.form.get('semester')
    shift = request.form.get('shift')
    section = request.form.get('section') or None
    student_number = request.form.get('student_number', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')

    if not full_name or not year or not semester or not shift:
        return jsonify({'success': False, 'message': 'Please fill in all required fields.'})

    db.update_student_v2(student_id, full_name, email, int(year), int(semester),
                         shift, section, student_number, phone)

    if password:
        db.execute_query("UPDATE users SET password_hash = %s WHERE id = %s",
                         (generate_password_hash(password), student['user_id']))

    return jsonify({
        'success': True, 'message': 'Student updated successfully!',
        'student': {
            'id': student_id, 'full_name': full_name, 'email': email,
            'year': int(year), 'semester': int(semester), 'shift': shift,
            'section': section, 'student_number': student_number, 'phone': phone
        }
    })


@admin_bp.route('/admin/students/<int:student_id>/delete', methods=['POST'])
@admin_required
def delete_student(student_id):
    """Delete student."""
    result = db.delete_student(student_id)
    flash('Student deleted successfully.' if result else 'Error deleting student.',
          'success' if result else 'danger')
    return redirect(url_for('.students'))


# =============================================
# ADMIN - SUBJECT MANAGEMENT
# =============================================

@admin_bp.route('/admin/subjects')
@admin_required
def subjects():
    """Manage subjects."""
    all_subjects = db.get_subjects_grouped_by_semester(session.get('major_id')) or []
    return render_template('admin/subjects.html', subjects=all_subjects)


@admin_bp.route('/admin/subjects/add', methods=['GET', 'POST'])
@admin_required
def add_subject():
    """Add new subject for a specific semester."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6

        if not name or not semester:
            flash('Please enter subject name and select semester.', 'warning')
            return render_template('admin/add_subject.html')

        if credits < 1 or credits > 30:
            flash('Credits must be between 1 and 30.', 'warning')
            return render_template('admin/add_subject.html')

        subject_id = db.create_subject(name, semester, description, credits, session.get('major_id'))
        if subject_id:
            flash(f'Subject "{name}" created for Semester {semester} with {credits} credits!', 'success')
            return redirect(url_for('.subjects'))
        else:
            flash('Subject already exists or error creating subject.', 'info')

    return render_template('admin/add_subject.html')


@admin_bp.route('/admin/subjects/<int:subject_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_subject(subject_id):
    """Edit subject."""
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found.', 'danger')
        return redirect(url_for('.subjects'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6

        if not name or not semester:
            flash('Please enter subject name and select semester.', 'warning')
            return render_template('admin/edit_subject.html', subject=subject)

        if credits < 1 or credits > 30:
            flash('Credits must be between 1 and 30.', 'warning')
            return render_template('admin/edit_subject.html', subject=subject)

        db.update_subject(subject_id, name, semester, description, credits)
        flash('Subject updated successfully!', 'success')
        return redirect(url_for('.subjects'))

    return render_template('admin/edit_subject.html', subject=subject)


@admin_bp.route('/admin/subjects/<int:subject_id>/delete', methods=['POST'])
@admin_required
def delete_subject(subject_id):
    """Delete subject."""
    result = db.delete_subject(subject_id)
    flash('Subject deleted successfully.' if result else 'Error deleting subject.',
          'success' if result else 'danger')
    return redirect(url_for('.subjects'))


@admin_bp.route('/admin/subjects/<int:subject_id>/toggle-results', methods=['POST'])
@admin_required
def toggle_subject_results(subject_id):
    """Toggle results publishing for a subject."""
    try:
        data = request.get_json()
        published = data.get('published', False)
        result = db.toggle_subject_results_published(subject_id, published, major_id=session.get('major_id'))
        if result:
            return jsonify({'success': True,
                            'message': f'Results {"published" if published else "unpublished"} successfully',
                            'published': published})
        return jsonify({'success': False, 'message': 'Failed to update results status'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@admin_bp.route('/admin/publish-semester-results/<int:semester>', methods=['POST'])
@admin_required
def publish_semester_results(semester):
    """Publish all subject results for an entire semester."""
    try:
        if semester not in [1, 2, 3, 4]:
            return jsonify({'success': False, 'message': 'Invalid semester'}), 400
        result = db.publish_semester_results(semester, major_id=session.get('major_id'))
        if result:
            return jsonify({'success': True,
                            'message': f'All results for Semester {semester} have been published successfully!'})
        return jsonify({'success': False, 'message': 'Failed to publish semester results'}), 500
    except Exception as e:
        print(f"Error publishing semester results: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@admin_bp.route('/admin/unpublish-semester-results/<int:semester>', methods=['POST'])
@admin_required
def unpublish_semester_results(semester):
    """Close/unpublish all subject results for an entire semester."""
    try:
        if semester not in [1, 2, 3, 4]:
            return jsonify({'success': False, 'message': 'Invalid semester'}), 400
        result = db.unpublish_semester_results(semester, major_id=session.get('major_id'))
        if result:
            return jsonify({'success': True,
                            'message': f'Results for Semester {semester} have been closed. Students can no longer view them.'})
        return jsonify({'success': False, 'message': 'Failed to close semester results'}), 500
    except Exception as e:
        print(f"Error closing semester results: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# =============================================
# ADMIN - GRADE COMPONENTS
# =============================================

@admin_bp.route('/admin/subjects/<int:subject_id>/grading')
@admin_required
def subject_grading(subject_id):
    """Manage grade distribution/rubric for a subject."""
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found!', 'danger')
        return redirect(url_for('.subjects'))

    components = db.get_grade_components_by_subject(subject_id) or []

    print(f"\n=== Loading grading page for subject {subject_id} ===")
    for comp in components:
        print(f"  [{comp['display_order']}] {comp['component_type']}: {comp['component_name']}")

    total_weight = db.get_subject_total_weight(subject_id)
    summary = db.get_grade_components_summary(subject_id) or []
    is_valid = abs(total_weight - 100.0) < 0.01

    return render_template('admin/subject_grading.html',
                           subject=subject, components=components,
                           total_weight=total_weight, is_valid=is_valid, summary=summary)


@admin_bp.route('/admin/subjects/<int:subject_id>/grading/add', methods=['POST'])
@admin_required
def add_grade_component(subject_id):
    """Add grade component(s) to subject."""
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found!', 'danger')
        return redirect(url_for('.subjects'))

    component_type = request.form.get('component_type')
    quantity = request.form.get('quantity', type=int, default=1)
    total_weight = request.form.get('weight_percentage', type=float)
    display_order = request.form.get('display_order', type=int, default=0)
    midterm_structure = request.form.get('midterm_structure', 'single')
    pair_mode = request.form.get('pair_mode', 'independent')

    # ── PAIRED REPORT+SEMINAR ─────────────────────────────────────────────────
    if component_type in ('report', 'seminar') and pair_mode == 'paired':
        paired_weight = request.form.get('weight_percentage', type=float)
        report_name = request.form.get('report_name', '').strip() or 'Report'
        seminar_name = request.form.get('seminar_name', '').strip() or 'Seminar'

        if not paired_weight or paired_weight <= 0:
            flash('Shared weight is required for paired mode!', 'danger')
            return redirect(url_for('.subject_grading', subject_id=subject_id))

        current_total = db.get_subject_total_weight(subject_id)
        if current_total + paired_weight > 100.01:
            flash(f'Cannot add! Total weight would be {current_total + paired_weight:.2f}% (max 100%)', 'danger')
            return redirect(url_for('.subject_grading', subject_id=subject_id))

        rid, sid, pg = db.add_paired_components(subject_id, report_name, seminar_name, paired_weight, display_order)
        if rid and sid:
            flash(
                f'Paired Report+Seminar added (Group {pg})! '
                f'Each scored out of {paired_weight} pts, average counts as {paired_weight}% of grade.',
                'success'
            )
        else:
            flash('Error adding paired components!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    type_names = {
        'homework': 'Homework', 'quiz': 'Quiz', 'report': 'Report', 'project': 'Project',
        'exam': 'Exam', 'midterm': 'Midterm', 'final': 'Final', 'lab_report': 'Lab Report',
        'activity': 'Activity', 'seminar': 'Seminar'
    }

    # Handle split midterm
    if component_type == 'midterm' and midterm_structure == 'split':
        practical_weight = request.form.get('practical_weight', type=float)
        theoretical_weight = request.form.get('theoretical_weight', type=float)

        if not practical_weight or not theoretical_weight:
            flash('Both practical and theoretical weights are required for split midterm!', 'danger')
            return redirect(url_for('.subject_grading', subject_id=subject_id))

        total_midterm_weight = practical_weight + theoretical_weight
        current_total = db.get_subject_total_weight(subject_id)
        if current_total + total_midterm_weight > 100.01:
            flash(f'Cannot add! Total weight would be {current_total + total_midterm_weight:.2f}% (max 100%)', 'danger')
            return redirect(url_for('.subject_grading', subject_id=subject_id))

        pid = db.add_grade_component(subject_id, 'midterm', 'Midterm Practical',
                                     practical_weight, practical_weight, display_order)
        tid = db.add_grade_component(subject_id, 'midterm', 'Midterm Theoretical',
                                     theoretical_weight, theoretical_weight, display_order + 1)

        if pid and tid:
            flash(f'Midterm split added! Practical: {practical_weight}% ({practical_weight} pts), '
                  f'Theoretical: {theoretical_weight}% ({theoretical_weight} pts)', 'success')
        else:
            flash('Error adding split midterm!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    if not all([component_type, total_weight is not None]):
        flash('All fields are required!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    if component_type != 'midterm' or midterm_structure == 'single':
        if quantity < 1 or quantity > 20:
            flash('Quantity must be between 1 and 20!', 'danger')
            return redirect(url_for('.subject_grading', subject_id=subject_id))

    if total_weight < 0 or total_weight > 100:
        flash('Weight percentage must be between 0 and 100!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    current_total = db.get_subject_total_weight(subject_id)
    if current_total + total_weight > 100.01:
        flash(f'Cannot add! Total weight would be {current_total + total_weight:.2f}% (max 100%)', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    existing_count = db.get_component_count_by_type(subject_id, component_type)
    max_scores = [total_weight] * quantity

    from decimal import Decimal, ROUND_HALF_UP
    total_decimal = Decimal(str(total_weight))
    quantity_decimal = Decimal(str(quantity))
    individual_weight = total_decimal / quantity_decimal

    weights = []
    running_total = Decimal('0')
    for i in range(quantity - 1):
        weight = individual_weight.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        weights.append(float(weight))
        running_total += weight
    weights.append(float(total_decimal - running_total))

    actual_total = sum(weights)
    if abs(actual_total - total_weight) > 0.001:
        flash(f'ERROR: Weight calculation mismatch! Expected {total_weight}%, got {actual_total}%.', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    added_count = 0
    type_display = type_names.get(component_type, component_type.title())

    for i in range(quantity):
        component_number = existing_count + i + 1
        component_name = type_display if quantity == 1 else f"{type_display} {component_number}"
        component_id = db.add_grade_component(
            subject_id, component_type, component_name,
            max_scores[i], weights[i], display_order + i
        )
        if component_id:
            added_count += 1

    if added_count == quantity:
        if quantity == 1:
            flash(f'Component "{type_display}" added! Weight: {total_weight}%, Max Score: {total_weight} pts', 'success')
        else:
            flash(f'{quantity} {type_display} components added! Total: {total_weight}%, Each max: {total_weight} pts.', 'success')
    else:
        flash(f'Error: Only {added_count} of {quantity} components were added!', 'warning')

    return redirect(url_for('.subject_grading', subject_id=subject_id))


@admin_bp.route('/admin/subjects/<int:subject_id>/grading/<int:component_id>/delete', methods=['POST'])
@admin_required
def delete_grade_component(subject_id, component_id):
    """Delete a grade component."""
    result = db.delete_grade_component(component_id)
    flash('Component deleted successfully!' if result else 'Error deleting component!',
          'success' if result else 'danger')
    return redirect(url_for('.subject_grading', subject_id=subject_id))


@admin_bp.route('/admin/subjects/<int:subject_id>/grading/<int:component_id>/edit', methods=['POST'])
@admin_required
def edit_grade_component(subject_id, component_id):
    """Edit a grade component."""
    component_type = request.form.get('component_type')
    component_name = request.form.get('component_name', '').strip()
    max_score = request.form.get('max_score', type=float)
    weight_percentage = request.form.get('weight_percentage', type=float)
    display_order = request.form.get('display_order', type=int, default=0)

    if not all([component_type, component_name, max_score, weight_percentage is not None]):
        flash('All fields are required!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    result = db.update_grade_component(component_id, component_type, component_name,
                                       max_score, weight_percentage, display_order)
    flash('Component updated successfully!' if result else 'Error updating component!',
          'success' if result else 'danger')
    return redirect(url_for('.subject_grading', subject_id=subject_id))


@admin_bp.route('/admin/subjects/<int:subject_id>/grading/delete-category/<component_type>', methods=['POST'])
@admin_required
def delete_grade_category(subject_id, component_type):
    """Delete all components of a specific type."""
    result = db.delete_grade_components_by_type(subject_id, component_type)
    type_names = {
        'homework': 'Homework', 'quiz': 'Quiz', 'report': 'Report', 'project': 'Project',
        'exam': 'Exam', 'midterm': 'Midterm', 'final': 'Final', 'lab_report': 'Lab Report',
        'activity': 'Activity', 'seminar': 'Seminar'
    }
    type_display = type_names.get(component_type, component_type.title())
    if result and len(result) > 0:
        flash(f'&#10003; All {type_display} components deleted successfully! ({len(result)} items removed)', 'success')
    else:
        flash(f'No {type_display} components found to delete!', 'warning')
    return redirect(url_for('.subject_grading', subject_id=subject_id))


@admin_bp.route('/admin/subjects/<int:subject_id>/grading/edit-category/<component_type>', methods=['POST'])
@admin_required
def edit_grade_category(subject_id, component_type):
    """Edit total weight for all components of a specific type."""
    new_total_weight = request.form.get('new_total_weight', type=float)

    if not new_total_weight or new_total_weight < 0:
        flash('Invalid weight value!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    components = db.get_grade_components_by_subject(subject_id)
    other_weight = float(sum(c['weight_percentage'] for c in components if c['component_type'] != component_type))

    if other_weight + new_total_weight > 100.01:
        flash(f'Cannot update! Total would be {other_weight + new_total_weight:.2f}% (max 100%)', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    result = db.update_grade_components_by_type(subject_id, component_type, new_total_weight)

    type_names = {
        'homework': 'Homework', 'quiz': 'Quiz', 'report': 'Report', 'project': 'Project',
        'exam': 'Exam', 'midterm': 'Midterm', 'final': 'Final', 'lab_report': 'Lab Report',
        'activity': 'Activity', 'seminar': 'Seminar'
    }
    type_display = type_names.get(component_type, component_type.title())
    flash(f'{type_display} category updated! New total: {new_total_weight}%' if result else f'Error updating {type_display} category!',
          'success' if result else 'danger')
    return redirect(url_for('.subject_grading', subject_id=subject_id))


@admin_bp.route('/admin/subjects/<int:subject_id>/grading/reorder', methods=['POST'])
@admin_required
def reorder_grade_components(subject_id):
    """Update display order for component categories."""
    category_order = request.form.get('category_order')

    if not category_order:
        flash('No order data received!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    categories = [c.strip() for c in category_order.split(',') if c.strip()]
    if not categories:
        flash('Invalid order data!', 'danger')
        return redirect(url_for('.subject_grading', subject_id=subject_id))

    print(f"Reordering categories for subject {subject_id}: {categories}")
    result = db.reorder_categories_by_type(subject_id, categories)

    flash(f'Successfully reordered {len(categories)} categories!' if result else 'Failed to update category order!',
          'success' if result else 'danger')
    return redirect(url_for('.subject_grading', subject_id=subject_id))


# =============================================
# ADMIN - ENROLLMENT PERIODS
# =============================================

@admin_bp.route('/admin/enrollment-periods')
@admin_required
def enrollment_periods():
    """Manage enrollment and exam periods (combined)."""
    now = datetime.now()
    active_tab = request.args.get('tab', 'enrollment')
    major_id = session.get('major_id')

    enroll_periods = db.get_all_enrollment_periods(major_id=major_id)
    for p in enroll_periods:
        p['is_active'] = p['start_date'] <= now <= p['end_date']
        p['is_upcoming'] = p['start_date'] > now

    exam_periods = db.get_all_exam_periods(major_id=major_id)
    for p in exam_periods:
        p['is_active'] = p['start_date'] <= now <= p['end_date']
        p['is_upcoming'] = p['start_date'] > now

    return render_template('admin/enrollment_periods.html',
                           enroll_periods=enroll_periods,
                           exam_periods=exam_periods,
                           active_tab=active_tab)


@admin_bp.route('/admin/enrollment-periods/add', methods=['POST'])
@admin_required
def add_enrollment_period():
    """Create a new enrollment period."""
    semester = request.form.get('semester', type=int)
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    description = request.form.get('description', '')

    if not all([semester, start_date, end_date]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400

    try:
        # Handle both standard date 'YYYY-MM-DD' and datetime 'YYYY-MM-DDTHH:MM' 
        if 'T' in start_date:
            start_dt = datetime.fromisoformat(start_date)
            start_day = start_dt.date()
        else:
            start_day = date.fromisoformat(start_date)
            start_dt = datetime.combine(start_day, time(0, 0, 0))
            
        if 'T' in end_date:
            end_dt = datetime.fromisoformat(end_date)
            end_day = end_dt.date()
        else:
            end_day = date.fromisoformat(end_date)
            end_dt = datetime.combine(end_day, time(23, 59, 59))

        if end_dt < start_dt:
            return jsonify({'success': False, 'error': 'End time must be on or after start time'}), 400

        result = db.create_enrollment_period(semester, start_dt, end_dt, description, session['user_id'])
        if result:
            return jsonify({'success': True, 'message': 'Enrollment period created successfully'})
        return jsonify({'success': False, 'error': 'Failed to create enrollment period'}), 500
    except Exception as e:
        print(f"Error creating enrollment period: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/enrollment-periods/<int:period_id>/delete', methods=['POST'])
@admin_required
def delete_enrollment_period(period_id):
    """Delete an enrollment period."""
    try:
        db.delete_enrollment_period(period_id)
        return jsonify({'success': True, 'message': 'Enrollment period deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================
# ADMIN - EXAM PERIODS
# =============================================

@admin_bp.route('/admin/exam-periods')
@admin_required
def exam_periods():
    """Redirect to combined period management page (exams tab)."""
    return redirect(url_for('.enrollment_periods', tab='exams'))


@admin_bp.route('/admin/exam-periods/add', methods=['POST'])
@admin_required
def add_exam_period():
    """Create a new exam period."""
    semester = request.form.get('semester', type=int)
    period_type = request.form.get('period_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    description = request.form.get('description', '')

    if not all([semester, period_type, start_date, end_date]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400

    if period_type not in ('final', 'second_round'):
        return jsonify({'success': False, 'error': 'Invalid period type'}), 400

    try:
        if 'T' in start_date:
            start_dt = datetime.fromisoformat(start_date)
            start_day = start_dt.date()
        else:
            start_day = date.fromisoformat(start_date)
            start_dt = datetime.combine(start_day, time(0, 0, 0))

        if 'T' in end_date:
            end_dt = datetime.fromisoformat(end_date)
            end_day = end_dt.date()
        else:
            end_day = date.fromisoformat(end_date)
            end_dt = datetime.combine(end_day, time(23, 59, 59))

        if end_dt < start_dt:
            return jsonify({'success': False, 'error': 'End time must be on or after start time'}), 400

        result = db.create_exam_period(semester, period_type, start_dt, end_dt, description, session['user_id'])
        if result:
            return jsonify({'success': True, 'message': 'Exam period created successfully'})
        return jsonify({'success': False, 'error': 'Failed to create exam period'}), 500
    except Exception as e:
        print(f"Error creating exam period: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/exam-periods/<int:period_id>/delete', methods=['POST'])
@admin_required
def delete_exam_period(period_id):
    """Delete an exam period."""
    try:
        db.delete_exam_period(period_id)
        return jsonify({'success': True, 'message': 'Exam period deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================
# ADMIN - SCHEDULE BUILDER API
# =============================================

@admin_bp.route('/admin/api/schedule/<int:semester>/<shift>/<section>', methods=['GET'])
@admin_required
def api_get_schedule(semester, shift, section):
    """API: Get schedule for a semester/shift/section."""
    import json
    major_id = session.get('major_id')
    schedule = db.get_schedule(semester, shift, section, major_id=major_id)
    if schedule and schedule.get('schedule_data'):
        data = schedule['schedule_data']
        if isinstance(data, (list, dict)):
            return {'success': True, 'data': data}
        return {'success': True, 'data': json.loads(data)}
    return {'success': True, 'data': []}


@admin_bp.route('/admin/api/schedule/<int:semester>/<shift>/<section>', methods=['POST'])
@admin_required
def api_save_schedule(semester, shift, section):
    """API: Save schedule."""
    import json
    major_id = session.get('major_id')
    data = request.get_json()
    schedule_data = data.get('schedule_data', [])
    result = db.save_schedule(semester, shift, section, json.dumps(schedule_data), major_id=major_id)
    if result:
        return {'success': True, 'message': 'Schedule saved successfully!'}
    return {'success': False, 'message': 'Error saving schedule'}, 500


# =============================================
# SUPERADMIN - MAJORS MANAGEMENT
# Only the superadmin (admin@epu.edu.iq, no major) can view
# and create admin accounts for each of the 72 majors.
# =============================================

@admin_bp.route('/admin/majors')
@superadmin_required
def majors():
    """List all 72 majors with admin status (superadmin only)."""
    all_majors = db.get_majors_with_admin_status() or []
    # Group by college for display
    colleges = {}
    for m in all_majors:
        college = m.get('college_name') or 'Unassigned'
        colleges.setdefault(college, []).append(m)
    return render_template('admin/majors.html', colleges=colleges, all_majors=all_majors)


@admin_bp.route('/admin/majors/<int:major_id>/add-admin', methods=['GET', 'POST'])
@superadmin_required
def add_major_admin(major_id):
    """Create an admin user for the given major (superadmin only)."""
    major = db.get_major_by_id(major_id)
    if not major:
        flash('Major not found.', 'danger')
        return redirect(url_for('.majors'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        current_admins = db.execute_query(
            "SELECT full_name, email FROM users WHERE major_id = %s AND role = 'admin' ORDER BY full_name",
            (major_id,), fetch_all=True) or []

        if not all([full_name, email, password]):
            flash('All fields are required.', 'warning')
            return render_template('admin/add_major_admin.html', major=major, current_admins=current_admins)

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('admin/add_major_admin.html', major=major, current_admins=current_admins)

        if db.get_user_by_email(email):
            flash(f'An account with email "{email}" already exists.', 'danger')
            return render_template('admin/add_major_admin.html', major=major, current_admins=current_admins)

        username = email.split('@')[0]
        if db.get_user_by_username(username):
            username = f"admin.{major['code']}"

        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, password_hash, full_name, 'admin', email, password, major_id)
        if user_id:
            flash(f'Admin "{full_name}" created for {major["name"]} successfully!', 'success')
            return redirect(url_for('.majors'))
        else:
            flash('Error creating admin account.', 'danger')

    current_admins = db.execute_query(
        "SELECT full_name, email FROM users WHERE major_id = %s AND role = 'admin' ORDER BY full_name",
        (major_id,), fetch_all=True) or []
    return render_template('admin/add_major_admin.html', major=major, current_admins=current_admins)


@admin_bp.route('/admin/api/schedule/<int:semester>/<shift>/<section>/auto-generate', methods=['POST'])
@admin_required
def api_auto_generate_schedule(semester, shift, section):
    """API: Auto-generate a sample schedule from existing subject/teacher data."""
    import json

    rows = db.execute_query("""
        SELECT DISTINCT s.id, s.name,
               u.full_name AS teacher
        FROM subjects s
        LEFT JOIN teacher_assignments ta
            ON ta.subject_id = s.id
            AND ta.class_id IN (
                SELECT id FROM classes
                WHERE semester = %s AND shift = %s AND section = %s
            )
        LEFT JOIN teachers t ON ta.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE s.semester = %s
        ORDER BY s.name
    """, (semester, shift, section, semester), fetch_all=True) or []

    if rows:
        seen, subjects = set(), []
        for r in rows:
            if r['name'] not in seen:
                seen.add(r['name'])
                subjects.append({'name': r['name'], 'teacher': r['teacher'] or ''})
    else:
        return jsonify({'success': False, 'error': 'No subjects found for this semester'}), 400

    if not subjects:
        return jsonify({'success': False, 'error': 'No subjects found for this semester'}), 400

    time_slots = [
        ('8:00', '9:00'), ('9:00', '10:00'), ('10:00', '11:00'), ('11:00', '12:00'),
        ('12:00', '13:00'), ('13:00', '14:00'), ('14:00', '15:00'),
    ]
    days = 5
    preferred_rows = [0, 2, 4]
    slots = [(row, col) for row in preferred_rows for col in range(days)]

    schedule = []
    occupied = set()
    slot_idx = 0
    times_per_subject = 2
    for i, subj in enumerate(subjects):
        count = 0
        while count < times_per_subject and slot_idx < len(slots):
            row, col = slots[slot_idx]
            slot_idx += 1
            if (row, col) in occupied:
                continue
            occupied.add((row, col))
            start, end = time_slots[row]
            schedule.append({
                'row': row, 'col': col, 'rowSpan': 1, 'colSpan': 1,
                'startTime': start, 'endTime': end,
                'theoryStartTime': start, 'theoryEndTime': end,
                'practicalStartTime': '', 'practicalEndTime': '',
                'subject': subj['name'], 'teacher': subj['teacher'],
                'practicalTeacher': '', 'lectureType': 'theory', 'room': '',
            })
            count += 1

    db.save_schedule(semester, shift, section, json.dumps(schedule), major_id=session.get('major_id'))
    return jsonify({'success': True, 'data': schedule})


@admin_bp.route('/admin/api/teachers-subjects/<int:semester>')
@admin_required
def api_get_teachers_subjects_by_semester(semester):
    """API: subjects for this semester + their teacher assignments."""
    conn = db.get_db_connection()
    if not conn:
        return {'subjects': [], 'assignments': []}

    cur = conn.cursor()
    try:
        major_id = session.get('major_id')
        cur.execute(
            "SELECT id, name, description FROM subjects WHERE semester = %s AND major_id = %s ORDER BY name",
            (semester, major_id)
        )
        sem_subjects = cur.fetchall()

        subject_list = [{'id': r[0], 'name': r[1], 'description': r[2] or ''} for r in sem_subjects]
        subject_ids = [s[0] for s in sem_subjects]
        assignment_list = []

        if subject_ids:
            cur.execute("""
                SELECT ta.id, ta.subject_id, s.name, ta.shift, t.id, u.full_name
                FROM teacher_assignments ta
                JOIN subjects s ON ta.subject_id = s.id
                JOIN teachers t ON ta.teacher_id = t.id
                JOIN users u ON t.user_id = u.id
                WHERE ta.subject_id = ANY(%s)
                ORDER BY s.name, ta.shift
            """, (subject_ids,))
            for row in cur.fetchall():
                for section in ['A', 'B', 'C']:
                    assignment_list.append({
                        'assignment_id': row[0], 'subject_id': row[1], 'subject_name': row[2],
                        'shift': row[3] or '', 'section': section,
                        'teacher_id': row[4], 'teacher_name': row[5] or ''
                    })

        return {'subjects': subject_list, 'assignments': assignment_list}
    except Exception as e:
        print(f"ERROR in api_get_teachers_subjects_by_semester: {e}")
        import traceback; traceback.print_exc()
        return {'subjects': [], 'assignments': [], 'error': str(e)}
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/admin/api/teachers-subjects')
@admin_required
def api_get_teachers_subjects():
    """API: all teachers and subjects for schedule dropdown."""
    teachers = db.get_all_teachers(session.get('major_id')) or []
    all_subjects = db.get_all_subjects(session.get('major_id')) or []
    return {
        'teachers': [{'id': t['id'], 'name': t['full_name']} for t in teachers],
        'subjects': [{
            'id': s['id'], 'name': s['name'], 'semester': s.get('semester'),
            'year': s.get('year'), 'teacher_name': s.get('teacher_name'),
            'practical_teacher_name': s.get('practical_teacher_name')
        } for s in all_subjects]
    }


# =============================================
# AJAX ROUTES
# =============================================

@admin_bp.route('/admin/users/<int:user_id>/edit-ajax', methods=['POST'])
@admin_required
def edit_user_ajax(user_id):
    """Edit user via AJAX."""
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '').strip()
    new_password = request.form.get('new_password', '')

    if not username or not full_name or not role:
        return jsonify({'success': False, 'message': 'Username, full name, and role are required.'})

    current_user = db.get_user_by_id(user_id)
    if current_user and username != current_user['username']:
        if db.get_user_by_username(username):
            return jsonify({'success': False, 'message': 'Username already exists.'})

    if new_password and len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long.'})

    result = db.update_user_complete(user_id, username, full_name, email, role)

    plain_pass = None
    if new_password:
        plain_pass = new_password
        password_result = db.update_user_password(user_id, generate_password_hash(new_password), plain_pass)
        if password_result is None:
            return jsonify({'success': False, 'message': 'Error updating password.'})

    if result is not None:
        return jsonify({
            'success': True,
            'message': 'User updated successfully!' + (' Password changed.' if new_password else ''),
            'user': {
                'id': user_id, 'username': username, 'full_name': full_name,
                'email': email, 'role': role,
                'plain_password': plain_pass if plain_pass else None
            }
        })
    return jsonify({'success': False, 'message': 'Error updating user.'})


@admin_bp.route('/admin/users/add-ajax', methods=['POST'])
@admin_required
def add_user_ajax():
    """Add user via AJAX."""
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '').strip()
    password = request.form.get('password', '')

    if not username or not full_name or not role or not password:
        return jsonify({'success': False, 'message': 'Please fill in all required fields.'})

    if db.get_user_by_username(username):
        return jsonify({'success': False, 'message': 'Username already exists.'})

    user_id = db.create_user(username, generate_password_hash(password), full_name, role, email, password, session.get('major_id'))

    if user_id:
        if role == 'teacher':
            db.create_teacher(user_id)

        new_user = db.get_user_by_id(user_id)
        if new_user:
            user_data = {
                'id': new_user['id'], 'username': new_user['username'],
                'full_name': new_user['full_name'], 'email': new_user.get('email'),
                'role': new_user['role'], 'plain_password': new_user.get('plain_password'),
                'year': None, 'semester': None, 'shift': None, 'section': None, 'subjects': None
            }
            if role == 'teacher':
                teacher = db.get_teacher_by_user_id(user_id)
                if teacher:
                    subjects = db.get_subjects_by_teacher_id(teacher['id'])
                    user_data['subjects'] = ','.join([str(s['id']) for s in subjects]) if subjects else None
                    user_data['sections'] = ''
            elif role == 'student':
                student = db.get_student_by_user_id(user_id)
                if student:
                    user_data.update({
                        'year': student.get('year'), 'semester': student.get('semester'),
                        'shift': student.get('shift'), 'section': student.get('section')
                    })
            return jsonify({'success': True, 'message': 'User created successfully!', 'user': user_data})

    return jsonify({'success': False, 'message': 'Error creating user.'})


@admin_bp.route('/admin/subjects/<int:subject_id>/edit-ajax', methods=['POST'])
@admin_required
def edit_subject_ajax(subject_id):
    """Edit subject via AJAX."""
    try:
        name = request.form.get('name', '').strip()
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6

        if not name or not semester:
            return jsonify({'success': False, 'message': 'Please enter subject name and select semester.'})

        if credits < 1 or credits > 30:
            return jsonify({'success': False, 'message': 'Credits must be between 1 and 30.'})

        result = db.update_subject(subject_id, name, semester, description, credits)
        if result is not None:
            return jsonify({'success': True, 'message': 'Subject updated successfully!',
                            'subject': {'id': subject_id, 'name': name}})
        return jsonify({'success': False, 'message': 'Error updating subject.'})
    except Exception as e:
        print(f'Error in edit_subject_ajax: {e}')
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@admin_bp.route('/admin/subjects/add-ajax', methods=['POST'])
@admin_required
def add_subject_ajax():
    """Add subject via AJAX."""
    try:
        name = request.form.get('name', '').strip()
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6

        if not name or not semester:
            return jsonify({'success': False, 'message': 'Please enter subject name and select semester.'})

        if credits < 1 or credits > 30:
            return jsonify({'success': False, 'message': 'Credits must be between 1 and 30.'})

        result = db.create_subject(name, semester, description, credits, session.get('major_id'))
        if result:
            return jsonify({'success': True, 'message': 'Subject created successfully!'})
        return jsonify({'success': False, 'message': 'Subject already exists or error creating subject.'})
    except Exception as e:
        print(f'Error in add_subject_ajax: {e}')
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


# =============================================
# ADMIN - SEMESTER UPGRADE
# =============================================

@admin_bp.route('/admin/upgrade/preview/<int:semester>')
@admin_required
def upgrade_preview(semester):
    """Show pass/fail preview for a semester before upgrading."""
    if semester < 1 or semester > 4:
        flash('Invalid semester.', 'danger')
        return redirect(url_for('.dashboard'))

    db.ensure_upgrade_tables()
    preview = db.get_semester_upgrade_preview(semester, major_id=session.get('major_id'))
    return render_template('admin/upgrade_preview.html', preview=preview, semester=semester)


@admin_bp.route('/admin/upgrade/execute/<int:semester>', methods=['POST'])
@admin_required
def upgrade_execute(semester):
    """Promote passing students."""
    if semester < 1 or semester > 4:
        flash('Invalid semester.', 'danger')
        return redirect(url_for('.dashboard'))

    db.ensure_upgrade_tables()

    try:
        result = db.execute_semester_upgrade(semester, session['user_id'], major_id=session.get('major_id'))
        if semester >= 4:
            flash(f'Semester {semester} upgrade complete: {result["graduated"]} graduated, {result["failed"]} failed.', 'success')
        else:
            flash(f'Semester {semester} upgrade complete: {result["promoted"]} promoted to Semester {semester + 1}, {result["failed"]} failed.', 'success')
    except Exception as e:
        print(f'Error executing upgrade: {e}')
        flash(f'Error during upgrade: {str(e)}', 'danger')

    return redirect(url_for('.dashboard'))
