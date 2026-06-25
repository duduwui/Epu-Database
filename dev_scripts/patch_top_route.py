import sys
import re

with open("blueprints/admin.py", "r", encoding="utf-8") as f:
    text = f.read()

route_code = """
@admin_bp.route('/admin/top-students', methods=['GET'])
@admin_required
def top_students():
    semester = request.args.get('semester', type=int)
    class_id = request.args.get('class_id', type=int)
    shift = request.args.get('shift', '')
    
    classes = db.get_classes() or []
    results = []
    
    if semester or class_id or shift:
        results = db.get_top_students_results(semester=semester, class_id=class_id, shift=shift)
        
    return render_template('admin/top_students.html', 
                            results=results,
                            classes=classes,
                            selected_semester=semester,
                            selected_class_id=class_id,
                            selected_shift=shift)
"""

if "def top_students(" not in text:
    text += "\n" + route_code + "\n"
    with open("blueprints/admin.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("success")
else:
    print("already exists")
