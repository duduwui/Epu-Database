import os

student_routes = '''

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

    subjects = db.get_student_subjects(student_id) or []
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
            
    # Need to find class_id for this student
    query = """
        SELECT class_id FROM student_enrollments
        WHERE student_id = %s
        LIMIT 1
    """
    enrollment = db.execute_query(query, (student_id,), fetch_one=True)
    if not enrollment:
        return "Not enrolled in any class", 403
    class_id = enrollment['class_id']
    
    subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    moodle_content = db.get_moodle_content(class_id, subject_id)
    
    return render_template('student/moodle_view.html', subject=subject, class_id=class_id, moodle_content=moodle_content, student_id=student_id)

@student_bp.route('/student/api/ping_engagement', methods=['POST'])
@student_required
def api_ping_engagement():
    try:
        data = request.get_json()
        subject_id = data.get('subject_id')
        class_id = data.get('class_id')
        active_seconds = data.get('active_seconds', 30)
        
        student_id = session.get('student_id')
        if not student_id:
           st = db.get_student_by_user_id(session['user_id'])
           student_id = st['id']

        # Ensure correct datatypes
        db.record_student_engagement(student_id, int(subject_id), int(class_id), int(active_seconds))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

'''

with open('blueprints/student.py', 'r', encoding='utf-8') as f:
    s_content = f.read()

if '# STUDENT - MOODLE' not in s_content:
    with open('blueprints/student.py', 'a', encoding='utf-8') as f:
        f.write(student_routes)
    print("Added student moodle routes")

