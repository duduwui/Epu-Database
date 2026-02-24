# Grade Publishing System - Migration Instructions

## Important: Database Migration Required!

Before using the new grade publishing features, you need to run the database migration to add the required fields.

### How to Run Migration:

**Option 1: Using the migration script**

```bash
python migrate_grade_publishing.py
```

**Option 2: Run SQL directly**
Connect to your PostgreSQL database and run:

```bash
psql -U postgres -d mis_system -f database/add_grade_publishing.sql
```

**Option 3: From pgAdmin or DBeaver**
Open `database/add_grade_publishing.sql` and execute it in your database client.

---

## What's New:

### For Teachers:

1. **Draft Mode**: When you save grades, they're saved as DRAFT (not visible to students)
2. **Publish Button**: Click "Publish Grades" to make all saved grades visible to students
3. **Safer Grading**: Set marks for all students, then publish when ready

### For Students:

- Can only see **published** grades in "My Grades" page
- Draft grades are hidden until teacher publishes them

### For Admins:

- Control final results visibility per subject
- Toggle `results_published` field to show/hide transcripts from students

---

## Database Changes:

### grades table:

- Added `published` column (BOOLEAN, default FALSE)
- Grades saved by teachers are draft (published=FALSE) by default
- Teachers can publish all grades for a subject/class at once

### subjects table:

- Added `results_published` column (BOOLEAN, default FALSE)
- Admins control whether final results/transcript is visible

---

## Workflow:

1. Teacher enters grades → **Saved as DRAFT** (students can't see)
2. Teacher reviews and verifies all grades
3. Teacher clicks **"Publish Grades"** → Students can now see grades
4. Admin can separately control final results visibility

This prevents students from seeing incomplete or incorrect grades!
