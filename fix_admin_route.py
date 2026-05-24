import os

with open('blueprints/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx_start = content.find("@admin_bp.route('/admin/feedback/results'")
if idx_start != -1:
    idx_end = content.find("@admin_bp.route('/admin/feedback/teacher/", idx_start)
    if idx_end != -1:
        new_route = """@admin_bp.route('/admin/feedback/results', methods=['GET'])
@admin_required
def feedback_results():
    from flask import session, render_template
    import db
    
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    major_id = user.get('major_id') if user else None
    
    summary = db.get_feedback_summary(major_id)
    return render_template("admin/feedback/results.html", summary=summary)

"""
        content = content[:idx_start] + new_route + content[idx_end:]
        with open('blueprints/admin.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("admin.py fixed")
    else:
        print("could not find end")
else:
    print("could not find start")
