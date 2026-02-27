"""
One-time fix: sync students.year, semester, shift, section from their assigned class.
Run this once to repair existing rows where class_id was updated without syncing those columns.
"""
import db

def sync():
    # Find all students whose direct fields disagree with their class
    mismatches = db.execute_query("""
        SELECT s.id, s.student_number,
               u.full_name,
               s.year   AS s_year,   c.year   AS c_year,
               s.semester AS s_sem,  c.semester AS c_sem,
               s.shift  AS s_shift,  c.shift  AS c_shift,
               s.section AS s_sec,   c.section AS c_sec
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN classes c ON s.class_id = c.id
        WHERE s.year     IS DISTINCT FROM c.year
           OR s.semester IS DISTINCT FROM c.semester
           OR s.shift    IS DISTINCT FROM c.shift
           OR s.section  IS DISTINCT FROM c.section
        ORDER BY u.full_name
    """, fetch_all=True)

    if not mismatches:
        print("✓  No mismatches found – all students are already in sync.")
        return

    print(f"Found {len(mismatches)} student(s) with mismatched fields:\n")
    for row in mismatches:
        print(f"  {row['full_name']} ({row['student_number'] or row['id']})")
        if row['s_year'] != row['c_year']:
            print(f"    year:     students={row['s_year']}  →  classes={row['c_year']}")
        if row['s_sem'] != row['c_sem']:
            print(f"    semester: students={row['s_sem']}  →  classes={row['c_sem']}")
        if row['s_shift'] != row['c_shift']:
            print(f"    shift:    students={row['s_shift']}  →  classes={row['c_shift']}")
        if row['s_sec'] != row['c_sec']:
            print(f"    section:  students={row['s_sec']}  →  classes={row['c_sec']}")

    print()
    confirm = input("Apply sync (update students table from classes)? [y/N] ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return

    result = db.execute_query("""
        UPDATE students s
        SET year     = c.year,
            semester = c.semester,
            shift    = c.shift,
            section  = c.section
        FROM classes c
        WHERE s.class_id = c.id
          AND (   s.year     IS DISTINCT FROM c.year
               OR s.semester IS DISTINCT FROM c.semester
               OR s.shift    IS DISTINCT FROM c.shift
               OR s.section  IS DISTINCT FROM c.section)
    """)
    print(f"✓  Done. Rows updated: {result if result is not None else 'N/A (check DB)'}")

if __name__ == '__main__':
    sync()
