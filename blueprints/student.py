"""
Student blueprint — all student-facing routes.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import date
import db
from blueprints.auth import login_required

student_bp = Blueprint('student', __name__)


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
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.dashboard'))

    grades = db.get_grades_by_student(student['id']) or []

    homework = []
    weekly_topics = []
    schedule_data = None
    current_semester = None

    if student['class_id']:
        homework = db.get_homework_by_class(student['class_id']) or []
        weekly_topics = db.get_weekly_topics_by_class(student['class_id']) or []

    if student.get('semester') and student.get('shift') and student.get('section'):
        current_semester = student['semester']
        schedule_data = db.get_class_schedule_data(
            student['semester'],
            student['shift'],
            student['section'],
            major_id=session.get('major_id')
        )

    attendance = db.get_attendance_by_student(student['id'], semester=current_semester) or []

    today = date.today().isoformat()
    return render_template('student/dashboard.html',
                           student=student,
                           attendance=attendance,
                           grades=grades,
                           homework=homework,
                           weekly_topics=weekly_topics,
                           schedule_data=schedule_data,
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
            'SELECT year, semester, section, shift FROM classes WHERE id = %s',
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
    if semester:
        enrollment_period = db.get_active_enrollment_period(semester)
        enrollment_active = enrollment_period is not None
    subjects = db.get_available_subjects_for_student(student['id'], semester) or []

    final_period = db.get_active_exam_period(semester, 'final') if semester else None
    second_round_period = db.get_active_exam_period(semester, 'second_round') if semester else None
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
        if not db.is_enrollment_active(semester):
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
        if not db.is_enrollment_active(semester):
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
    """Build display groups for student grades.
    Paired components share a pair_group — merged into one Paired Average block."""
    SUM_TYPES = {'midterm'}
    pair_group_items = {}
    non_paired_by_type = {}
    for g in grades_data:
        pg = g.get('pair_group')
        ct = g.get('component_type')
        if pg is not None:
            pair_group_items.setdefault(pg, []).append(g)
        else:
            non_paired_by_type.setdefault(ct, []).append(g)

    display_groups = []
    seen_pgs = set()
    seen_cts = set()
    for g in grades_data:
        pg = g.get('pair_group')
        ct = g.get('component_type')
        if pg is not None:
            if pg not in seen_pgs:
                seen_pgs.add(pg)
                items = pair_group_items[pg]
                scores = [float(i.get('score') or 0) for i in items]
                maxes = [float(i['max_score']) for i in items]
                n = len(items)
                display_groups.append({
                    'is_paired': True,
                    'label': 'Paired Average',
                    'rows': items,
                    'subtotal_score': round(sum(scores) / n, 1) if n else 0,
                    'subtotal_max': round(sum(maxes) / n, 1) if n else 0,
                })
        else:
            if ct not in seen_cts:
                seen_cts.add(ct)
                items = non_paired_by_type[ct]
                n = len(items)
                s_sum = sum(float(i.get('score') or 0) for i in items)
                m_sum = sum(float(i['max_score']) for i in items)
                if ct in SUM_TYPES:
                    s, m = s_sum, m_sum
                else:
                    s = s_sum / n if n else 0
                    m = m_sum / n if n else 0
                display_groups.append({
                    'is_paired': False,
                    'label': ct.replace('_', ' ').title(),
                    'component_type': ct,
                    'rows': items,
                    'subtotal_score': round(s, 1),
                    'subtotal_max': round(m, 1),
                })
    return display_groups


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
            raw_grades = db.get_student_grades_for_subject(student['id'], selected_subject_id) or []
            subject_info = next((s for s in enrolled_subjects if s['id'] == selected_subject_id), None)
            grades_data = [g for g in raw_grades if g.get('component_type') != 'final']
            display_groups = _build_grade_display_groups(grades_data)
            total_score = round(sum(g['subtotal_score'] for g in display_groups), 1)
            total_max = round(sum(g['subtotal_max'] for g in display_groups), 1)
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

        period = db.get_active_exam_period(semester, exam_type) if semester else None
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

        period = db.get_active_exam_period(semester, exam_type) if semester else None
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

    sum_types = ['midterm', 'final']

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
            if subject.get('results_published'):
                sem_has_published = True

            grades_data = db.get_student_grades_for_subject(student['id'], subject['id']) or []
            if not grades_data:
                continue
            grades_exist = True

            if not subject.get('results_published'):
                continue

            grouped = {}
            for grade in grades_data:
                type_key = grade['component_type']
                if type_key not in grouped:
                    grouped[type_key] = []
                grouped[type_key].append(grade)

            total_score = 0
            total_max = 0

            for component_type, group_grades in grouped.items():
                group_total_score = sum(float(g['score'] or 0) for g in group_grades)
                group_total_max = sum(float(g['max_score']) for g in group_grades)
                group_count = len(group_grades)

                if component_type in sum_types:
                    total_score += group_total_score
                    total_max += group_total_max
                elif group_count > 0:
                    total_score += group_total_score / group_count
                    total_max += group_total_max / group_count

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
