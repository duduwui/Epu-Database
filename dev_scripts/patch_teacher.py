import os

teacher_moodle_routes = '''

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
    subject = execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    moodle_content = db.get_moodle_content(class_id, subject_id)
    return render_template('teacher/moodle_hub.html', subject=subject, class_id=class_id, moodle_content=moodle_content)

@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/add_week', methods=['POST'])
@teacher_required
def moodle_add_week(subject_id, class_id):
    teacher = db.get_teacher_by_user_id(session['user_id'])
    title = request.form.get('title')
    display_order = request.form.get('display_order', 0)
    db.create_moodle_week(class_id, subject_id, teacher['id'], title, display_order)
    flash(f"Moodle week added successfully.", "success")
    return redirect(url_for('teacher.moodle_hub', subject_id=subject_id, class_id=class_id))

@teacher_bp.route('/teacher/moodle/<int:subject_id>/<int:class_id>/engagement')
@teacher_required
def moodle_engagement(subject_id, class_id):
    query = """
        SELECT s.student_name, e.access_date, e.time_spent_seconds 
        FROM student_engagement e
        JOIN students s ON e.student_id = s.id
        WHERE e.subject_id = %s AND e.class_id = %s
        ORDER BY e.access_date DESC, e.time_spent_seconds DESC
    """
    stats = db.execute_query(query, (subject_id, class_id), fetch_all=True) or []
    subject = execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
    return render_template('teacher/moodle_engagement.html', stats=stats, subject=subject, class_id=class_id)
'''

with open('blueprints/teacher.py', 'r', encoding='utf-8') as f:
    t_content = f.read()

# I need to add execute_query to teacher if it isn't defined explicitly but wait, db.execute_query is safe. Let me replace execute_query with db.execute_query.
teacher_moodle_routes = teacher_moodle_routes.replace('execute_query(', 'db.execute_query(')

if '# TEACHER - MOODLE HUB' not in t_content:
    with open('blueprints/teacher.py', 'a', encoding='utf-8') as f:
        f.write(teacher_moodle_routes)
    print("Added teacher moodle routes")

