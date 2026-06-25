import re
from pathlib import Path

profile_py = Path("blueprints/profile.py")
content = profile_py.read_text(encoding="utf-8")

# 1. Add RESEARCH_SECTIONS
research_sections_code = """
RESEARCH_SECTIONS = {
    'research': {
        'table': 'researches',
        'title': 'Researches',
        'active': 'researches',
        'group_label': 'Researches',
        'api_base': '/profile/api/researches',
        'columns': [('title', 'Title'), ('publication_status', 'Status'), ('publication_type', 'Type'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'publication_status', 'label': 'Publication Status', 'type': 'select', 'required': True, 'options': ['Published', 'Under Review', 'In Progress']},
            {'name': 'publication_type', 'label': 'Publication Type', 'type': 'select', 'required': True, 'options': ['Impact factor Journal', 'Non-Impact factor Journal', 'Conference Paper', 'Book Chapter']},
            {'name': 'journal_name_and_number', 'label': 'Journal Name and Number', 'type': 'text'},
            {'name': 'published_research_link', 'label': 'Published Research Link', 'type': 'url'},
            {'name': 'doi_link', 'label': 'DOI Link', 'type': 'url'},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'book': {
        'table': 'books',
        'title': 'Books',
        'active': 'researches',
        'group_label': 'Researches',
        'api_base': '/profile/api/researches',
        'columns': [('title', 'Title'), ('publisher', 'Publisher'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'publisher', 'label': 'Publisher', 'type': 'text', 'required': True},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'grant': {
        'table': 'grants',
        'title': 'Grants',
        'active': 'researches',
        'group_label': 'Researches',
        'api_base': '/profile/api/researches',
        'columns': [('title', 'Title Name'), ('grant_type', 'Type'), ('achievement', 'Achievement'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'grant_type', 'label': 'Grant Type', 'type': 'text', 'required': True},
            {'name': 'achievement', 'label': 'Achievement', 'type': 'text', 'required': True},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
}
"""

if "RESEARCH_SECTIONS =" not in content:
    content = content.replace("def _section_config_or_404(section):", research_sections_code + "\ndef _section_config_or_404(section):")

# 2. Update _section_config_or_404
old_return = "return CAD_SECTIONS.get(section) or PORTFOLIO_SECTIONS.get(section)"
new_return = "return CAD_SECTIONS.get(section) or PORTFOLIO_SECTIONS.get(section) or RESEARCH_SECTIONS.get(section)"
content = content.replace(old_return, new_return)

# 3. Add researches routes
if "@profile_bp.route('/researches/<section>')" not in content:
    portfolio_routes_regex = r"@profile_bp\.route\('/portfolio/<section>'\).*?def delete_portfolio_record\(section, item_id\):.*?return _json_success\('The Record Deleted'\)"
    
    match = re.search(portfolio_routes_regex, content, flags=re.DOTALL)
    if match:
        portfolio_code = match.group(0)
        researches_code = portfolio_code.replace("portfolio", "researches").replace("Portfolio", "Researches")
        
        content = content.replace(portfolio_code, portfolio_code + "\n\n\n" + researches_code)
    else:
        print("Could not find portfolio routes to duplicate.")

profile_py.write_text(content, encoding="utf-8")
print("Updated blueprints/profile.py")
