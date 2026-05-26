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

    # 1. Update Grid Area to ensure it handles overflow
    content = content.replace(
        '.scheduler-grid-area {\n      padding: 16px;\n      background: #fff;\n      overflow-x: auto;\n    }',
        '.scheduler-grid-area {\n      padding: 16px;\n      background: #fff;\n      overflow-x: auto;\n      max-width: 100%;\n      -webkit-overflow-scrolling: touch;\n    }'
    )

    # 2. Also ensure current header and filters stack properly on very small screens
    content = content.replace(
        '@media (max-width: 768px) {\n      .scheduler-table th .day-full {\n        display: none;\n      }',
        '@media (max-width: 768px) {\n      .scheduler-wrapper {\n        border-radius: 0;\n        border-left: none;\n        border-right: none;\n      }\n      .scheduler-grid-area {\n        padding: 8px;\n      }\n      .filter-chip-group {\n        flex-direction: column;\n        align-items: flex-start;\n      }\n      .scheduler-table th .day-full {\n        display: none;\n      }'
    )

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched 2 {file_path}")

