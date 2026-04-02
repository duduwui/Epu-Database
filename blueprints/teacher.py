"""
Teacher blueprint — teacher routes, weekly topics, schedule, homework, files,
and shared file/homework download routes (teachers + students both use them).
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, send_from_directory, current_app)
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import db
from blueprints.auth import teacher_required, login_required

teacher_bp = Blueprint('teacher', __name__)


# =============================================
# TEACHER - DASHBOARD
# =============================================

@teacher_bp.route('/teacher/dashboard')
@teacher_required
def dashboard():
    """Teacher dashboard."""
    teacher = db.get_teacher_by_user_id(session['user_id'])

    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    homework = db.get_homework_by_teacher(teacher['id']) or []

    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'count': 0, 'classes': [], 'credits': s.get('credits', 6)}
        grouped_subjects[name]['count'] += 1
        grouped_subjects[name]['classes'].append({
            'subject_id': s['id'],
            'class_id': s.get('class_id'),
            'section': s.get('section', ''),
            'semester': s.get('semester', ''),
            'shift': s.get('shift', 'morning'),
        })

    return render_template('teacher/dashboard.html',
                           teacher=teacher,
                           subjects=subjects,
                           grouped_subjects=grouped_subjects,
                           homework=homework)


# =============================================
# TEACHER - ATTENDANCE
# =============================================

@teacher_bp.route('/teacher/attendance')
@teacher_required
def attendance():
    """Attendance management page — grouped by subject name."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []

    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'classes': []}

        class_name = s.get('class_name', '')
        parts = class_name.split(' - ')
        year = parts[0].replace('Year ', '') if len(parts) > 0 else '?'
        semester = parts[1].replace('Sem ', '') if len(parts) > 1 else '?'
        section = parts[2].replace('Section ', '') if len(parts) > 2 else ''
        shift = parts[3].lower() if len(parts) > 3 else 'morning'

        grouped_subjects[name]['classes'].append({
            'subject_id': s['id'],
            'class_id': s.get('class_id'),
            'class_name': class_name,
            'year': year,
            'semester': semester,
            'section': section,
            'shift': shift
        })

    return render_template('teacher/attendance.html', grouped_subjects=grouped_subjects, teacher=teacher)


@teacher_bp.route('/teacher/attendance/take/<int:subject_id>/<int:class_id>', methods=['GET', 'POST'])
@teacher_required
def take_attendance(subject_id, class_id):
    """Take attendance for a subject."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == class_id), None)

    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher.attendance'))

    students = db.get_enrolled_students_for_subject(subject_id, class_id) or []
    attendance_date = request.args.get('date', date.today().isoformat())

    if request.method == 'POST':
        attendance_date = request.form.get('date', date.today().isoformat())

        for student in students:
            status = request.form.get(f'status_{student["id"]}', 'absent')
            notes = request.form.get(f'notes_{student["id"]}', '')
            db.record_attendance(student['id'], subject_id, teacher['id'], attendance_date, status, notes)

        flash('Attendance recorded successfully!', 'success')
        return redirect(url_for('teacher.take_attendance', subject_id=subject_id, class_id=class_id, date=attendance_date))

    existing_attendance = db.get_attendance_by_subject_date(subject_id, attendance_date) or []
    attendance_dict = {a['student_id']: a for a in existing_attendance}

    return render_template('teacher/take_attendance.html',
                           subject=subject,
                           students=students,
                           attendance_date=attendance_date,
                           attendance_dict=attendance_dict)


@teacher_bp.route('/teacher/attendance/logs/<int:subject_id>/<int:class_id>')
@teacher_required
def attendance_logs(subject_id, class_id):
    """View attendance logs with filtering."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == class_id), None)

    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher.attendance'))

    student_id = request.args.get('student_id', type=int)
    status = request.args.get('status', '')

    students = db.get_enrolled_students_for_subject(subject_id, class_id) or []

    all_logs = db.get_attendance_logs(subject_id) or []

    logs_by_date = {}
    for log in all_logs:
        date_str = log['date'].strftime('%A, %B %d, %Y') if log['date'] else 'Unknown'
        if date_str not in logs_by_date:
            logs_by_date[date_str] = []
        logs_by_date[date_str].append(log)

    student_logs = []
    if student_id:
        student_logs = db.get_attendance_logs(
            subject_id,
            student_id=student_id,
            status=status if status else None
        ) or []

    summary = db.get_attendance_summary(subject_id) or []
    dates = db.get_attendance_dates(subject_id) or []

    return render_template('teacher/attendance_logs.html',
                           subject=subject,
                           students=students,
                           logs_by_date=logs_by_date,
                           student_logs=student_logs,
                           summary=summary,
                           dates=dates,
                           filters={
                               'student_id': student_id,
                               'status': status
                           })


# =============================================
# TEACHER - GRADES
# =============================================

@teacher_bp.route('/teacher/grades')
@teacher_required
def grades():
    """Grades management page — grouped by subject name."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []

    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'classes': []}

        class_id = s.get('class_id')
        if class_id:
            class_name = s.get('class_name', '')
            parts = class_name.split(' - ')
            year = parts[0].replace('Year ', '') if len(parts) > 0 else '?'
            sem = parts[1].replace('Sem ', '') if len(parts) > 1 else str(s.get('semester', '?'))
            section = parts[2].replace('Section ', '') if len(parts) > 2 else ''
            shift = parts[3].lower() if len(parts) > 3 else 'morning'
        else:
            sem = str(s.get('semester', '?'))
            year = str(s.get('year', ''))
            section = s.get('section') or ''
            shift = s.get('shift') or 'morning'
            class_name = f'Semester {sem}'

        grouped_subjects[name]['classes'].append({
            'subject_id': s['id'],
            'class_id': class_id or 0,
            'class_name': class_name,
            'year': year,
            'semester': sem,
            'section': section,
            'shift': shift
        })

    return render_template('teacher/grades.html', grouped_subjects=grouped_subjects, teacher=teacher)


@teacher_bp.route('/teacher/grades/add/<int:subject_id>/<int:class_id>', methods=['GET', 'POST'])
@teacher_required
def add_grades(subject_id, class_id):
    """Add grades for a subject."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    effective_class_id = None if class_id == 0 else class_id
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == effective_class_id), None)

    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher.grades'))

    students = db.get_enrolled_students_for_subject(subject_id, effective_class_id) or []
    components = db.get_grade_components_by_subject(subject_id) or []

    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id', '')
            grade_date_str = request.form.get('date', '').strip()

            if not grade_date_str:
                grade_date = date.today().isoformat()
            else:
                grade_date = grade_date_str

            if not student_id:
                return jsonify({'success': False, 'message': 'Student ID is required'}), 400

            grades_saved = 0
            errors = []

            for key in request.form.keys():
                if key.startswith('component_'):
                    component_id = int(key.replace('component_', ''))
                    score_str = request.form.get(key, '').strip()

                    if score_str != '':
                        try:
                            score = float(score_str)

                            component = next((c for c in components if c['id'] == component_id), None)
                            if component:
                                result = db.upsert_grade(
                                    int(student_id),
                                    subject_id,
                                    teacher['id'],
                                    component['component_type'],
                                    component['component_name'],
                                    score,
                                    float(component['max_score']),
                                    grade_date,
                                    component_id,
                                    None,
                                    False
                                )

                                if result:
                                    grades_saved += 1
                                else:
                                    errors.append(f"Failed to save {component['component_name']}")
                            else:
                                errors.append(f"Component {component_id} not found")
                        except ValueError as e:
                            errors.append(f"Invalid score value for component {component_id}: {e}")
                        except Exception as e:
                            errors.append(f"Exception for component {component_id}: {e}")

            if grades_saved > 0:
                message = f'{grades_saved} grade(s) saved successfully'
                if errors:
                    message += f'. Errors: {"; ".join(errors)}'
                return jsonify({'success': True, 'message': message}), 200
            else:
                error_msg = 'No valid grades were entered'
                if errors:
                    error_msg += f': {"; ".join(errors)}'
                return jsonify({'success': False, 'message': error_msg}), 400

        except Exception as e:
            print(f"ERROR SAVING GRADES: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    pair_groups_seen = set()
    effective_component_count = 0
    effective_total_weight = 0.0
    for c in components:
        pg = c.get('pair_group')
        if pg is None:
            effective_component_count += 1
            effective_total_weight += float(c.get('weight_percentage') or 0)
        elif pg not in pair_groups_seen:
            effective_component_count += 1
            effective_total_weight += float(c.get('weight_percentage') or 0)
            pair_groups_seen.add(pg)

    return render_template('teacher/add_grades.html',
                           subject=subject,
                           students=students,
                           components=components,
                           effective_component_count=effective_component_count,
                           effective_total_weight=effective_total_weight,
                           today=date.today().isoformat())


@teacher_bp.route('/teacher/grades/publish/<int:subject_id>/<int:class_id>', methods=['POST'])
@teacher_required
def publish_grades(subject_id, class_id):
    """Publish all draft grades for a subject/class."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        return jsonify({'success': False, 'message': 'Teacher profile not found'}), 403

    effective_class_id = None if class_id == 0 else class_id
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == effective_class_id), None)

    if not subject:
        return jsonify({'success': False, 'message': 'Subject not found or access denied'}), 403

    try:
        db.publish_grades_for_subject(subject_id, effective_class_id)
        return jsonify({'success': True, 'message': 'Grades published successfully! Students can now see their grades.'})
    except Exception as e:
        print(f"Error publishing grades: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@teacher_bp.route('/teacher/grades/student/<int:student_id>/subject/<int:subject_id>')
@teacher_required
def get_student_grades(student_id, subject_id):
    """Get existing grades for a specific student and subject (for pre-filling the modal)."""
    try:
        query = """
            SELECT
                gc.id AS component_id,
                gc.component_name,
                gc.component_type,
                gc.max_score,
                gc.weight_percentage,
                gc.pair_group,
                gc.display_order,
                g.score,
                g.date,
                COALESCE(g.published, FALSE) AS published
            FROM grade_components gc
            LEFT JOIN LATERAL (
                SELECT gr.score, gr.date, gr.published
                FROM grades gr
                WHERE gr.student_id = %s
                  AND gr.subject_id = %s
                  AND gr.component_id = gc.id
                ORDER BY gr.date DESC, gr.id DESC
                LIMIT 1
            ) g ON TRUE
            WHERE gc.subject_id = %s
            ORDER BY gc.display_order, gc.id
        """
        component_rows = db.execute_query(query, (student_id, subject_id, subject_id), fetch_all=True) or []
        summary = db.build_grade_summary(component_rows)

        grades_list = []
        for grade in component_rows:
            if grade.get('score') is None:
                continue
            grades_list.append({
                'component_id': grade['component_id'],
                'score': grade['score'],
                'max_score': grade['max_score'],
                'weight_percentage': grade.get('weight_percentage', 0),
                'component_name': grade.get('component_name', ''),
                'pair_group': grade.get('pair_group'),
                'date': grade['date'].isoformat() if hasattr(grade.get('date'), 'isoformat') else str(grade.get('date') or ''),
                'published': bool(grade.get('published')),
            })

        return jsonify({
            'success': True,
            'grades': grades_list,
            'summary': {
                'total_score': summary['total_score'],
                'total_max': summary['total_max'],
            }
        })

    except Exception as e:
        print(f"Error fetching student grades: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@teacher_bp.route('/teacher/grades/view/<int:subject_id>/<int:class_id>')
@teacher_required
def view_grades(subject_id, class_id):
    """View grades for a subject."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    effective_class_id = None if class_id == 0 else class_id
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == effective_class_id), None)

    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher.grades'))

    grades_list = db.get_grades_by_subject(subject_id) or []
    return render_template('teacher/view_grades.html', subject=subject, grades=grades_list)


# =============================================
# TEACHER - HOMEWORK
# =============================================

@teacher_bp.route('/teacher/homework')
@teacher_required
def homework():
    """Homework management page."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    homework_list = db.get_homework_by_teacher(teacher['id']) or []
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    today = date.today().isoformat()

    grouped = {}
    for hw in homework_list:
        due_iso = hw['due_date'].isoformat() if hasattr(hw['due_date'], 'isoformat') else str(hw['due_date'])
        key = (hw['title'], hw['subject_name'], due_iso)
        if key not in grouped:
            grouped[key] = {
                'ids': [],
                'title': hw['title'],
                'description': hw.get('description', ''),
                'filename': hw.get('filename'),
                'file_size': hw.get('file_size'),
                'first_id': hw['id'],
                'subject_name': hw['subject_name'],
                'due_date': hw['due_date'],
                'due_iso': due_iso,
                'classes': [],
            }
        grouped[key]['ids'].append(hw['id'])
        grouped[key]['classes'].append(hw['class_name'])

    grouped_homework = list(grouped.values())
    return render_template('teacher/homework.html',
                           grouped_homework=grouped_homework,
                           homework=homework_list,
                           subjects=subjects,
                           today=today)


@teacher_bp.route('/teacher/homework/add', methods=['GET', 'POST'])
@teacher_required
def add_homework():
    """Add new homework."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    unique_subjects = sorted(set(s['name'] for s in subjects))

    if request.method == 'POST':
        assignment_ids = request.form.getlist('assignment_ids')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date', '')

        if not all([assignment_ids, title, due_date]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('teacher/add_homework.html', subjects=subjects, unique_subjects=unique_subjects)

        filename = None
        file_content = None
        file_type = None
        file_size = None

        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                from flask import current_app as _ca
                from werkzeug.utils import secure_filename as _sf
                original_filename = _sf(file.filename)
                ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                allowed = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip', 'rar',
                           'jpg', 'jpeg', 'png', 'gif'}
                if ext in allowed:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{original_filename}"
                    file_content = file.read()
                    file_size = len(file_content)
                    file_type = ext

        success_count = 0
        for assignment_id in assignment_ids:
            assignment = next((s for s in subjects if s['assignment_id'] == int(assignment_id)), None)
            if assignment:
                current_file_path = None
                if file_content:
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    homework_folder = os.path.join(upload_folder, 'homework', f"subject_{assignment['id']}")
                    os.makedirs(homework_folder, exist_ok=True)
                    current_file_path = os.path.join(homework_folder, filename)
                    with open(current_file_path, 'wb') as f:
                        f.write(file_content)
                    current_file_path = os.path.relpath(current_file_path, upload_folder)

                hw_id = db.create_homework(
                    assignment['class_id'],
                    assignment['id'],
                    teacher['id'],
                    title,
                    description,
                    due_date,
                    filename=filename,
                    file_path=current_file_path,
                    file_type=file_type,
                    file_size=file_size
                )
                if hw_id:
                    success_count += 1

        if success_count > 0:
            flash(f'Homework created successfully for {success_count} class(es)!', 'success')
            return redirect(url_for('teacher.homework'))
        else:
            flash('Error creating homework.', 'danger')

    return render_template('teacher/add_homework.html', subjects=subjects, unique_subjects=unique_subjects)


@teacher_bp.route('/teacher/homework/delete/<int:homework_id>', methods=['POST'])
@teacher_required
def delete_homework(homework_id):
    """Delete homework."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    result = db.delete_homework(homework_id, teacher['id'])

    if result:
        flash('Homework marked as done and removed successfully!', 'success')
    else:
        flash('Error: Could not delete homework. You can only delete your own homework.', 'danger')

    return redirect(url_for('teacher.homework'))


@teacher_bp.route('/teacher/homework/delete-group', methods=['POST'])
@teacher_required
def delete_homework_group():
    """Delete a group of homework rows at once."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    ids_raw = request.form.get('homework_ids', '')
    deleted = 0
    for id_str in ids_raw.split(','):
        try:
            hw_id = int(id_str.strip())
            if db.delete_homework(hw_id, teacher['id']):
                deleted += 1
        except (ValueError, TypeError):
            continue

    if deleted:
        flash(f'Homework marked as done and removed ({deleted} class(es)).', 'success')
    else:
        flash('Could not delete homework.', 'danger')

    return redirect(url_for('teacher.homework'))


# =============================================
# SHARED FILE DOWNLOAD (teachers + students)
# =============================================

@teacher_bp.route('/homework/download/<int:homework_id>')
@login_required
def download_homework_file(homework_id):
    """Download homework attachment file."""
    query = "SELECT * FROM homework WHERE id = %s"
    hw = db.execute_query(query, (homework_id,), fetch_one=True)

    if not hw or not hw.get('filename'):
        flash('File not found.', 'danger')
        return redirect(request.referrer or url_for('auth.dashboard'))

    user_role = session.get('role')

    if user_role == 'teacher':
        teacher = db.get_teacher_by_user_id(session['user_id'])
        if teacher and hw['teacher_id'] != teacher['id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher.homework'))
    elif user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if student and hw['class_id'] != student['class_id']:
            flash('Access denied. This homework is not for your class.', 'danger')
            return redirect(url_for('student.dashboard'))

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], hw['file_path'])

    if os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename, as_attachment=True, download_name=hw['filename'])
    else:
        flash('File not found on server.', 'danger')
        return redirect(request.referrer or url_for('auth.dashboard'))


@teacher_bp.route('/files/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Download a lecture file."""
    file_info = db.get_lecture_file_by_id(file_id)

    if not file_info:
        flash('File not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    user_role = session.get('role')

    if user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if student:
            if student['class_id'] != file_info['class_id']:
                flash('Access denied. This file is not for your class.', 'danger')
                return redirect(url_for('student.files'))

    if os.path.exists(file_info['file_path']):
        directory = os.path.dirname(file_info['file_path'])
        filename = os.path.basename(file_info['file_path'])
        return send_from_directory(directory, filename, as_attachment=True, download_name=file_info['file_name'])
    else:
        flash('File not found on server.', 'danger')
        return redirect(url_for('auth.dashboard'))


@teacher_bp.route('/files/view/<int:file_id>')
@login_required
def view_file(file_id):
    """View a lecture file (for PDFs and images)."""
    file_info = db.get_lecture_file_by_id(file_id)

    if not file_info:
        flash('File not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    user_role = session.get('role')

    if user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if student:
            if student['class_id'] != file_info['class_id']:
                flash('Access denied. This file is not for your class.', 'danger')
                return redirect(url_for('student.files'))

    if os.path.exists(file_info['file_path']):
        directory = os.path.dirname(file_info['file_path'])
        filename = os.path.basename(file_info['file_path'])
        return send_from_directory(directory, filename)
    else:
        flash('File not found on server.', 'danger')
        return redirect(url_for('auth.dashboard'))


# =============================================
# TEACHER - SCHEDULE (View Only)
# =============================================

@teacher_bp.route('/teacher/schedule')
@teacher_required
def schedule():
    """View class schedules (read-only)."""
    return render_template('teacher/schedule.html')


@teacher_bp.route('/teacher/api/schedule/<int:semester>/<shift>/<section>', methods=['GET'])
@teacher_required
def api_get_schedule(semester, shift, section):
    """API: Get schedule for a semester/shift/section (teacher read-only)."""
    import json
    major_id = session.get('major_id')
    sched = db.get_schedule(semester, shift, section, major_id=major_id)
    if sched and sched.get('schedule_data'):
        data = sched['schedule_data']
        if isinstance(data, (list, dict)):
            return {'success': True, 'data': data}
        return {'success': True, 'data': json.loads(data)}
    return {'success': True, 'data': []}


# =============================================
# TEACHER - WEEKLY TOPICS
# =============================================

@teacher_bp.route('/teacher/topics')
@teacher_required
def topics():
    """Weekly topics management — grouped by subject name."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []

    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'classes': []}

        class_name = s.get('class_name', '')
        parts = class_name.split(' - ')
        year = parts[0].replace('Year ', '') if len(parts) > 0 else '?'
        semester = parts[1].replace('Sem ', '') if len(parts) > 1 else '?'
        section = parts[2].replace('Section ', '') if len(parts) > 2 else ''
        shift = parts[3].lower() if len(parts) > 3 else 'morning'

        grouped_subjects[name]['classes'].append({
            'subject_id': s['id'],
            'class_name': class_name,
            'year': year,
            'semester': semester,
            'section': section,
            'shift': shift
        })

    return render_template('teacher/topics.html', grouped_subjects=grouped_subjects)


@teacher_bp.route('/teacher/topics/<int:subject_id>', methods=['GET', 'POST'])
@teacher_required
def manage_topics(subject_id):
    """Manage exam/quiz notes for a subject."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id), None)

    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher.topics'))

    if request.method == 'POST' and request.form.get('action') == 'delete':
        note_id = request.form.get('note_id', type=int)
        if note_id:
            db.delete_exam_note(note_id, teacher['id'])
            flash('Note deleted.', 'success')
        return redirect(url_for('teacher.manage_topics', subject_id=subject_id))

    if request.method == 'POST':
        note_type = request.form.get('note_type', 'exam').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        exam_date = request.form.get('exam_date', '')

        if not title:
            flash('Please enter a title.', 'warning')
        else:
            db.create_exam_note(
                subject['class_id'], subject_id, teacher['id'],
                note_type, title,
                description if description else None,
                exam_date if exam_date else None
            )
            flash('Note saved successfully!', 'success')
        return redirect(url_for('teacher.manage_topics', subject_id=subject_id))

    notes = db.get_weekly_topics_by_subject(subject_id) or []
    return render_template('teacher/manage_topics.html', subject=subject, topics=notes)


# =============================================
# TEACHER - LECTURE FILES MANAGEMENT
# =============================================

@teacher_bp.route('/teacher/files')
@teacher_required
def files():
    """View all uploaded lecture files."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    files_list = db.get_lecture_files_by_teacher(teacher['id']) or []
    subjects = db.get_subjects_by_teacher(teacher['id']) or []

    grouped = {}
    for f in files_list:
        key = (f['title'], f['subject_name'], f.get('week_number'), f.get('file_name'))
        if key not in grouped:
            grouped[key] = {
                'ids': [],
                'first_id': f['id'],
                'title': f['title'],
                'subject_name': f['subject_name'],
                'file_name': f.get('file_name'),
                'file_type': f.get('file_type'),
                'file_size': f.get('file_size'),
                'week_number': f.get('week_number'),
                'file_path': f.get('file_path'),
                'uploaded_at': f.get('uploaded_at'),
                'classes': [],
            }
        grouped[key]['ids'].append(f['id'])
        grouped[key]['classes'].append(f.get('class_name', ''))

    grouped_files = list(grouped.values())
    return render_template('teacher/files.html', grouped_files=grouped_files, files=files_list, subjects=subjects)


# =============================================
# TEACHER - EXAM SIGNUPS
# =============================================

@teacher_bp.route('/teacher/exams/signups/<int:subject_id>')
@teacher_required
def view_exam_signups(subject_id):
    """View students signed up for exams in this subject."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id), None)

    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('auth.dashboard'))

    final_signups = db.get_exam_signups_for_subject(subject_id, 'final') or []
    second_round_signups = db.get_exam_signups_for_subject(subject_id, 'second_round') or []

    return render_template('teacher/exam_signups.html',
                           subject=subject,
                           final_signups=final_signups,
                           second_round_signups=second_round_signups)


@teacher_bp.route('/teacher/files/upload', methods=['GET', 'POST'])
@teacher_required
def upload_file():
    """Upload a new lecture file."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    unique_subjects = sorted(set(s['name'] for s in subjects))

    if request.method == 'POST':
        assignment_ids = request.form.getlist('assignment_ids')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        week_number = request.form.get('week_number', '')

        if 'file' not in request.files:
            flash('No file selected.', 'warning')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No file selected.', 'warning')
            return redirect(request.url)

        if not assignment_ids or not title:
            flash('Please fill in all required fields.', 'warning')
            return render_template('teacher/upload_file.html', subjects=subjects, unique_subjects=unique_subjects)

        allowed = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip', 'rar',
                   'jpg', 'jpeg', 'png', 'gif'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

        if file and ext in allowed:
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{original_filename}"

            file_content = file.read()
            file_size = len(file_content)
            file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
            week_num = int(week_number) if week_number else None

            upload_folder = current_app.config['UPLOAD_FOLDER']
            success_count = 0
            for assignment_id in assignment_ids:
                assignment = next((s for s in subjects if s['assignment_id'] == int(assignment_id)), None)
                if not assignment:
                    continue

                subject_id = assignment['id']
                class_id = assignment['class_id']

                subject_folder = os.path.join(upload_folder, f"subject_{subject_id}")
                os.makedirs(subject_folder, exist_ok=True)

                file_path_individual = os.path.join(subject_folder, filename)

                with open(file_path_individual, 'wb') as f:
                    f.write(file_content)

                db.create_lecture_file(
                    subject_id=subject_id,
                    teacher_id=teacher['id'],
                    class_id=class_id,
                    title=title,
                    description=description,
                    file_name=original_filename,
                    file_path=file_path_individual,
                    file_size=file_size,
                    file_type=file_type,
                    week_number=week_num
                )
                success_count += 1

            flash(f'File "{original_filename}" uploaded successfully to {success_count} class(es)!', 'success')
            return redirect(url_for('teacher.upload_file'))
        else:
            flash('File type not allowed. Allowed: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, TXT, ZIP, RAR, Images', 'danger')

    return render_template('teacher/upload_file.html', subjects=subjects, unique_subjects=unique_subjects)


@teacher_bp.route('/teacher/files/delete/<int:file_id>', methods=['POST'])
@teacher_required
def delete_file(file_id):
    """Delete a lecture file."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    file_info = db.get_lecture_file_by_id(file_id)
    if file_info and file_info['teacher_id'] == teacher['id']:
        if os.path.exists(file_info['file_path']):
            os.remove(file_info['file_path'])
        db.delete_lecture_file(file_id)
        flash('File deleted successfully!', 'success')
    else:
        flash('File not found or access denied.', 'danger')

    return redirect(url_for('teacher.files'))


@teacher_bp.route('/teacher/files/delete-group', methods=['POST'])
@teacher_required
def delete_file_group():
    """Delete all class copies of a grouped lecture file at once."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    ids_raw = request.form.get('file_ids', '')
    physical_deleted = False
    deleted = 0
    for id_str in ids_raw.split(','):
        try:
            fid = int(id_str.strip())
            file_info = db.get_lecture_file_by_id(fid)
            if file_info and file_info['teacher_id'] == teacher['id']:
                if not physical_deleted and file_info.get('file_path') and os.path.exists(file_info['file_path']):
                    os.remove(file_info['file_path'])
                    physical_deleted = True
                db.delete_lecture_file(fid)
                deleted += 1
        except (ValueError, TypeError):
            continue

    if deleted:
        flash(f'File deleted from {deleted} class(es) successfully!', 'success')
    else:
        flash('Could not delete file.', 'danger')

    return redirect(url_for('teacher.files'))
