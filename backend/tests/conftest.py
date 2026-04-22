import os
import pytest
from datetime import datetime
from typing import Generator
from unittest.mock import patch

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["RELAY_ENV"] = "test"
os.environ["RELAY_HUMAN_ID"] = "human"
os.environ["RELAY_HUMAN_NAME"] = "Human"
os.environ["RELAY_HUMAN_KEY"] = "test-human-key-12345"
os.environ["RELAY_AGENT_1_ID"] = "agent1"
os.environ["RELAY_AGENT_1_NAME"] = "Agent One"
os.environ["RELAY_AGENT_1_KEY"] = "test-agent1-key-12345"
os.environ["RELAY_AGENT_1_ROLE"] = "Worker"
os.environ["RELAY_AGENT_1_MODEL"] = "openai/gpt-4o"
os.environ["RELAY_AGENT_1_PROVIDER"] = "openai"
os.environ["RELAY_AGENT_2_ID"] = "agent2"
os.environ["RELAY_AGENT_2_NAME"] = "Agent Two"
os.environ["RELAY_AGENT_2_KEY"] = "test-agent2-key-12345"
os.environ["RELAY_AGENT_2_ROLE"] = "Reviewer"
os.environ["RELAY_AGENT_2_MODEL"] = "anthropic/claude-sonnet-4-6"
os.environ["RELAY_AGENT_2_PROVIDER"] = "anthropic"
os.environ["RELAY_RATE_LIMIT_REQUESTS"] = "10000"

TEST_API_KEY = "test-human-key-12345"
TEST_AGENT1_KEY = "test-agent1-key-12345"
TEST_AGENT2_KEY = "test-agent2-key-12345"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    from backend.database import Base

    Base.metadata.create_all(bind=engine)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db(db_engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def seed_db(db: Session) -> Session:
    from backend.seed import seed
    from backend.security import ensure_api_key_storage, migrate_api_keys, migrate_agent_webhooks

    ensure_api_key_storage(db.get_bind())
    seed(db)
    migrate_api_keys(db)
    migrate_agent_webhooks(db.get_bind())
    db.commit()
    return db


@pytest.fixture
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def agent1_headers():
    return {"X-API-Key": TEST_AGENT1_KEY}


@pytest.fixture
def agent2_headers():
    return {"X-API-Key": TEST_AGENT2_KEY}


@pytest.fixture
def seed_project(db: Session):
    from backend.models import Project

    project = Project(
        name="Test Project",
        description="A test project description",
        status="Active",
        lead_agent_id="agent1",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def seed_sprint(db: Session, seed_project):
    from backend.models import Sprint

    sprint = Sprint(
        project_id=seed_project.id,
        name="Sprint 1",
        start_date="2026-01-01",
        end_date="2026-01-14",
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


@pytest.fixture
def seed_task(db: Session, seed_project, seed_sprint):
    from backend.models import Task

    task = Task(
        project_id=seed_project.id,
        sprint_id=seed_sprint.id,
        title="Test Task",
        description="A test task description",
        assignee_id="agent1",
        reporter_id="human",
        priority="P2",
        status="To Do",
        tags="test,backend",
        due_date="2026-01-15",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture
def seed_agent(db: Session):
    from backend.models import Agent

    agent = Agent(
        id="testagent",
        name="Test Agent",
        avatar="🤖",
        role="Worker",
        model="openai/gpt-4o",
        provider="openai",
        status="Idle",
        capabilities="coding,testing",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture
def client(db: Session, seed_db):
    from backend.main import app
    from backend.database import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db: Session, seed_db):
    from backend.main import app
    from backend.database import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_dispatcher_fire():
    with patch("backend.main.fire") as mock_fire:
        mock_fire.return_value = None
        yield mock_fire