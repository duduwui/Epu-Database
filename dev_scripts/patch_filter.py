import re

with open("templates/admin/students.html", "r", encoding="utf-8") as f:
    text = f.read()

old_year = """                <div class="col-6 col-md-2">
                    <label class="form-label mb-1" style="font-size:0.8rem;">Year</label>
                    <select name="year" id="filterYear" class="form-select form-select-sm" onchange="updateSemesterFilter(); applyFilters()">
                        <option value="">All Years</option>
                        <option value="1" {{ 'selected' if request.args.get('year') == '1' }}>Year 1</option>
                        <option value="2" {{ 'selected' if request.args.get('year') == '2' }}>Year 2</option>
                    </select>
                </div>"""

new_year = """                <!-- Year filter removed -->"""

if old_year in text:
    text = text.replace(old_year, new_year)
    
old_sem = """                <div class="col-6 col-md-2">
                    <label class="form-label mb-1" style="font-size:0.8rem;">Semester</label>
                    <select name="semester" id="filterSemester" class="form-select form-select-sm" onchange="applyFilters()">
                        <option value="">All Semesters</option>
                        {% set sel_year = request.args.get('year', '') %}
                        {% set sel_sem = request.args.get('semester', '') %}
                        {% if sel_year == '1' %}
                        <option value="1" {{ 'selected' if sel_sem == '1' }}>Sem 1</option>
                        <option value="2" {{ 'selected' if sel_sem == '2' }}>Sem 2</option>
                        {% elif sel_year == '2' %}
                        <option value="3" {{ 'selected' if sel_sem == '3' }}>Sem 3</option>
                        <option value="4" {{ 'selected' if sel_sem == '4' }}>Sem 4</option>
                        {% else %}
                        <option value="1" {{ 'selected' if sel_sem == '1' }}>Sem 1</option>
                        <option value="2" {{ 'selected' if sel_sem == '2' }}>Sem 2</option>
                        <option value="3" {{ 'selected' if sel_sem == '3' }}>Sem 3</option>
                        <option value="4" {{ 'selected' if sel_sem == '4' }}>Sem 4</option>
                        {% endif %}
                    </select>
                </div>"""

new_sem = """                <div class="col-6 col-md-2">
                    <label class="form-label mb-1" style="font-size:0.8rem;">Semester</label>
                    <select name="semester" id="filterSemester" class="form-select form-select-sm" onchange="applyFilters()">
                        <option value="">All Semesters</option>
                        {% set sel_sem = request.args.get('semester', '') %}
                        <option value="1" {{ 'selected' if sel_sem == '1' }}>Sem 1</option>
                        <option value="2" {{ 'selected' if sel_sem == '2' }}>Sem 2</option>
                        <option value="3" {{ 'selected' if sel_sem == '3' }}>Sem 3</option>
                        <option value="4" {{ 'selected' if sel_sem == '4' }}>Sem 4</option>
                    </select>
                </div>"""

if old_sem in text:
    text = text.replace(old_sem, new_sem)
    
old_script = """function updateSemesterFilter() {
    const year = document.getElementById('filterYear').value;
    const semSelect = document.getElementById('filterSemester');
    const currentVal = semSelect.value;
    semSelect.innerHTML = '<option value="">All Semesters</option>';
    if (year === '1') {
        semSelect.innerHTML += '<option value="1">Sem 1</option><option value="2">Sem 2</option>';
    } else if (year === '2') {
        semSelect.innerHTML += '<option value="3">Sem 3</option><option value="4">Sem 4</option>';
    } else {
        semSelect.innerHTML += '<option value="1">Sem 1</option><option value="2">Sem 2</option><option value="3">Sem 3</option><option value="4">Sem 4</option>';
    }
    if (["1","2","3","4"].includes(currentVal)) {
        semSelect.value = currentVal;
    }
}"""

if old_script in text:
    text = text.replace(old_script, "// updateSemesterFilter removed")

with open("templates/admin/students.html", "w", encoding="utf-8") as f:
    f.write(text)
print("success")
