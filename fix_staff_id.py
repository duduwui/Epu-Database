from pathlib import Path
profile_py = Path("db/profile.py")
content = profile_py.read_text(encoding="utf-8")

if "def get_teacher_by_staff_id(" not in content:
    func = "\n\ndef get_teacher_by_staff_id(staff_id):\n    return execute_query(\"SELECT * FROM users WHERE staff_id=%s AND role='teacher'\", (staff_id,), fetch_one=True)\n"
    content = content + func
    profile_py.write_text(content, encoding="utf-8")
    print("Added get_teacher_by_staff_id")
