"""
Check which subjects have grade components
"""
import sys
sys.path.insert(0, '.')
import db

print("=" * 60)
print("Subjects with Grade Components")
print("=" * 60)

components_by_subject = db.execute_query("""
    SELECT s.id, s.name, s.semester, COUNT(gc.id) as component_count
    FROM subjects s
    LEFT JOIN grade_components gc ON s.id = gc.subject_id
    GROUP BY s.id, s.name, s.semester
    ORDER BY s.semester, s.name
""", fetch_all=True)

print("\nAll subjects and their component counts:")
for subj in components_by_subject:
    status = "✓" if subj['component_count'] > 0 else "✗"
    print(f"  {status} Sem {subj['semester']}: {subj['name']} - {subj['component_count']} component(s)")

# Check specifics for Sem 1
print("\n" + "=" * 60)
print("Semester 1 Subjects (Need components for grades!):")
print("=" * 60)

sem1_subjects = [s for s in components_by_subject if s['semester'] == 1]
for subj in sem1_subjects:
    if subj['component_count'] == 0:
        print(f"  ⚠ {subj['name']} (ID: {subj['id']}) - NO COMPONENTS!")
    else:
        print(f"  ✓ {subj['name']} (ID: {subj['id']}) - {subj['component_count']} components")

print("\n" + "=" * 60)
