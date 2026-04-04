import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("MEDIA_ROOT", "/tmp/lfb-media-tests")
Path(os.environ["MEDIA_ROOT"]).mkdir(parents=True, exist_ok=True)

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import auth_session, claim, item  # noqa: F401


@pytest.fixture()
def db_session_factory():
    db_path = Path("/tmp/lfb-test.db")
    if db_path.exists():
        db_path.unlink()
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal
    finally:
        engine.dispose()
        if db_path.exists():
            db_path.unlink()


@pytest.fixture()
def client(db_session_factory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
