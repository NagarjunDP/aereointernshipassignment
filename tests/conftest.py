from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.config as config
from app.database import Base, get_db
from app.main import app
import app.processor as processor


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "test_certs.db"
    test_db_url = f"sqlite:///{db_file}"
    test_output_dir = (tmp_path / "generated").resolve()
    test_output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "DATABASE_URL", test_db_url)
    monkeypatch.setattr(config, "OUTPUT_DIR", test_output_dir)
    monkeypatch.setattr(processor, "OUTPUT_DIR", test_output_dir)

    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    testing_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(processor, "SessionLocal", testing_session_factory)

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)
