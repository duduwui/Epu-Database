import re
from pathlib import Path

profile_py = Path("db/profile.py")
content = profile_py.read_text(encoding="utf-8")

if "'researches':" not in content:
    old_code = r"'memberships': \['organization_name', 'link', 'level', 'date', 'attachment'\],"
    new_code = "'memberships': ['organization_name', 'link', 'level', 'date', 'attachment'],\n    'researches': ['title', 'publication_status', 'publication_type', 'journal_name_and_number', 'published_research_link', 'doi_link', 'date', 'attachment'],\n    'books': ['title', 'publisher', 'date', 'attachment'],\n    'grants': ['title', 'grant_type', 'achievement', 'date', 'attachment'],"
    content = re.sub(old_code, new_code, content)
    profile_py.write_text(content, encoding="utf-8")
    print("Updated PROFILE_SECTION_FIELDS in db/profile.py")
else:
    print("Already updated.")
