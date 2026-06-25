import re

with open("templates/admin/feedback/teacher_history.html", "r", encoding="utf-8") as f:
    text = f.read()

old_block = """                <div class="accordion-body p-0">
                    
                    {% for cls in year_group.classes %}
                    {% set class_loop = loop %}
                    {% set class_loop = loop %}
                    <div class="card border-0 mb-0 {% if not loop.first %}border-top{% endif %}">"""

new_block = """                <div class="accordion-body p-0">
                    
                    {% for sem in year_group.semesters %}
                    {% set sem_loop = loop %}
                    <div class="p-2 border-bottom fw-bold text-navy" style="background: #e9ecef;">
                        <i class="bi bi-calendar-range me-2 opacity-75"></i> Semester {{ sem.semester }}
                    </div>
                    
                    {% for cls in sem.classes %}
                    {% set class_loop = loop %}
                    <div class="card border-0 mb-0 {% if not loop.first %}border-top{% endif %}">"""

text = text.replace(old_block, new_block)

old_end = """                        </div>
                    </div>
                    {% endfor %}
                    
                </div>"""

new_end = """                        </div>
                    </div>
                    {% endfor %}
                    {% endfor %}
                    
                </div>"""

text = text.replace(old_end, new_end)

# Also replace collapse-student- IDs:
text = text.replace("collapse-student-{{ year_loop.index }}-{{ class_loop.index }}-{{ loop.index }}", "collapse-student-{{ year_loop.index }}-{{ sem_loop.index }}-{{ class_loop.index }}-{{ loop.index }}")

with open("templates/admin/feedback/teacher_history.html", "w", encoding="utf-8") as f:
    f.write(text)

print("success")