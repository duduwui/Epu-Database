with open('templates/admin/feedback/teacher_details.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_form = """        <form method="GET" class="row gx-2 gy-2 align-items-end">
            <div class="col-md-4">
                <label class="form-label small fw-medium text-navy">Filter by Subject</label>
                <select name="subject_id" class="form-select form-select-sm" onchange="this.form.submit()">
                    {% for subj in subjects %}
                    <option value="{{ subj.subject_id }}" {% if subj.subject_id == selected_subject_id %}selected{% endif %}>
                        {{ subj.subject_name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
        </form>"""

new_form = """        <form method="GET" class="row gx-2 gy-2 align-items-end">
            <div class="col-md-4">
                <label class="form-label small fw-medium text-navy">Filter by Subject</label>
                <select name="subject_id" class="form-select form-select-sm" onchange="this.form.submit()">
                    {% for subj in subjects %}
                    <option value="{{ subj.subject_id }}" {% if subj.subject_id == selected_subject_id %}selected{% endif %}>
                        {{ subj.subject_name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            
            {% if classes %}
            <div class="col-md-4">
                <label class="form-label small fw-medium text-navy">Filter by Class</label>
                <select name="class_id" class="form-select form-select-sm" onchange="this.form.submit()">
                    {% for cls in classes %}
                    <option value="{{ cls.class_id }}" {% if cls.class_id == selected_class_id %}selected{% endif %}>
                        {{ cls.class_name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            {% endif %}
        </form>"""

if '{% if classes %}' not in text:
    text = text.replace(old_form, new_form)
    
    # Update Empty Data message for clarity
    text = text.replace("No active feedback submitted by students for this subject currently.", "No active feedback submitted by students for this class/subject currently.")
    
    with open('templates/admin/feedback/teacher_details.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Patched teacher_details HTML template")

