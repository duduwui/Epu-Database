import sys

content = open('blueprints/admin.py', 'r', encoding='utf-8').read()
start_idx = content.find('@admin_bp.route(\'/admin/feedback/results\', methods=[\'GET\'])')
end_idx = content.find('@admin_bp.route(\'/admin/users/add-ajax\', methods=[\'POST\'])')

if start_idx != -1 and end_idx != -1:
    new_code = '''@admin_bp.route('/admin/feedback/results', methods=['GET'])
@admin_required
def feedback_results():
    from flask import request, session, render_template
    import db
    
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    major_id = user.get('major_id') if user else None

    study_years = db.get_feedback_study_years(major_id)
    selected_year = request.args.get('study_year')
    if not selected_year and study_years:
        selected_year = study_years[0]
        
    selected_sem = request.args.get('semester', '')
    
    summary = []
    if selected_year:
        summary = db.get_feedback_summary(selected_year, selected_sem, major_id)
        
    return render_template("admin/feedback/results.html", 
                           summary=summary,
                           study_years=study_years,
                           selected_year=selected_year,
                           selected_sem=selected_sem)

@admin_bp.route('/admin/feedback/teacher/<int:teacher_id>', methods=['GET'])
@admin_required
def feedback_teacher_details(teacher_id):
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
    current_details = []
    questions_list = []
    
    if selected_subject_id:
        history = db.get_feedback_teacher_history(teacher_id, selected_subject_id)
        
        selected_year = request.args.get('study_year')
        if not selected_year and history:
            selected_year = history[0]['study_year']
            
        if selected_year:
            current_details, questions_list = db.get_feedback_teacher_detail(teacher_id, selected_subject_id, selected_year)

    return render_template("admin/feedback/teacher_details.html",
                           teacher_name=teacher['full_name'],
                           teacher_id=teacher_id,
                           subjects=subjects,
                           selected_subject_id=selected_subject_id,
                           selected_year=selected_year,
                           history=history,
                           current_details=current_details,
                           questions_list=questions_list)

'''
    open('blueprints/admin.py', 'w', encoding='utf-8').write(content[:start_idx] + new_code + content[end_idx:])
    print('SUCCESS')
else:
    print('FAILED')
