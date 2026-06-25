import glob, re

count = 0
for filepath in glob.glob('templates/**/*.html', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    tables = list(re.finditer(r'(<table\b[^>]*>)', new_content, re.IGNORECASE))
    
    for t in reversed(tables):
        start_idx = t.start()
        end_idx = new_content.find('</table>', start_idx)
        if end_idx == -1: continue
        end_idx += len('</table>')
        
        prefix = new_content[:start_idx]
        last_div_open = prefix.rfind('<div')
        
        is_wrapped = False
        if last_div_open != -1 and 'table-responsive' in prefix[last_div_open:]:
            is_wrapped = True
            
        if 'win.document.write' in prefix[max(0, start_idx-200):]:
            is_wrapped = True
            
        # specifically if it's already in schedule table that we manually wrapped
        if 'scheduler-table' in new_content[start_idx:end_idx] and 'scheduler-grid-area table-responsive' in prefix[-200:]:
            is_wrapped = True
            
        if not is_wrapped:
            table_html = new_content[start_idx:end_idx]
            wrapped = f'<div class=\"table-responsive\">\\n{table_html}\\n</div>'
            new_content = new_content[:start_idx] + wrapped + new_content[end_idx:]
            count += 1
            print(f'Wrapped a table in {filepath}')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

print(f'Wrapped {count} tables total.')
