from backend.app.db.database import Base, engine
from backend.app.db.models import Assessment, RiskFeedback, ReviewCase


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
