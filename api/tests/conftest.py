import os
import sys
from pathlib import Path

# Ensure imports like `from app.main import app` work whether pytest is run from repo root or /api
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

# Make Settings() happy at import-time; we override DB anyway.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.deps import get_db
from app.models import Base


@pytest.fixture(scope="function")
def client():
    """FastAPI TestClient backed by an in-memory SQLite DB (isolated per test)."""

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)