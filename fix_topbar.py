from pathlib import Path

for file_name in ['dashboard.html', 'edit.html', 'scientific_titles.html', 'section_records.html']:
    p = Path('templates/profile') / file_name
    if p.exists():
        content = p.read_text(encoding='utf-8')
        old = "href=\"{{ url_for('profile.public_teacher_profile', staff_id=teacher.staff_id) }}\" target=\"_blank\">View my profile</a>"
        new = "href=\"{% if teacher.staff_id %}{{ url_for('profile.public_teacher_profile', staff_id=teacher.staff_id) }}{% else %}#{% endif %}\" target=\"_blank\" {% if not teacher.staff_id %}onclick=\"alert('Please set your Staff ID in Edit Profile first.'); return false;\"{% endif %}>View my profile</a>"
        if old in content:
            p.write_text(content.replace(old, new), encoding='utf-8')
            print(f"Fixed {file_name}")
