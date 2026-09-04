from backend.app.db.database import engine
from sqlalchemy import text


LEGACY_ASSIGNMENT_ID = "LEGACY-ASSIGNMENT-0831"
LEGACY_ASSIGNMENT_NUMBER = "LEGACY-0831"
LEGACY_ASSIGNMENT_NAME = "Legacy Existing Data"


def migrate() -> None:
    with engine.begin() as conn:
        # 1. Create a legacy assignment for existing assessment data.
        conn.execute(
            text("""
                INSERT INTO assignments (
                    assignment_id,
                    assignment_number,
                    assignment_name,
                    created_at
                )
                VALUES (
                    :assignment_id,
                    :assignment_number,
                    :assignment_name,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (assignment_number) DO NOTHING
            """),
            {
                "assignment_id": LEGACY_ASSIGNMENT_ID,
                "assignment_number": LEGACY_ASSIGNMENT_NUMBER,
                "assignment_name": LEGACY_ASSIGNMENT_NAME,
            },
        )

        # 2. Add assignment_id to assessments.
        conn.execute(
            text("""
                ALTER TABLE assessments
                ADD COLUMN IF NOT EXISTS assignment_id VARCHAR(36)
            """)
        )

        # 3. Put existing assessments into the legacy assignment.
        conn.execute(
            text("""
                UPDATE assessments
                SET assignment_id = :assignment_id
                WHERE assignment_id IS NULL
            """),
            {
                "assignment_id": LEGACY_ASSIGNMENT_ID,
            },
        )

        # 4. Make assignment_id mandatory.
        conn.execute(
            text("""
                ALTER TABLE assessments
                ALTER COLUMN assignment_id SET NOT NULL
            """)
        )

        # 5. Add lookup index.
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_assessments_assignment_id
                ON assessments (assignment_id)
            """)
        )

        # 6. Add the foreign key.
        conn.execute(
            text("""
                ALTER TABLE assessments
                ADD CONSTRAINT fk_assessments_assignment
                FOREIGN KEY (assignment_id)
                REFERENCES assignments(assignment_id)
            """)
        )


if __name__ == "__main__":
    migrate()
    print("Assessment → Assignment migration completed.")
