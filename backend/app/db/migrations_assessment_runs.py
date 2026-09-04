from backend.app.db.database import engine
from sqlalchemy import text


def migrate() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE review_cases
            ADD COLUMN IF NOT EXISTS assessment_id VARCHAR(32)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_review_cases_assessment_id
            ON review_cases (assessment_id)
        """))


if __name__ == "__main__":
    migrate()
    print("Assessment run schema migration completed.")
