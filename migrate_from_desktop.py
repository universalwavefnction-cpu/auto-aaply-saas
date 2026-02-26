"""
Migrate data from the desktop AutoApply app (~/.autoapply/) into the new web app database.

Run: python migrate_from_desktop.py
"""
import sqlite3
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from backend.database import engine, SessionLocal, init_db
from backend.models import User, Profile, Application, JobFilter
from backend.auth import hash_password

# Paths
OLD_DB = os.path.expanduser("~/.autoapply/applications.db")
OLD_CONFIG = os.path.expanduser("~/.autoapply/config.json")
OLD_QUESTIONS = os.path.expanduser("~/.autoapply/questions.json")


def _parse_dt(val):
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.fromisoformat(val)
        except (ValueError, TypeError):
            pass
    return None


def migrate():
    init_db()
    db = SessionLocal()

    # Load old data
    with open(OLD_CONFIG) as f:
        config = json.load(f)
    with open(OLD_QUESTIONS) as f:
        questions = json.load(f)

    personal = config.get("personal_info", {})
    email = config.get("credentials", {}).get("xing", {}).get("email", "user@example.com")

    # Create user
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"User {email} already exists, skipping user creation")
        user = existing
    else:
        user = User(email=email, password_hash=hash_password("changeme123"))
        db.add(user)
        db.flush()
        print(f"Created user: {email} (id={user.id})")

    # Create/update profile
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(
            user_id=user.id,
            first_name=personal.get("first_name", ""),
            last_name=personal.get("last_name", ""),
            phone=personal.get("phone", ""),
            city=personal.get("city", "Berlin"),
            zip_code=personal.get("zip_code", ""),
            street_address=personal.get("street_address", ""),
            salary_expectation=int(personal.get("salary_expectation", 0) or 0),
            years_experience=int(personal.get("years_experience", 0) or 0),
            linkedin_url=personal.get("linkedin_profile", ""),
            questions_json=questions,
        )
        db.add(profile)
        print(f"Created profile with {len(questions)} Q&A pairs")

    # Create job filter
    job_filter = db.query(JobFilter).filter(JobFilter.user_id == user.id).first()
    if not job_filter:
        search = config.get("search", {})
        job_filter = JobFilter(
            user_id=user.id,
            job_titles=search.get("job_titles", "").split(", ") if search.get("job_titles") else [],
            locations=search.get("locations", "").split(", ") if search.get("locations") else ["Berlin"],
            remote_only=search.get("remote", False),
            min_salary=search.get("min_salary", 0),
        )
        db.add(job_filter)
        print("Created job filter")

    db.flush()

    # Import applications from old DB
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row
    old_cur = old_conn.cursor()
    old_cur.execute("SELECT * FROM applications")
    rows = old_cur.fetchall()

    imported = 0
    skipped = 0
    for row in rows:
        url = row["url"]
        existing_app = db.query(Application).filter(
            Application.user_id == user.id,
            Application.url == url,
        ).first()
        if existing_app:
            skipped += 1
            continue

        status_map = {
            "success": "success",
            "failed": "failed",
            "cleared": "success",
            "pending": "pending",
            "skipped": "skipped",
        }

        app = Application(
            user_id=user.id,
            platform=row["platform"].lower() if row["platform"] else "unknown",
            job_title=row["title"],
            company=row["company"],
            url=url,
            status=status_map.get(row["status"], row["status"]),
            response_status=row["response_status"] or "waiting",
            applied_at=_parse_dt(row["applied_at"]),
            notes=row["notes"],
        )
        db.add(app)
        imported += 1

    db.commit()
    old_conn.close()
    db.close()

    print(f"\nMigration complete:")
    print(f"  Applications imported: {imported}")
    print(f"  Applications skipped (duplicate): {skipped}")
    print(f"  Total in old DB: {len(rows)}")


if __name__ == "__main__":
    migrate()
