import glob
import re

for filepath in glob.glob('templates/**/*.html', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Find the starting tag `<table ` or `<table\n` or `<table\r\n` or `<table>`
    # We want to replace it only if it is NOT preceded by `<div class="something table-responsive something">`
    # A robust way is to just look for all `<table...</table>` blocks and check if they're inside `<div class="table-responsive">`.
    
    # Actually, the simplest way is to check every `<table` and its previous non-whitespace characters.
    # If the previous tags don't include `table-responsive`, wrap it.

    # Let's just use re to locate `table-responsive` wrapping.
    # Let's count `<table` occurrences.
    if '<table' in content:
        print(f"Checking {filepath}...")
