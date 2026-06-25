with open('db.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'query += " ORDER BY study_year DESC, semester DESC LIMIT 1"',
    'query += " ORDER BY created_at DESC LIMIT 1"'
)

text = text.replace(
    'query_form += " ORDER BY study_year DESC, created_at DESC LIMIT 1"',
    'query_form += " ORDER BY created_at DESC LIMIT 1"'
)

with open('db.py', 'w', encoding='utf-8') as f:
    f.write(text)
