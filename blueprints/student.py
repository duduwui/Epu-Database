"""
Student blueprint — all student-facing routes.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from datetime import date, datetime
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename
import os
import time
import db
from blueprints.auth import login_required, student_required
from blueprints.teacher import _resolve_uploaded_path

student_bp = Blueprint('student', __name__)


def _get_file_extension(file_info):
    file_name = (file_info.get('file_name') or '').lower()
    if '.' in file_name:
        return file_name.rsplit('.', 1)[1]

    file_type = (file_info.get('file_type') or '').lower()
    if '/' in file_type:
        return file_type.split('/')[-1]
    return file_type


def _extract_text_html(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    return Markup(f"<pre class=\"viewer-pre\">{escape(text)}</pre>")


def _get_student_file_view_payload(file_info):
    file_path = _resolve_uploaded_path(file_info.get('file_path'))
    extension = _get_file_extension(file_info)

    inline_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
    text_extensions = {'txt', 'csv', 'json', 'md'}
    html_extensions = {'html', 'htm'}
    docx_extensions = {'docx'}
    pptx_extensions = {'pptx'}
    xlsx_extensions = {'xlsx'}

    payload = {
        'mode': 'unsupported',
        'extension': extension,
        'raw_url': url_for('teacher.view_file', file_id=file_info['id']),
        'download_url': url_for('student.download_file', file_id=file_info['id']),
        'content_html': None,
    }

    if extension in inline_extensions:
        payload['mode'] = 'embed'
    elif extension in text_extensions or extension in html_extensions:
        payload['mode'] = 'html'
        payload['content_html'] = _extract_text_html(file_path)
    elif extension in docx_extensions or extension in pptx_extensions or extension in xlsx_extensions:
        # Preserve the original file and let the browser/device handle the native format.
        payload['mode'] = 'native'

    return payload


# =============================================
# STUDENT - DASHBOARD
# =============================================

@student_bp.route('/student/dashboard')
@login_required
def dashboard():
    """Student dashboard."""
    if session.get('role') != 'student':
        return redirect(url_for('auth.dashboard'))

    student = db.get_student_by_user_id(session['user_id'])

    if not student:
        lang = session.get('lang', 'en')
        session.clear()
        session['lang'] = lang
        flash('Student profile not found. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    current_semester = None
    attendance_summary = []
    attendance_log = []
    recent_materials = []
    pending_requests = []
    schedule_data = None

    if student.get('semester') and student.get('shift') and student.get('section'):
        current_semester = student['semester']
        schedule_data = db.get_class_schedule_data(
            student['semester'],
            student['shift'],
            student['section'],
            major_id=session.get('major_id')
        )

    attendance_summary = db.get_student_attendance_summary(student['id'], semester=current_semester) or []
    attendance_log = db.get_student_attendance_log(student['id'], semester=current_semester, limit=8) or []
    recent_materials = db.get_student_recent_moodle_materials(student['id'], semester=current_semester, limit=6) or []
    pending_requests = db.get_student_pending_moodle_requests(student['id'], semester=current_semester, limit=6) or []

    total_present = sum((row.get('present_count') or 0) for row in attendance_summary)
    total_absent = sum((row.get('absent_count') or 0) for row in attendance_summary)
    total_late = sum((row.get('late_count') or 0) for row in attendance_summary)
    total_excused = sum((row.get('excused_count') or 0) for row in attendance_summary)
    total_attendance_records = sum((row.get('total_records') or 0) for row in attendance_summary)
    attendance_rate = round(
        ((total_present + total_late + total_excused) / total_attendance_records) * 100, 1
    ) if total_attendance_records else 0.0

    today = date.today().isoformat()
    return render_template('student/dashboard.html',
                           student=student,
                           attendance_summary=attendance_summary,
                           attendance_log=attendance_log,
                           attendance_rate=attendance_rate,
                           total_present=total_present,
                           total_absent=total_absent,
                           total_late=total_late,
                           total_excused=total_excused,
                           total_attendance_records=total_attendance_records,
                           pending_requests=pending_requests,
                           recent_materials=recent_materials,
                           schedule_data=schedule_data,
                           current_semester=current_semester,
                           today=today)


# =============================================
# STUDENT - COMBINED SIGNUPS (Subjects + Exams)
# =============================================

@student_bp.route('/student/signups')
@login_required
def signups():
    """Combined signups page — subject enrollment + exam signup."""
    if session.get('role') != 'student':
        return redirect(url_for('auth.dashboard'))

    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    active_tab = request.args.get('tab', 'subjects')
    if active_tab not in ('subjects', 'exams'):
        active_tab = 'subjects'

    selected_semester = request.args.get('semester', type=int)

    class_info = None
    semester = selected_semester
    if student['class_id']:
        class_info = db.execute_query(
            'SELECT year, semester, section, shift, major_id FROM classes WHERE id = %s',
            (student['class_id'],), fetch_one=True
        )
        if class_info and semester is None:
            semester = class_info['semester']

    if semester is None and student.get('semester'):
        semester = student['semester']

    if semester is None:
        semester = 1

    enrollment_period = None
    enrollment_active = False
    effective_major_id = (
        student.get('major_id')
        or (class_info.get('major_id') if class_info else None)
        or session.get('major_id')
    )
    if semester:
        enrollment_period = db.get_active_enrollment_period(semester, major_id=effective_major_id)
        enrollment_active = enrollment_period is not None
    subjects = db.get_available_subjects_for_student(student['id'], semester) or []

    final_period = db.get_active_exam_period(semester, 'final', major_id=effective_major_id) if semester else None
    second_round_period = db.get_active_exam_period(semester, 'second_round', major_id=effective_major_id) if semester else None
    final_subjects = db.get_exam_eligible_subjects(student['id'], 'final', semester) if final_period else []
    second_round_subjects = db.get_exam_eligible_subjects(student['id'], 'second_round', semester) if second_round_period else []

    return render_template('student/signups.html',
                           student=student,
                           class_info=class_info,
                           active_tab=active_tab,
                           subjects=subjects,
                           enrollment_period=enrollment_period,
                           enrollment_active=enrollment_active,
                           final_period=final_period,
                           second_round_period=second_round_period,
                           final_subjects=final_subjects,
                           second_round_subjects=second_round_subjects,
                           selected_semester=semester)


@student_bp.route('/student/subjects')
@login_required
def subjects():
    """Redirect to combined signups page — subjects tab."""
    return redirect(url_for('student.signups', tab='subjects'))

@student_bp.route('/student/debug_exams')
@login_required
def debug_exams():
    res = f"Session Major ID: {session.get('major_id')}<br>Semester: {session.get('semester', 'N/A')}<br>Role: {session.get('role')}"
    return res

@student_bp.route('/student/subjects/enroll/<int:subject_id>', methods=['POST'])
@login_required
def enroll_subject(subject_id):
    """Enroll in a subject."""
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        return jsonify({'success': False, 'error': 'Student profile not found'}), 404

    class_info = db.execute_query(
        'SELECT semester FROM classes WHERE id = %s',
        (student['class_id'],),
        fetch_one=True
    )
    if class_info:
        semester = class_info['semester']
        if not db.is_enrollment_active(semester, major_id=session.get('major_id')):
            return jsonify({'success': False, 'error': 'Enrollment period has ended or not started yet'}), 403

    try:
        subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
        if not subject:
            return jsonify({'success': False, 'error': 'Subject not found'}), 404

        success = db.enroll_student_in_subject(student['id'], subject_id)
        if success:
            return jsonify({'success': True, 'message': 'Enrolled successfully'})
        else:
            return jsonify({'success': False, 'error': 'Already enrolled'})
    except Exception as e:
        print(f"Error enrolling student {student['id']} in subject {subject_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/student/subjects/unenroll/<int:subject_id>', methods=['POST'])
@login_required
def unenroll_subject(subject_id):
    """Unenroll from a subject."""
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        return jsonify({'success': False, 'error': 'Student profile not found'}), 404

    class_info = db.execute_query(
        'SELECT semester FROM classes WHERE id = %s',
        (student['class_id'],),
        fetch_one=True
    )
    if class_info:
        semester = class_info['semester']
        if not db.is_enrollment_active(semester, major_id=session.get('major_id')):
            return jsonify({'success': False, 'error': 'Enrollment period has ended or not started yet'}), 403

    try:
        db.unenroll_student_from_subject(student['id'], subject_id)
        return jsonify({'success': True, 'message': 'Unenrolled successfully'})
    except Exception as e:
        print(f"Error unenrolling student {student['id']} from subject {subject_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================
# STUDENT - GRADES
# =============================================

def _build_grade_display_groups(grades_data):
    """Build display groups for student grades using the shared calculator."""
    return db.build_grade_display_groups(grades_data)


@student_bp.route('/student/grades')
@login_required
def grades():
    """View student grades."""
    if session.get('role') != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.dashboard'))

    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    all_enrolled = db.get_enrolled_subjects_for_student(student['id']) or []

    semester_set = set()
    for subj in all_enrolled:
        if subj.get('semester'):
            semester_set.add(subj['semester'])
    available_semesters = sorted(semester_set)

    current_semester = student.get('semester') or (max(available_semesters) if available_semesters else 1)
    selected_semester = request.args.get('semester', type=int) or current_semester

    enrolled_subjects = [s for s in all_enrolled if s.get('semester') == selected_semester]
    selected_subject_id = request.args.get('subject_id', type=int)

    grades_data = []
    display_groups = []
    subject_info = None
    total_score = 0
    total_max = 0

    if selected_subject_id:
        if any(s['id'] == selected_subject_id for s in enrolled_subjects):
            # --- FEEDBACK INTERCEPT LOGIC ---
            active_form = db.execute_query('''
                SELECT * FROM feedback_forms 
                WHERE semester = %s::varchar 
                  AND CURRENT_DATE BETWEEN start_date AND end_date
                LIMIT 1
            ''', (str(selected_semester),), fetch_one=True)

            if active_form:
                # Find if student has a specific teacher for this subject
                teacher_for_subject = db.execute_query('''
                    SELECT u.*, t.id as real_teacher_id FROM teacher_assignments ta
                    JOIN teachers t ON ta.teacher_id = t.id
                    JOIN users u ON u.id = t.user_id
                    WHERE ta.subject_id = %s
                      AND (ta.class_id IS NULL OR ta.class_id = %s)
                    LIMIT 1
                ''', (selected_subject_id, student.get('class_id', 0)), fetch_one=True)

                if teacher_for_subject:
                    already_submitted = db.execute_query('''
                        SELECT 1 FROM feedback_responses
                        WHERE form_id = %s AND student_id = %s AND subject_id = %s
                    ''', (active_form['id'], student['id'], selected_subject_id), fetch_one=True)

                    if not already_submitted:
                        import json
                        questions = active_form.get('questions', [])
                        if isinstance(questions, str):
                            try:
                                questions = json.loads(questions)
                            except:
                                questions = []
                        return render_template('student/feedback_intercept.html',
                                               student=student,
                                               form=active_form,
                                               questions=questions,
                                               teacher=teacher_for_subject,
                                               subject_info=next(s for s in enrolled_subjects if s['id'] == selected_subject_id),
                                               enrolled_subjects=enrolled_subjects,
                                               selected_semester=selected_semester,
                                               selected_subject_id=selected_subject_id,
                                               available_semesters=available_semesters,
                                               current_semester=current_semester)
            # --- END FEEDBACK INTERCEPT LOGIC ---

            raw_grades = db.get_student_grades_for_subject(student['id'], selected_subject_id) or []
            subject_info = next((s for s in enrolled_subjects if s['id'] == selected_subject_id), None)
            # Exclude 'final' component — shown separately after exam
            grades_data = [g for g in raw_grades if g.get('component_type') != 'final']
            display_groups = _build_grade_display_groups(grades_data)
            total_score, total_max = db._calc_grade_totals(grades_data)
        else:
            selected_subject_id = None

    return render_template('student/grades.html',
                           enrolled_subjects=enrolled_subjects,
                           selected_subject_id=selected_subject_id,
                           subject_info=subject_info,
                           grades_data=grades_data,
                           display_groups=display_groups,
                           total_score=total_score,
                           total_max=total_max,
                           student=student,
                           available_semesters=available_semesters,
                           selected_semester=selected_semester,
                           current_semester=current_semester)


# =============================================
# STUDENT - EXAM SIGNUP
# =============================================

@student_bp.route('/student/exams')
@login_required
def exams():
    """Redirect to combined signups page — exams tab."""
    return redirect(url_for('student.signups', tab='exams'))


@student_bp.route('/student/exams/signup/<int:subject_id>/<exam_type>', methods=['POST'])
@login_required
def exam_signup(subject_id, exam_type):
    """Sign up for an exam."""
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    if exam_type not in ('final', 'second_round'):
        return jsonify({'success': False, 'error': 'Invalid exam type'}), 400

    try:
        student = db.get_student_by_user_id(session['user_id'])
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        class_info = db.get_class_by_id(student['class_id']) if student.get('class_id') else None
        semester = (class_info['semester'] if class_info else None) or student.get('semester')

        effective_major_id = (
            student.get('major_id')
            or (class_info.get('major_id') if class_info else None)
            or session.get('major_id')
        )
        period = db.get_active_exam_period(semester, exam_type, major_id=effective_major_id) if semester else None
        if not period:
            return jsonify({'success': False, 'error': 'No active exam period for this type'}), 400

        eligible = db.get_exam_eligible_subjects(student['id'], exam_type, semester) or []
        subject_ids = [s['id'] for s in eligible if s.get('eligible')]
        if subject_id not in subject_ids:
            existing = db.get_exam_signup(student['id'], subject_id, exam_type)
            if existing:
                return jsonify({'success': True, 'message': 'Already signed up'})
            return jsonify({'success': False, 'error': 'Not eligible for this exam'}), 400

        db.signup_for_exam(student['id'], subject_id, exam_type)
        return jsonify({'success': True, 'message': 'Successfully signed up for exam'})
    except Exception as e:
        print(f"Error signing up for exam: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': 'Signup failed, please try again'}), 500


@student_bp.route('/student/exams/cancel/<int:subject_id>/<exam_type>', methods=['POST'])
@login_required
def exam_cancel(subject_id, exam_type):
    """Cancel an exam signup."""
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    if exam_type not in ('final', 'second_round'):
        return jsonify({'success': False, 'error': 'Invalid exam type'}), 400

    try:
        student = db.get_student_by_user_id(session['user_id'])
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        class_info = db.get_class_by_id(student['class_id']) if student.get('class_id') else None
        semester = (class_info['semester'] if class_info else None) or student.get('semester')

        effective_major_id = (
            student.get('major_id')
            or (class_info.get('major_id') if class_info else None)
            or session.get('major_id')
        )
        period = db.get_active_exam_period(semester, exam_type, major_id=effective_major_id) if semester else None
        if not period:
            return jsonify({'success': False, 'error': 'Exam period is not active'}), 400

        db.cancel_exam_signup(student['id'], subject_id, exam_type)
        return jsonify({'success': True, 'message': 'Exam signup cancelled'})
    except Exception as e:
        print(f"Error cancelling exam signup: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': 'Cancel failed, please try again'}), 500


# =============================================
# STUDENT - RESULTS / TRANSCRIPT
# =============================================

@student_bp.route('/student/results')
@login_required
def results():
    """View student final results/transcript — grouped by semester."""
    if session.get('role') != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.dashboard'))

    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    enrolled_subjects = db.get_enrolled_subjects_for_student(student['id']) or []

    grades_exist = False

    subjects_by_semester = {}
    for subj in enrolled_subjects:
        sem = subj.get('semester') or 0
        if sem not in subjects_by_semester:
            subjects_by_semester[sem] = []
        subjects_by_semester[sem].append(subj)

    semester_results = []
    grand_total_credits = 0
    grand_total_weighted = 0

    for sem in sorted(subjects_by_semester.keys()):
        if sem == 0:
            continue

        sem_subjects = subjects_by_semester[sem]
        results_list = []
        sem_credits_possible = 0
        sem_credits_earned = 0
        sem_has_published = False

        for subject in sem_subjects:
            current_grades_data = db.get_student_grades_for_subject(student['id'], subject['id']) or []
            if db.grade_rows_have_scores(current_grades_data):
                grades_exist = True

            grades_data = db.get_student_result_grades_for_subject(student['id'], subject['id']) or []
            if not db.grade_rows_have_scores(grades_data):
                continue

            sem_has_published = True

            # Use the canonical calculator — same rules as My Grades tab and signup eligibility.
            # This ensures all three views show the same number.
            total_score, total_max = db._calc_grade_totals(grades_data)

            percentage = (total_score / total_max * 100) if total_max > 0 else 0

            if percentage >= 97: letter_grade = 'A+'
            elif percentage >= 93: letter_grade = 'A'
            elif percentage >= 90: letter_grade = 'A-'
            elif percentage >= 87: letter_grade = 'B+'
            elif percentage >= 83: letter_grade = 'B'
            elif percentage >= 80: letter_grade = 'B-'
            elif percentage >= 77: letter_grade = 'C+'
            elif percentage >= 73: letter_grade = 'C'
            elif percentage >= 70: letter_grade = 'C-'
            elif percentage >= 67: letter_grade = 'D+'
            elif percentage >= 63: letter_grade = 'D'
            elif percentage >= 60: letter_grade = 'D-'
            else: letter_grade = 'F'

            passed = percentage >= 60
            credits = subject.get('credits') or 0
            weighted_score = round(percentage * credits / 100, 3)

            results_list.append({
                'subject_name': subject['name'],
                'credits': credits,
                'percentage': round(percentage, 1),
                'letter_grade': letter_grade,
                'weighted_score': weighted_score,
                'passed': passed
            })

            sem_credits_possible += credits
            if passed:
                sem_credits_earned += credits

        if sem_has_published:
            sem_weighted = round(sum(r['weighted_score'] for r in results_list), 3)
            year = 1 if sem <= 2 else 2
            semester_results.append({
                'semester': sem,
                'year': year,
                'results': results_list,
                'total_weighted_score': sem_weighted,
                'credits_possible': sem_credits_possible,
                'credits_earned': sem_credits_earned
            })
            if results_list:
                grand_total_credits += sem_credits_possible
                grand_total_weighted += sem_weighted

    return render_template('student/results.html',
                           student=student,
                           semester_results=semester_results,
                           grades_exist=grades_exist,
                           grand_total_weighted=round(grand_total_weighted, 3),
                           grand_total_credits=grand_total_credits)


# =============================================
# STUDENT - VIEW LECTURE FILES
# =============================================

@student_bp.route('/student/files')
@login_required
def files():
    """View lecture files for student's class."""
    if session.get('role') != 'student':
        return redirect(url_for('auth.dashboard'))

    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    files_list = []
    grouped_files = {}
    if student['class_id']:
        files_list = db.get_lecture_files_by_class(student['class_id']) or []
        for file in files_list:
            subject_name = file['subject_name']
            if subject_name not in grouped_files:
                grouped_files[subject_name] = []
            grouped_files[subject_name].append(file)

    return render_template('student/files.html',
                           files=files_list,
                           grouped_files=grouped_files,
                           student=student)


# =============================================
# STUDENT - MOODLE
# =============================================

@student_bp.route('/student/moodle')
@student_required
def moodle():
    """List student subjects for Moodle view"""
    student_id = session.get('student_id')
    user_id = session['user_id']
    if not student_id:
        st = db.get_student_by_user_id(user_id)
        if st:
            student_id = st['id']
            session['student_id'] = student_id

    subjects = db.get_enrolled_subjects_for_student(student_id) or []
    return render_template('student/moodle_list.html', subjects=subjects)

@student_bp.route('/student/moodle/<int:subject_id>')
@student_required
def moodle_view(subject_id):
    student_id = session.get('student_id')
    user_id = session['user_id']
    if not student_id:
        st = db.get_student_by_user_id(user_id)
        if st:
            student_id = st['id']
            session['student_id'] = student_id
            
    enrolled_subjects = db.get_enrolled_subjects_for_student(student_id) or []
    subject_row = next((sub for sub in enrolled_subjects if sub['id'] == subject_id), None)
    if not subject_row:
        return "You are not enrolled in this subject", 403

    class_id = request.args.get('class_id', type=int) or subject_row.get('class_id')
    if not class_id:
        return "Not enrolled in any class", 403
    
    subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    moodle_content = db.get_moodle_content(class_id, subject_id, student_id=student_id)
    
    return render_template(
        'student/moodle_view.html',
        subject=subject,
        class_id=class_id,
        moodle_content=moodle_content,
        student_id=student_id,
        current_time=datetime.now()
    )


@student_bp.route('/student/moodle/request/<int:request_id>/submit', methods=['POST'])
@student_required
def submit_moodle_request(request_id):
    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    request_row = db.get_moodle_request_by_id(request_id)
    if not request_row:
        flash('Request not found.', 'danger')
        return redirect(url_for('student.moodle'))

    if student['class_id'] != request_row['class_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.moodle'))

    enrolled_subjects = db.get_enrolled_subjects_for_student(student['id']) or []
    if not any(sub['id'] == request_row['subject_id'] for sub in enrolled_subjects):
        flash('Access denied.', 'danger')
        return redirect(url_for('student.moodle'))

    due_at = request_row.get('due_at')
    if due_at and due_at < datetime.now():
        flash('This request is closed. The due time has passed.', 'danger')
        return redirect(url_for('student.moodle_view', subject_id=request_row['subject_id'], class_id=request_row['class_id']))

    file = request.files.get('file')
    if not file or not file.filename:
        flash('Please choose a file to submit.', 'danger')
        return redirect(url_for('student.moodle_view', subject_id=request_row['subject_id'], class_id=request_row['class_id']))

    filename = secure_filename(file.filename)
    upload_dir = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        'moodle_submissions',
        f"request_{request_id}",
        f"student_{student['id']}"
    )
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = f"{int(time.time())}_{filename}"
    absolute_path = os.path.join(upload_dir, unique_filename)
    file.save(absolute_path)
    relative_path = os.path.relpath(absolute_path, current_app.config['UPLOAD_FOLDER'])
    file_size = os.path.getsize(absolute_path)
    file_type = file.content_type

    existing = db.get_moodle_request_submission_by_student(request_id, student['id'])
    db.upsert_moodle_request_submission(
        request_id=request_id,
        student_id=student['id'],
        file_name=filename,
        file_path=relative_path,
        file_type=file_type,
        file_size=file_size
    )
    if existing:
        old_file_path = _resolve_uploaded_path(existing.get('file_path'))
        if old_file_path and os.path.exists(old_file_path) and os.path.normpath(old_file_path) != os.path.normpath(absolute_path):
            os.remove(old_file_path)
    flash('Submission saved successfully.', 'success')
    return redirect(url_for('student.moodle_view', subject_id=request_row['subject_id'], class_id=request_row['class_id']))


@student_bp.route('/student/moodle/file/<int:file_id>')
@student_required
def moodle_file_viewer(file_id):
    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    file_info = db.get_lecture_file_by_id(file_id)
    if not file_info:
        flash('File not found.', 'danger')
        return redirect(url_for('student.moodle'))

    if student['class_id'] != file_info['class_id']:
        flash('Access denied. This file is not for your class.', 'danger')
        return redirect(url_for('student.moodle'))

    subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (file_info['subject_id'],), fetch_one=True)
    view_payload = _get_student_file_view_payload(file_info)

    return render_template(
        'student/moodle_file_viewer.html',
        file_info=file_info,
        subject=subject,
        class_id=file_info['class_id'],
        view_payload=view_payload
    )


@student_bp.route('/student/files/download/<int:file_id>')
@student_required
def download_file(file_id):
    """Student alias for the shared lecture-file download route."""
    return redirect(url_for('teacher.download_file', file_id=file_id))


@student_bp.route('/student/files/view/<int:file_id>')
@student_required
def view_file(file_id):
    """Student alias for the shared lecture-file inline view route."""
    return redirect(url_for('teacher.view_file', file_id=file_id))

@student_bp.route('/student/api/ping_engagement', methods=['POST'])
@student_required
def api_ping_engagement():
    try:
        data = request.get_json()
        action = data.get('action', 'ping')
        subject_id = data.get('subject_id')
        class_id = data.get('class_id')
        active_seconds = data.get('active_seconds', 30)
        session_id = data.get('session_id')
        
        student_id = session.get('student_id')
        if not student_id:
           st = db.get_student_by_user_id(session['user_id'])
           student_id = st['id']

        subject_id = int(subject_id)
        class_id = int(class_id)

        if action == 'start':
            engagement_session_id = db.start_student_engagement_session(
                student_id,
                subject_id,
                class_id,
                data.get('resource_title'),
                data.get('resource_type')
            )
            return jsonify({"success": True, "session_id": engagement_session_id})

        if action == 'stop':
            if session_id:
                db.stop_student_engagement_session(int(session_id), student_id)
            return jsonify({"success": True})

        if action == 'resource':
            if session_id:
                db.set_student_engagement_resource(
                    int(session_id),
                    student_id,
                    data.get('resource_title'),
                    data.get('resource_type')
                )
            return jsonify({"success": True})

        if not session_id:
            engagement_session_id = db.start_student_engagement_session(
                student_id,
                subject_id,
                class_id,
                data.get('resource_title'),
                data.get('resource_type')
            )
            db.ping_student_engagement_session(engagement_session_id, student_id, int(active_seconds))
            return jsonify({"success": True, "session_id": engagement_session_id})

        db.ping_student_engagement_session(int(session_id), student_id, int(active_seconds))
        return jsonify({"success": True, "session_id": int(session_id)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@student_bp.route('/student/feedback')
@student_required
def student_feedback_list():
    import db
    student = db.get_student_by_user_id(session['user_id'])
    sem = student['semester']
    
    forms = db.execute_query('''
        SELECT f.* 
        FROM feedback_forms f
        WHERE f.semester = %s
          AND CURRENT_DATE BETWEEN f.start_date AND f.end_date
    ''', (sem,), fetch_all=True) or []
    
    return render_template('student/feedback_list.html', forms=forms)

@student_bp.route('/student/feedback/<int:form_id>')
@student_required
def student_feedback_form(form_id):
    import db
    import json
    student = db.get_student_by_user_id(session['user_id'])
    
    form = db.execute_query('SELECT * FROM feedback_forms WHERE id = %s', (form_id,), fetch_one=True)
    if not form:
        flash("Invalid form.", "danger")
        return redirect('/student/feedback')
        
    teachers = db.execute_query('''
        SELECT DISTINCT t.id as teacher_id, tu.full_name as teacher_name, sub.id as subject_id, sub.name as subject_name
        FROM student_enrollments se
        JOIN subjects sub ON se.subject_id = sub.id
        JOIN teacher_assignments ta ON ta.subject_id = sub.id
        JOIN teachers t ON ta.teacher_id = t.id
        JOIN users tu ON t.user_id = tu.id
        WHERE se.student_id = %s AND sub.semester = %s
          AND (ta.class_id IS NULL OR ta.class_id = %s)
    ''', (student['id'], form['semester'], student['class_id']), fetch_all=True) or []
    
    return render_template('student/feedback_form.html', form=form, teachers=teachers, questions=form['questions'])

@student_bp.route('/student/feedback/submit/<int:form_id>', methods=['POST'])
@student_required
def student_feedback_submit(form_id):
    import db
    import json
    student = db.get_student_by_user_id(session['user_id'])
    form = db.execute_query('SELECT * FROM feedback_forms WHERE id = %s', (form_id,), fetch_one=True)
    qs = form['questions'] if form else []
    
    submitted_pairs = set()
    for key, val in request.form.items():
        if key.startswith('rating_'):
            parts = key.split('_')
            sub_id = int(parts[1])
            tch_id = int(parts[2])
            
            pair = (sub_id, tch_id)
            if pair in submitted_pairs: continue
            submitted_pairs.add(pair)
            
            ratings = []
            for idx, q in enumerate(qs):
                r_val = request.form.get(f'rating_{sub_id}_{tch_id}_{idx}')
                ratings.append(int(r_val) if r_val else 1)
                
            comments = request.form.get(f'comments_{sub_id}_{tch_id}', '')
            
            db.execute_query('''
                INSERT INTO feedback_responses (form_id, student_id, teacher_id, subject_id, ratings, comments)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (form_id, student['id'], tch_id, sub_id, json.dumps(ratings), comments))
            
    flash("Thank you! Feedback submitted successfully.", "success")
    
    if request.form.get('return_to_grades') == '1':
        return redirect(url_for('student.grades', subject_id=request.form.get('ratings_subject_id'), semester=form['semester']))
        
    return redirect('/student/feedback')
