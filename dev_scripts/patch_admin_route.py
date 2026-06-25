with open('blueprints/admin.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Update admin.py to fetch classes based on subject
old_route = """    selected_subject_id = request.args.get('subject_id', type=int)
    if not selected_subject_id and subjects:
        selected_subject_id = subjects[0]['subject_id']
        
    current_students = []
    questions_list = []
    if selected_subject_id:
        current_students, questions_list = db.get_feedback_teacher_detail_current(teacher_id, selected_subject_id, major_id)"""

new_route = """    selected_subject_id = request.args.get('subject_id', type=int)
    if not selected_subject_id and subjects:
        selected_subject_id = subjects[0]['subject_id']
        
    classes = []
    selected_class_id = request.args.get('class_id', type=int)
    
    current_students = []
    questions_list = []
    
    if selected_subject_id:
        classes = db.get_feedback_teacher_classes(teacher_id, selected_subject_id, major_id)
        if not selected_class_id and classes:
            selected_class_id = classes[0]['class_id']
            
        current_students, questions_list = db.get_feedback_teacher_detail_current(teacher_id, selected_subject_id, selected_class_id, major_id)"""

if 'selected_class_id' not in text:
    text = text.replace(old_route, new_route)
    
    # Also update the render_template call
    text = text.replace("                           selected_subject_id=selected_subject_id,", "                           selected_subject_id=selected_subject_id,\n                           classes=classes,\n                           selected_class_id=selected_class_id,")

    with open('blueprints/admin.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Patched admin.py")
