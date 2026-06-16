with open('templates/profile/_sidebar.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '<a class="profile-side-sublink" href="#">Researches</a>',
    '<a class="profile-side-sublink" href="{{ url_for(\'profile.researches_section\', section=\'research\') }}">Researches</a>'
).replace(
    '<a class="profile-side-sublink" href="#">Books</a>',
    '<a class="profile-side-sublink" href="{{ url_for(\'profile.researches_section\', section=\'book\') }}">Books</a>'
).replace(
    '<a class="profile-side-sublink" href="#">Grants</a>',
    '<a class="profile-side-sublink" href="{{ url_for(\'profile.researches_section\', section=\'grant\') }}">Grants</a>'
)

with open('templates/profile/_sidebar.html', 'w', encoding='utf-8') as f:
    f.write(text)
