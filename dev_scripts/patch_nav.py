import re

with open("templates/admin/students.html", "r", encoding="utf-8") as f:
    text = f.read()

old_nav = """                <a href="{{ url_for('admin.assign_sections') }}" class="btn btn-outline-primary">
                    <i class="bi bi-diagram-3 me-1"></i>Assign Classes
                </a>"""
                
new_nav = """                <a href="{{ url_for('admin.top_students') }}" class="btn btn-outline-success">
                    <i class="bi bi-trophy me-1"></i>Top Students Results
                </a>
                <a href="{{ url_for('admin.assign_sections') }}" class="btn btn-outline-primary">
                    <i class="bi bi-diagram-3 me-1"></i>Assign Classes
                </a>"""

if "bi-trophy" not in text:
    text = text.replace(old_nav, new_nav)
    with open("templates/admin/students.html", "w", encoding="utf-8") as f:
        f.write(text)
    print("success")
else:
    print("already exists")
