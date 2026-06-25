import re
from pathlib import Path

profile_py = Path("blueprints/profile.py")
content = profile_py.read_text(encoding="utf-8")

# Let's fix the config checking function which might be broken by previous replacement
if "RESEARCH_SECTIONS.get(section)" not in content:
    content = content.replace(
        "return CAD_SECTIONS.get(section) or PORTFOLIO_SECTIONS.get(section)",
        "return CAD_SECTIONS.get(section) or PORTFOLIO_SECTIONS.get(section) or RESEARCH_SECTIONS.get(section)"
    )

if "@profile_bp.route('/researches/<section>')" not in content:
    regex = r"@profile_bp\.route\('/portfolio/<section>'\).*?def delete_portfolio_record\(section, item_id\):.*?return jsonify\(\{.*?\}\)"
    match = re.search(regex, content, flags=re.DOTALL)
    if match:
        portfolio_code = match.group(0)
        researches_code = portfolio_code.replace("portfolio", "researches").replace("Portfolio", "Researches").replace("PORTFOLIO_SECTIONS", "RESEARCH_SECTIONS")
        content = content.replace(portfolio_code, portfolio_code + "\n\n\n" + researches_code)
    else:
        print("Still could not find portfolio routes.")
        
profile_py.write_text(content, encoding="utf-8")
print("Added researches routes.")
