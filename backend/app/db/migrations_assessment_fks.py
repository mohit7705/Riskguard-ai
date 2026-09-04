from backend.app.db.database import engine
from sqlalchemy import text


def migrate() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE risk_feedback
            ADD CONSTRAINT fk_risk_feedback_assessment
            FOREIGN KEY (assessment_id)
            REFERENCES assessments(assessment_id)
        """))

        conn.execute(text("""
            ALTER TABLE review_cases
            ADD CONSTRAINT fk_review_cases_assessment
            FOREIGN KEY (assessment_id)
            REFERENCES assessments(assessment_id)
        """))

    print("Assessment foreign-key migration completed.")


if __name__ == "__main__":
    migrate()
