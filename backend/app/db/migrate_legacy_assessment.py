from datetime import datetime, timezone

from sqlalchemy import text

from backend.app.db.database import engine


LEGACY_ASSESSMENT_ID = "RG-LEGACY-0831"


def migrate() -> None:
    with engine.begin() as conn:
        # ---------------------------------------------------------
        # 1. Create the legacy assessment run for the old dataset.
        # ---------------------------------------------------------
        conn.execute(
            text("""
                INSERT INTO assessments (
                    assessment_id,
                    assessment_type,
                    total_records,
                    created_at
                )
                SELECT
                    :assessment_id,
                    'LEGACY',
                    COUNT(*),
                    :created_at
                FROM risk_feedback
                WHERE assessment_id IS NULL
                ON CONFLICT (assessment_id) DO NOTHING
            """),
            {
                "assessment_id": LEGACY_ASSESSMENT_ID,
                "created_at": datetime.now(timezone.utc),
            },
        )

        # ---------------------------------------------------------
        # 2. Assign all historical orphan feedback to legacy run.
        # ---------------------------------------------------------
        feedback_result = conn.execute(
            text("""
                UPDATE risk_feedback
                SET assessment_id = :assessment_id
                WHERE assessment_id IS NULL
            """),
            {"assessment_id": LEGACY_ASSESSMENT_ID},
        )

        # ---------------------------------------------------------
        # 3. Assign the 14 legacy review cases through their
        #    matching feedback records.
        # ---------------------------------------------------------
        legacy_case_result = conn.execute(
            text("""
                UPDATE review_cases rc
                SET assessment_id = rf.assessment_id
                FROM risk_feedback rf
                WHERE rc.case_id = rf.case_id
                  AND rc.assessment_id IS NULL
                  AND rf.assessment_id = :assessment_id
            """),
            {"assessment_id": LEGACY_ASSESSMENT_ID},
        )

        # ---------------------------------------------------------
        # 4. Assign the remaining review cases from their existing
        #    RiskFeedback assessment IDs.
        # ---------------------------------------------------------
        known_case_result = conn.execute(
            text("""
                UPDATE review_cases rc
                SET assessment_id = rf.assessment_id
                FROM risk_feedback rf
                WHERE rc.case_id = rf.case_id
                  AND rc.assessment_id IS NULL
                  AND rf.assessment_id IS NOT NULL
            """)
        )

        # ---------------------------------------------------------
        # 5. Verification.
        # ---------------------------------------------------------
        legacy_feedback_count = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM risk_feedback
                WHERE assessment_id = :assessment_id
            """),
            {"assessment_id": LEGACY_ASSESSMENT_ID},
        ).scalar_one()

        legacy_case_count = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM review_cases
                WHERE assessment_id = :assessment_id
            """),
            {"assessment_id": LEGACY_ASSESSMENT_ID},
        ).scalar_one()

        orphan_feedback = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM risk_feedback
                WHERE assessment_id IS NULL
            """)
        ).scalar_one()

        orphan_cases = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM review_cases
                WHERE assessment_id IS NULL
            """)
        ).scalar_one()

        total_assessments = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM assessments
            """)
        ).scalar_one()

        print("========== LEGACY MIGRATION ==========")
        print("Assessment ID              :", LEGACY_ASSESSMENT_ID)
        print("Feedback updated           :", feedback_result.rowcount)
        print("Legacy cases updated       :", legacy_case_result.rowcount)
        print("Known-run cases updated    :", known_case_result.rowcount)
        print("Feedback in legacy         :", legacy_feedback_count)
        print("Cases in legacy            :", legacy_case_count)
        print("Orphan feedback            :", orphan_feedback)
        print("Orphan cases               :", orphan_cases)
        print("Total assessments          :", total_assessments)

        # Hard verification.
        if legacy_feedback_count != 2335:
            raise RuntimeError(
                f"Expected 2335 legacy feedback records, "
                f"found {legacy_feedback_count}"
            )

        if legacy_case_count != 14:
            raise RuntimeError(
                f"Expected 14 legacy review cases, "
                f"found {legacy_case_count}"
            )

        if orphan_feedback != 0:
            raise RuntimeError(
                f"Expected 0 orphan feedback records, "
                f"found {orphan_feedback}"
            )

        if orphan_cases != 0:
            raise RuntimeError(
                f"Expected 0 orphan review cases, "
                f"found {orphan_cases}"
            )

        print("Migration verification: PASSED")


if __name__ == "__main__":
    migrate()
