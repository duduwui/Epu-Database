import re

with open('blueprints/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update feedback_teacher_history
old_history = '''def feedback_teacher_history(teacher_id):
    from flask import request, flash, redirect, render_template
    import db
    
    teacher = db.execute_query("SELECT full_name FROM users WHERE id = %s", (teacher_id,), fetch_one=True)
    if not teacher:
        flash("Teacher not found", "danger")
        return redirect('/admin/feedback/results')
        
    subjects = db.get_feedback_teacher_subjects(teacher_id)
    selected_subject_id = request.args.get('subject_id', type=int)
    if not selected_subject_id and subjects:
        selected_subject_id = subjects[0]['subject_id']
        
    history = []
    if selected_subject_id:
        history = db.get_feedback_teacher_history_by_year(teacher_id, selected_subject_id)
        
    return render_template("admin/feedback/teacher_history.html",
                           teacher_name=teacher['full_name'],
                           teacher_id=teacher_id,
                           subjects=subjects,
                           selected_subject_id=selected_subject_id,
                           history=history)'''

new_history = '''def feedback_teacher_history(teacher_id):
    from flask import request, flash, redirect, render_template
    import db
    
    teacher = db.execute_query("SELECT full_name FROM users WHERE id = %s", (teacher_id,), fetch_one=True)
    if not teacher:
        flash("Teacher not found", "danger")
        return redirect('/admin/feedback/results')
        
    subjects = db.get_feedback_teacher_subjects(teacher_id)
    selected_subject_id = request.args.get('subject_id', type=int)
    if not selected_subject_id and subjects:
        selected_subject_id = subjects[0]['subject_id']
        
    classes = []
    if selected_subject_id:
        classes = db.execute_query("""
            SELECT DISTINCT c.id as class_id, c.name as class_name 
            FROM feedback_responses r 
            JOIN classes c ON r.snapshot_class_id = c.id 
            WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s) 
              AND r.subject_id = %s
            ORDER BY c.name
        """, (teacher_id, selected_subject_id), fetch_all=True) or []
        
    selected_class_id = request.args.get('class_id', type=int)
    
    history = []
    if selected_subject_id:
        history = db.get_feedback_teacher_history_by_year(teacher_id, selected_subject_id, selected_class_id)
        
    return render_template("admin/feedback/teacher_history.html",
                           teacher_name=teacher['full_name'],
                           teacher_id=teacher_id,
                           subjects=subjects,
                           selected_subject_id=selected_subject_id,
                           classes=classes,
                           selected_class_id=selected_class_id,
                           history=history)'''

content = content.replace(old_history, new_history)

# Remove analytics route
content = re.sub(r"@admin_bp\.route\('/admin/feedback/analytics', methods=\['GET'\]\)\n@admin_required\ndef feedback_analytics\(\):\n(?:    .*?\n)*", '', content)

with open('blueprints/admin.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated admin.py")