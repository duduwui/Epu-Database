import os

file_path = 'templates/admin/feedback/teacher_history.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '{% for year_group in history %}',
    '{% for year_group in history %}\n    {% set year_loop = loop %}'
)

content = content.replace(
    '{% for cls in year_group.classes %}',
    '{% for cls in year_group.classes %}\n                    {% set class_loop = loop %}'
)

content = content.replace(
    '{{ loop.parent.loop.parent.loop.index }}-{{ loop.parent.loop.index }}-{{ loop.index }}',
    '{{ year_loop.index }}-{{ class_loop.index }}-{{ loop.index }}'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Template fixed.")
