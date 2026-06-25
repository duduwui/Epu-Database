import os
import re

with open('templates/base.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace Teacher Menu
teacher_old_h = r'<li class="nav-item">\s*<a class="nav-link" href="{{ url_for\(\'teacher\.homework\'\) }}">\s*<i class="bi bi-journal-text"><\/i>\s*<span>{{ t\(\'Homework\'\) }}<\/span>\s*<\/a>\s*<\/li>'
teacher_old_t = r'<li class="nav-item">\s*<a class="nav-link" href="{{ url_for\(\'teacher\.topics\'\) }}">\s*<i class="bi bi-list-task"><\/i>\s*<span>{{ t\(\'Topics\'\) }}<\/span>\s*<\/a>\s*<\/li>'
teacher_old_f = r'<li class="nav-item">\s*<a class="nav-link" href="{{ url_for\(\'teacher\.files\'\) }}">\s*<i class="bi bi-folder2-open"><\/i>\s*<span>{{ t\(\'Files\'\) }}<\/span>\s*<\/a>\s*<\/li>'

html = re.sub(teacher_old_t, '', html, flags=re.IGNORECASE)
html = re.sub(teacher_old_f, '', html, flags=re.IGNORECASE)
moodle_teacher_html = '''<li class="nav-item">
            <a class="nav-link" href="{{ url_for('teacher.moodle') }}">
              <i class="bi bi-mortarboard-fill"></i>
              <span>{{ t('Moodle Hub') }}</span>
            </a>
          </li>'''
html = re.sub(teacher_old_h, moodle_teacher_html, html, flags=re.IGNORECASE)

# Replace Student Menu
student_old_f = r'<li class="nav-item">\s*<a class="nav-link" href="{{ url_for\(\'student\.files\'\) }}">\s*<i class="bi bi-folder"><\/i>\s*<span>{{ t\(\'Files\'\) }}<\/span>\s*<\/a>\s*<\/li>'
student_old_h = r'<li class="nav-item">\s*<a class="nav-link" href="{{ url_for\(\'student\.homework\'\) }}">\s*<i class="bi bi-journal-text"><\/i>\s*<span>{{ t\(\'Homework\'\) }}<\/span>\s*<\/a>\s*<\/li>'

html = re.sub(student_old_h, '', html, flags=re.IGNORECASE)
moodle_student_html = '''<li class="nav-item">
            <a class="nav-link" href="{{ url_for('student.moodle') }}">
              <i class="bi bi-book"></i>
              <span>{{ t('Moodle View') }}</span>
            </a>
          </li>'''
html = re.sub(student_old_f, moodle_student_html, html, flags=re.IGNORECASE)

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Updated base.html sidebar!")
