import os

paths = [
    'templates/admin/class_students.html',
    'templates/admin/dashboard.html',
    'templates/student/dashboard.html',
    'templates/teacher/take_attendance.html',
    'templates/teacher/schedule.html'
]

for p in paths:
    if not os.path.exists(p): continue
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '<div class="table-responsive">' not in content:
        c = content.replace('<table', '<div class="table-responsive">\n<table', 1)
        c = c.replace('</table>', '</table>\n</div>', 1)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        print('Wrapped table in', p)

