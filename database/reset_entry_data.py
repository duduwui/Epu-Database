import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DATABASE_DIR = ROOT / "database"
UPLOADS_DIR = ROOT / "uploads"


def load_env_file(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def get_db_config() -> dict:
    env_file = load_env_file(ENV_PATH)
    return {
        "host": os.getenv("DB_HOST", env_file.get("DB_HOST", "localhost")),
        "port": os.getenv("DB_PORT", env_file.get("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", env_file.get("DB_NAME", "mis_system")),
        "user": os.getenv("DB_USER", env_file.get("DB_USER", "postgres")),
        "password": os.getenv("DB_PASSWORD", env_file.get("DB_PASSWORD", "")),
    }


def create_backup(cfg: dict) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = DATABASE_DIR / f"{cfg['dbname']}_pre_entry_reset_{timestamp}.dump"
    pg_dump = Path(r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe")

    env = os.environ.copy()
    env["PGPASSWORD"] = cfg["password"]

    subprocess.run(
        [
            str(pg_dump),
            "-h",
            cfg["host"],
            "-p",
            str(cfg["port"]),
            "-U",
            cfg["user"],
            "-d",
            cfg["dbname"],
            "-F",
            "c",
            "-f",
            str(backup_path),
        ],
        check=True,
        env=env,
    )
    return backup_path


def clear_upload_files() -> tuple[int, int]:
    if not UPLOADS_DIR.exists():
        return 0, 0

    removed_files = 0
    removed_dirs = 0

    for path in sorted(UPLOADS_DIR.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
            removed_files += 1
        elif path.is_dir():
            try:
                path.rmdir()
                removed_dirs += 1
            except OSError:
                pass

    return removed_files, removed_dirs


def reset_entry_data(cfg: dict) -> dict:
    summary = {}
    conn = psycopg.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
    )

    truncate_tables = [
        "attendance",
        "class_schedules",
        "classes",
        "enrollment_periods",
        "exam_periods",
        "exam_signups",
        "grade_components",
        "grades",
        "homework",
        "homework_submissions",
        "lecture_files",
        "moodle_weeks",
        "semester_subjects",
        "student_engagement",
        "student_engagement_sessions",
        "student_enrollments",
        "subjects",
        "teacher_assignments",
        "teachers",
        "timetable",
        "upgrade_history",
        "weekly_topics",
    ]

    count_tables = truncate_tables + ["students", "users"]

    try:
        with conn.cursor() as cur:
            for table in count_tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                summary[f"before_{table}"] = cur.fetchone()[0]

            cur.execute(
                """
                SELECT id
                FROM users
                WHERE role = 'admin'
                  AND (
                      id = 1
                      OR username = 'admin'
                      OR email = 'admin@epu.edu.iq'
                  )
                ORDER BY id
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Super admin was not found; aborting reset.")
            super_admin_id = row[0]
            summary["super_admin_id"] = super_admin_id

            cur.execute(f"TRUNCATE TABLE {', '.join(truncate_tables)} RESTART IDENTITY CASCADE")
            cur.execute("DELETE FROM students")
            cur.execute("DELETE FROM users WHERE id <> %s", (super_admin_id,))

            for table in count_tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                summary[f"after_{table}"] = cur.fetchone()[0]

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    removed_files, removed_dirs = clear_upload_files()
    summary["removed_upload_files"] = removed_files
    summary["removed_upload_dirs"] = removed_dirs
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Safely wipe entry/content data while preserving schema, majors, departments, system settings, and the super admin."
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required safety flag. Without this flag the script only explains what it would do.",
    )
    args = parser.parse_args()

    if not args.confirm_reset:
        print("Dry run only. Re-run with --confirm-reset to back up and wipe entry/content data.")
        return

    cfg = get_db_config()
    backup_path = create_backup(cfg)
    summary = reset_entry_data(cfg)

    print(f"Backup created: {backup_path}")
    for key in sorted(summary):
        print(f"{key}: {summary[key]}")


if __name__ == "__main__":
    main()
