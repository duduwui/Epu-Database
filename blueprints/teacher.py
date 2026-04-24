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
import time
from blueprints.auth import teacher_required, login_required

teacher_bp = Blueprint('teacher', __name__)


def _resolve_uploaded_path(stored_path):
    """Resolve legacy absolute paths and newer UPLOAD_FOLDER-relative paths."""
    if not stored_path:
        return None

    normalized_path = os.path.normpath(stored_path)
    if os.path.isabs(normalized_path):
        return normalized_path

    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if upload_folder:
        return os.path.normpath(os.path.join(upload_folder, normalized_path))

    return normalized_path


def _teacher_has_assignment(teacher_id, subject_id, class_id):
    assignments = db.get_subjects_by_teacher(teacher_id) or []
    return any(item['id'] == subject_id and item.get('class_id') == class_id for item in assignments)


def _send_uploaded_file(stored_path, download_name=None, as_attachment=False):
    file_path = _resolve_uploaded_path(stored_path)
    if file_path and os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        kwargs = {'as_attachment': as_attachment}
        if download_name:
            kwargs['download_name'] = download_name
        return send_from_directory(directory, filename, **kwargs)
    flash('File not found on server.', 'danger')
    return redirect(request.referrer or url_for('auth.dashboard'))


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

@teacher_bp.route('/teacher/grades/overview', methods=['GET'])
@teacher_required
def grades_overview():
    """Detailed overview table for filtering and inline editing."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    grades_data = db.get_all_grades_overview_for_teacher(teacher['id']) or []
    
    # Process into a structured format for the template
    # Group by student + subject so each row is a student's performance in one subject
    students_dict = {}
    for r in grades_data:
        key = (r['student_id'], r['subject_id'])
        if key not in students_dict:
            students_dict[key] = {
                'student_id': r['student_id'],
                'student_name': r['student_name'],
                'student_number': r['student_number'],
                'subject_id': r['subject_id'],
                'subject_name': r['subject_name'],
                'semester': r['semester'],
                'class_name': r['class_name'] or 'Unassigned',
                'shift': r['shift'] or 'Morning',
                'components': {}
            }
        
        students_dict[key]['components'][r['component_id']] = {
            'component_id': r['component_id'],
            'component_name': r['component_name'],
            'score': r['score'],
            'max_score': r['max_score'],
            'grade_id': r['grade_id']
        }
        
    students_list = list(students_dict.values())
    
    # We also need unique classes/semesters/shifts/subjects for the dropdown filters
    filters = {
        'classes': sorted(list(set(s['class_name'] for s in students_list))),
        'semesters': sorted(list(set(s['semester'] for s in students_list))),
        'shifts': sorted(list(set(s['shift'] for s in students_list))),
        'subjects': sorted(list(set(s['subject_name'] for s in students_list)))
    }
    
    # We need a master list of all components for column headers (grouped by subject)
    subject_components = {}
    for r in grades_data:
        if r['subject_id'] not in subject_components:
            subject_components[r['subject_id']] = []
        if not any(c['id'] == r['component_id'] for c in subject_components[r['subject_id']]):
            subject_components[r['subject_id']].append({
                'id': r['component_id'],
                'name': r['component_name'],
                'max_score': r['max_score']
            })

    return render_template('teacher/grades_overview.html', 
                           students=students_list, 
                           filters=filters, 
                           subject_components=subject_components,
                           teacher=teacher)


@teacher_bp.route('/teacher/api/save_inline_grade', methods=['POST'])
@teacher_required
def api_save_inline_grade():
    """AJAX endpoint for saving a specific grade from the overview table."""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        return jsonify({'success': False, 'message': 'Teacher profile not found.'}), 403

    try:
        student_id = int(request.form.get('student_id', 0))
        subject_id = int(request.form.get('subject_id', 0))
        component_id = int(request.form.get('component_id', 0))
        score_str = request.form.get('score', '').strip()

        # Validate assignment
        assignments = db.get_subjects_by_teacher(teacher['id']) or []
        if not any(a['id'] == subject_id for a in assignments):
            return jsonify({'success': False, 'message': 'Access denied for subject.'}), 403

        # Validate Component
        components = db.get_grade_components_by_subject(subject_id) or []
        target_component = next((c for c in components if c['id'] == component_id), None)

        if not target_component:
            return jsonify({'success': False, 'message': 'Component not found.'}), 404

        grade_date = date.today().isoformat()

        if score_str == '':
            # Empty means they want to delete/null the grade or the UI just didn't send - but our ui shouldn't support deleting for now without more logic. We will skip deleting for safety, or accept 0. Or if empty string we can pass score=None if upsert supports it. Actually upsert_grade handles it as floating score.
            return jsonify({'success': False, 'message': 'Cannot delete grades via inline UI currently.'}), 400

        score = float(score_str)
        if score < 0 or score > target_component['max_score']:
            return jsonify({'success': False, 'message': f'Score must be between 0 and {target_component["max_score"]}.'}), 400

        result = db.upsert_grade(
            student_id,
            subject_id,
            teacher['id'],
            target_component['component_type'],
            target_component['component_name'],
            score,
            float(target_component['max_score']),
            grade_date,
            component_id,
            None,
            False # Draft mode
        )

        if result:
            return jsonify({'success': True, 'message': 'Grade saved.'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save grade to database.'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


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

    return _send_uploaded_file(hw.get('file_path'), download_name=hw['filename'], as_attachment=True)


@teacher_bp.route('/homework/view/<int:homework_id>')
@login_required
def view_homework_file(homework_id):
    """Open a homework attachment inline when the browser supports it."""
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

    return _send_uploaded_file(hw.get('file_path'))


@teacher_bp.route('/moodle/submissions/download/<int:submission_id>')
@login_required
def download_moodle_submission_file(submission_id):
    submission = db.get_moodle_request_submission_by_id(submission_id)
    if not submission:
        flash('File not found.', 'danger')
        return redirect(request.referrer or url_for('auth.dashboard'))

    user_role = session.get('role')
    if user_role == 'teacher':
        teacher = db.get_teacher_by_user_id(session['user_id'])
        if not teacher or submission['teacher_id'] != teacher['id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher.moodle'))
    elif user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if not student or submission['student_id'] != student['id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('student.moodle'))

    return _send_uploaded_file(submission.get('file_path'), download_name=submission['file_name'], as_attachment=True)


@teacher_bp.route('/moodle/submissions/view/<int:submission_id>')
@login_required
def view_moodle_submission_file(submission_id):
    submission = db.get_moodle_request_submission_by_id(submission_id)
    if not submission:
        flash('File not found.', 'danger')
        return redirect(request.referrer or url_for('auth.dashboard'))

    user_role = session.get('role')
    if user_role == 'teacher':
        teacher = db.get_teacher_by_user_id(session['user_id'])
        if not teacher or submission['teacher_id'] != teacher['id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher.moodle'))
    elif user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if not student or submission['student_id'] != student['id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('student.moodle'))

    return _send_uploaded_file(submission.get('file_path'))


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

    return _send_uploaded_file(file_info.get('file_path'), download_name=file_info['file_name'], as_attachment=True)


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

    return _send_uploaded_file(file_info.get('file_path'))


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
        file_path = _resolve_uploaded_path(file_info.get('file_path'))
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
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
                file_path = _resolve_uploaded_path(file_info.get('file_path'))
                if not physical_deleted and file_path and os.path.exists(file_path):
                    os.remove(file_path)
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


# =============================================
# TEACHER - MOODLE HUB
# =============================================

@teacher_bp.route('/teacher/moodle')
@teacher_required
def moodle():
    """List subjects for Moodle view"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    return render_template('teacher/moodle_list.html', subjects=subjects)

@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>', methods=['GET'])
@teacher_required
def moodle_hub(subject_id, class_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher or not _teacher_has_assignment(teacher['id'], subject_id, class_id):
        flash("Access denied.", "danger")
        return redirect(url_for('teacher.moodle'))
    subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    moodle_content = db.get_moodle_content(class_id, subject_id)
    return render_template('teacher/moodle_hub.html', subject=subject, class_id=class_id, moodle_content=moodle_content)

@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/add_week', methods=['POST'])
@teacher_required
def moodle_add_week(subject_id, class_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher and session.get('role') == 'admin':
        flash("Admins cannot add Moodle content unless assigned as a teacher.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))
    elif not teacher:
        flash("Teacher record not found.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    title = request.form.get('title')
    display_order = request.form.get('display_order', 0)
    db.create_moodle_week(class_id, subject_id, session['user_id'], title, display_order)
    flash(f"Moodle week added successfully.", "success")
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/add_file', methods=['POST'])
@teacher_required
def moodle_add_file(subject_id, class_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash("You must be an assigned teacher to add content.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))
        
    material_type = request.form.get('material_type')
    title = request.form.get('title')
    description = request.form.get('description', '')
    week_id = request.form.get('week_id')
    
    if material_type == 'link':
        link_url = request.form.get('link_url')
        db.create_lecture_file(subject_id, teacher['id'], class_id, title, description, None, None, None, None, None, week_id, True, link_url)
        flash("Link added successfully.", "success")
    else:
        file = request.files.get('file')
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Setup upload dir
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f"subject_{subject_id}")
            os.makedirs(upload_dir, exist_ok=True)
            
            # Create a unique filename
            unique_filename = f"{int(time.time())}_{filename}"
            file_path = os.path.join(f"subject_{subject_id}", unique_filename)
            absolute_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
            
            file.save(absolute_path)
            file_size = os.path.getsize(absolute_path)
            file_type = file.content_type
            
            db.create_lecture_file(subject_id, teacher['id'], class_id, title, description, filename, file_path, file_size, file_type, None, week_id, False, None)
            flash("File uploaded successfully.", "success")
        else:
            flash("No file selected.", "danger")
            
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/add_request', methods=['POST'])
@teacher_required
def moodle_add_request(subject_id, class_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher or not _teacher_has_assignment(teacher['id'], subject_id, class_id):
        flash("You must be an assigned teacher to create Moodle requests.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    due_at_raw = request.form.get('due_at')
    week_id = request.form.get('week_id') or None
    attachment = request.files.get('file')

    if not title or not due_at_raw:
        flash("Title and due date/time are required.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    try:
        due_at = datetime.fromisoformat(due_at_raw)
    except ValueError:
        flash("Invalid due date/time.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    if week_id:
        try:
            week_id = int(week_id)
        except (TypeError, ValueError):
            flash("Invalid week selected.", "danger")
            return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))
        week = db.get_moodle_week_by_id(week_id, teacher_id=session['user_id'])
        if not week or week['subject_id'] != subject_id or week['class_id'] != class_id:
            flash("Invalid week selected.", "danger")
            return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    filename = None
    relative_path = None
    file_size = 0
    file_type = None

    if attachment and attachment.filename:
        filename = secure_filename(attachment.filename)
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'moodle_requests', f"subject_{subject_id}", f"class_{class_id}")
        os.makedirs(upload_dir, exist_ok=True)
        unique_filename = f"{int(time.time())}_{filename}"
        absolute_path = os.path.join(upload_dir, unique_filename)
        attachment.save(absolute_path)
        relative_path = os.path.relpath(absolute_path, current_app.config['UPLOAD_FOLDER'])
        file_size = os.path.getsize(absolute_path)
        file_type = attachment.content_type

    db.create_homework(
        class_id=class_id,
        subject_id=subject_id,
        teacher_id=teacher['id'],
        title=title,
        description=description,
        due_date=due_at.date(),
        filename=filename,
        file_path=relative_path,
        file_type=file_type,
        file_size=file_size,
        week_id=week_id,
        is_moodle_request=True,
        due_at=due_at
    )
    flash("Moodle request created successfully.", "success")
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/request/<int:request_id>')
@teacher_required
def moodle_request_details(subject_id, class_id, request_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher or not _teacher_has_assignment(teacher['id'], subject_id, class_id):
        flash("Access denied.", "danger")
        return redirect(url_for('teacher.moodle'))

    request_row = db.get_moodle_request_by_id(request_id)
    if not request_row or request_row['subject_id'] != subject_id or request_row['class_id'] != class_id or request_row['teacher_id'] != teacher['id']:
        flash("Request not found or access denied.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    roster = db.get_moodle_request_roster(request_id)
    submitted = [row for row in roster if row.get('submission_id')]
    remaining = [row for row in roster if not row.get('submission_id')]
    return render_template(
        'teacher/moodle_request_submissions.html',
        subject=subject,
        class_id=class_id,
        request_row=request_row,
        roster=roster,
        submitted=submitted,
        remaining=remaining
    )


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/request/<int:request_id>/update_due', methods=['POST'])
@teacher_required
def moodle_update_request_due(subject_id, class_id, request_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher or not _teacher_has_assignment(teacher['id'], subject_id, class_id):
        flash("Access denied.", "danger")
        return redirect(url_for('teacher.moodle'))

    due_at_raw = request.form.get('due_at')
    try:
        due_at = datetime.fromisoformat(due_at_raw)
    except (TypeError, ValueError):
        flash("Invalid due date/time.", "danger")
        return redirect(url_for('teacher.moodle_request_details', subject_id=subject_id, class_id=class_id, request_id=request_id))

    updated = db.update_moodle_request_due(request_id, teacher['id'], due_at)
    flash("Due date updated successfully." if updated else "Could not update due date.", "success" if updated else "danger")
    return redirect(url_for('teacher.moodle_request_details', subject_id=subject_id, class_id=class_id, request_id=request_id))


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/request/<int:request_id>/delete', methods=['POST'])
@teacher_required
def moodle_delete_request(subject_id, class_id, request_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher or not _teacher_has_assignment(teacher['id'], subject_id, class_id):
        flash("Access denied.", "danger")
        return redirect(url_for('teacher.moodle'))

    request_row = db.get_moodle_request_by_id(request_id)
    if not request_row or request_row['subject_id'] != subject_id or request_row['class_id'] != class_id or request_row['teacher_id'] != teacher['id']:
        flash("Request not found or access denied.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    attachment_path = _resolve_uploaded_path(request_row.get('file_path'))
    if attachment_path and os.path.exists(attachment_path):
        os.remove(attachment_path)

    for submission in db.get_moodle_request_submissions(request_id):
        submission_path = _resolve_uploaded_path(submission.get('file_path'))
        if submission_path and os.path.exists(submission_path):
            os.remove(submission_path)

    db.delete_moodle_request_submissions(request_id)
    db.delete_moodle_request(request_id, teacher['id'])
    flash("Moodle request deleted successfully.", "success")
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/delete_week/<int:week_id>', methods=['POST'])
@teacher_required
def moodle_delete_week(subject_id, class_id, week_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash("You must be an assigned teacher to delete weeks.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    week = db.get_moodle_week_by_id(week_id, teacher_id=session['user_id'])
    if not week or week['subject_id'] != subject_id or week['class_id'] != class_id:
        flash("Week not found or access denied.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    files = db.get_lecture_files_for_week(week_id)
    for file_info in files:
        if file_info['subject_id'] != subject_id or file_info['class_id'] != class_id:
            continue
        if not file_info.get('is_link'):
            file_path = _resolve_uploaded_path(file_info.get('file_path'))
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        db.delete_lecture_file(file_info['id'])

    homework_rows = db.get_homework_for_week(week_id)
    for hw in homework_rows:
        if hw['subject_id'] != subject_id or hw['class_id'] != class_id:
            continue
        file_path = _resolve_uploaded_path(hw.get('file_path'))
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        for submission in db.get_moodle_request_submissions(hw['id']):
            submission_path = _resolve_uploaded_path(submission.get('file_path'))
            if submission_path and os.path.exists(submission_path):
                os.remove(submission_path)
        db.delete_moodle_request_submissions(hw['id'])
    db.delete_homework_by_week(week_id)

    db.delete_moodle_week(week_id, session['user_id'])
    flash("Week and its files deleted successfully.", "success")
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/delete_file/<int:file_id>', methods=['POST'])
@teacher_required
def moodle_delete_file(subject_id, class_id, file_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash("You must be an assigned teacher to delete files.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    file_info = db.get_lecture_file_by_id(file_id)
    if not file_info or file_info['teacher_id'] != teacher['id'] or file_info['subject_id'] != subject_id or file_info['class_id'] != class_id:
        flash("File not found or access denied.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    if not file_info.get('is_link'):
        file_path = _resolve_uploaded_path(file_info.get('file_path'))
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    db.delete_lecture_file(file_id)
    flash("File deleted successfully.", "success")
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/replace_file/<int:file_id>', methods=['POST'])
@teacher_required
def moodle_replace_file(subject_id, class_id, file_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash("You must be an assigned teacher to replace files.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    file_info = db.get_lecture_file_by_id(file_id)
    if not file_info or file_info['teacher_id'] != teacher['id'] or file_info['subject_id'] != subject_id or file_info['class_id'] != class_id:
        flash("File not found or access denied.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    if file_info.get('is_link'):
        flash("Links cannot be replaced. Delete and add the link again.", "warning")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    file = request.files.get('file')
    if not file or not file.filename:
        flash("No replacement file selected.", "danger")
        return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f"subject_{subject_id}")
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = f"{int(time.time())}_{filename}"
    relative_path = os.path.join(f"subject_{subject_id}", unique_filename)
    absolute_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_path)
    file.save(absolute_path)
    file_size = os.path.getsize(absolute_path)
    file_type = file.content_type

    old_file_path = _resolve_uploaded_path(file_info.get('file_path'))
    if old_file_path and os.path.exists(old_file_path):
        os.remove(old_file_path)

    db.update_lecture_file_asset(
        file_id=file_id,
        teacher_id=teacher['id'],
        file_name=filename,
        file_path=relative_path,
        file_size=file_size,
        file_type=file_type
    )
    flash("File replaced successfully.", "success")
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))


@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/engagement')
@teacher_required
def moodle_engagement(subject_id, class_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher or not _teacher_has_assignment(teacher['id'], subject_id, class_id):
        flash("Access denied.", "danger")
        return redirect(url_for('teacher.moodle'))
    assignments = db.get_subjects_by_teacher(teacher['id']) if teacher else []
    stats = db.get_moodle_engagement_stats(subject_id, class_id)
    daily_details = db.get_moodle_engagement_daily_details(subject_id, class_id)
    details_by_student = {}
    for row in daily_details:
        details_by_student.setdefault(row['student_id'], []).append(row)
    for stat in stats:
        stat['daily_details'] = details_by_student.get(stat['student_id'], [])
    subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    return render_template(
        'teacher/moodle_engagement.html',
        stats=stats,
        subject=subject,
        class_id=class_id,
        assignments=assignments,
        selected_subject_id=subject_id,
        selected_class_id=class_id
    )
