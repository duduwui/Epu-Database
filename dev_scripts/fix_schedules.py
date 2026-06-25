import os

files = [
    'templates/teacher/schedule.html',
    'templates/admin/dashboard.html',
    'templates/student/dashboard.html'
]

for file_path in files:
    if not os.path.exists(file_path):
        continue
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update filter-chip-group
    content = content.replace(
        '.filter-chip-group {\n      display: flex;\n      align-items: center;\n      gap: 8px;\n    }',
        '.filter-chip-group {\n      display: flex;\n      align-items: center;\n      gap: 8px;\n      flex-wrap: wrap;\n    }'
    )

    # 2. Update filter-section
    content = content.replace(
        '.filter-section {\n      display: flex;\n      align-items: center;\n      gap: 20px;\n    }',
        '.filter-section {\n      display: flex;\n      align-items: center;\n      gap: 20px;\n      flex-wrap: wrap;\n    }'
    )

    # 3. Update scheduler-filters
    content = content.replace(
        '.scheduler-filters {\n      display: flex;\n      align-items: center;\n      justify-content: space-between;\n      padding: 14px 20px;\n      background: #f8fafc;\n      border-top: 1px solid #e5e7eb;\n      border-bottom: 1px solid #e5e7eb;\n    }',
        '.scheduler-filters {\n      display: flex;\n      align-items: center;\n      justify-content: space-between;\n      flex-wrap: wrap;\n      padding: 14px 20px;\n      background: #f8fafc;\n      border-top: 1px solid #e5e7eb;\n      border-bottom: 1px solid #e5e7eb;\n    }'
    )
    
    # 4. Update the wrapper to ensure it's responsive.
    content = content.replace(
        '.scheduler-wrapper {\n      background: #fff;\n      border: 1px solid #e5e7eb;\n      border-radius: 12px;\n      margin-bottom: 2rem;\n      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);\n      overflow: hidden;\n    }',
        '.scheduler-wrapper {\n      background: #fff;\n      border: 1px solid #e5e7eb;\n      border-radius: 12px;\n      margin-bottom: 2rem;\n      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);\n      overflow: hidden;\n      width: 100%;\n    }'
    )

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {file_path}")

