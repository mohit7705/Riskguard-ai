from backend.app.db.database import engine
from sqlalchemy import text


def migrate() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS assignments (
                assignment_id VARCHAR(36) PRIMARY KEY,
                assignment_number VARCHAR(32) NOT NULL UNIQUE,
                assignment_name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_assignments_assignment_number
            ON assignments (assignment_number)
        """))


if __name__ == "__main__":
    migrate()
    print("Assignment schema migration completed.")
