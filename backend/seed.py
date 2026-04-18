import os
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Agent, ApiKey, Project, Sprint, Task
from .security import hash_api_key


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


def get_api_keys():
    keys = {}
    i = 1
    while True:
        agent_id = os.getenv(f"RELAY_AGENT_{i}_ID")
        agent_key = os.getenv(f"RELAY_AGENT_{i}_KEY")
        if not agent_id or not agent_key:
            break
        keys[agent_id] = agent_key
        i += 1
    human_id = os.getenv("RELAY_HUMAN_ID", "human")
    human_key = os.getenv("RELAY_HUMAN_KEY")
    if human_key:
        keys[human_id] = human_key
    return keys


def ensure_agent(db: Session, agent_id: str, name: str, avatar: str, role: str, model: str, provider: str, status: str) -> None:
    agent = db.get(Agent, agent_id)
    if agent:
        # Preserve webhook registration — only update mutable identity fields
        agent.name = name
        agent.avatar = avatar
        agent.role = role
        agent.model = model
        agent.provider = provider
        agent.status = status
        agent.last_active = datetime.utcnow().isoformat()
        db.add(agent)
        return
    db.add(Agent(
        id=agent_id, name=name, avatar=avatar, role=role,
        model=model, provider=provider, status=status,
        last_active=datetime.utcnow().isoformat(),
    ))


def ensure_project(db: Session, name: str, description: str, status: str, lead_agent_id: str):
    project = db.query(Project).filter(Project.name == name).first()
    if project:
        project.description = description
        project.status = status
        project.lead_agent_id = lead_agent_id
        project.updated_at = datetime.utcnow().isoformat()
        db.add(project)
        return project
    project = Project(name=name, description=description, status=status, lead_agent_id=lead_agent_id)
    db.add(project)
    db.flush()
    return project


def ensure_sprint(db: Session, project_id: int, name: str, start_date: str, end_date: str):
    sprint = db.query(Sprint).filter(Sprint.project_id == project_id, Sprint.name == name).first()
    if sprint:
        sprint.start_date = start_date
        sprint.end_date = end_date
        db.add(sprint)
        return sprint
    sprint = Sprint(project_id=project_id, name=name, start_date=start_date, end_date=end_date)
    db.add(sprint)
    db.flush()
    return sprint


def ensure_task(db, project_id, sprint_id, title, description, assignee_id, reporter_id, priority, status, due_date):
    task = db.query(Task).filter(Task.project_id == project_id, Task.title == title).first()
    if task:
        task.description = description
        task.assignee_id = assignee_id
        task.reporter_id = reporter_id
        task.priority = priority
        task.status = status
        task.sprint_id = sprint_id
        task.due_date = due_date
        task.updated_at = datetime.utcnow().isoformat()
        db.add(task)
        return task
    task = Task(
        project_id=project_id, sprint_id=sprint_id, title=title,
        description=description, assignee_id=assignee_id, reporter_id=reporter_id,
        priority=priority, status=status, tags="", due_date=due_date,
    )
    db.add(task)
    return task


def ensure_key(db: Session, agent_id: str, key: str) -> None:
    key_hash = hash_api_key(key)
    existing = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if existing:
        if existing.key:
            existing.key = None
            db.add(existing)
        return
    legacy = db.query(ApiKey).filter(ApiKey.key == key).first()
    if legacy:
        legacy.key_hash = key_hash
        legacy.key = None
        db.add(legacy)
        return
    db.add(ApiKey(agent_id=agent_id, key=None, key_hash=key_hash))


def handle_renames(db: Session) -> None:
    """
    Handle agent ID renames: if an old agent ID still exists in the DB but the
    env now refers to it by a new ID (e.g. gandalf -> main), rename the row.
    """
    RENAMES = {"gandalf": "main"}
    for old_id, new_id in RENAMES.items():
        old_agent = db.query(Agent).filter(Agent.id == old_id).first()
        if not old_agent:
            continue
        new_agent = db.query(Agent).filter(Agent.id == new_id).first()
        if new_agent:
            db.delete(old_agent)
        else:
            old_agent.id = new_id
        db.flush()


def seed_from_env(db: Session) -> None:
    """
    Seed agents and API keys from environment variables.

    Set these in your .env:
      RELAY_HUMAN_ID=human
      RELAY_HUMAN_KEY=your-key

      RELAY_AGENT_1_ID=agent1
      RELAY_AGENT_1_NAME=Agent One
      RELAY_AGENT_1_AVATAR=🤖
      RELAY_AGENT_1_ROLE=Worker
      RELAY_AGENT_1_MODEL=openai/gpt-4o
      RELAY_AGENT_1_PROVIDER=openai
      RELAY_AGENT_1_KEY=agent1-key
      RELAY_AGENT_1_WEBHOOK_SECRET=your-webhook-secret
      # repeat for RELAY_AGENT_2_, RELAY_AGENT_3_, ...
    """
    handle_renames(db)
    i = 1
    while True:
        agent_id = os.getenv(f"RELAY_AGENT_{i}_ID")
        if not agent_id:
            break
        name = os.getenv(f"RELAY_AGENT_{i}_NAME", agent_id)
        avatar = os.getenv(f"RELAY_AGENT_{i}_AVATAR", "🤖")
        role = os.getenv(f"RELAY_AGENT_{i}_ROLE", "Agent")
        model = os.getenv(f"RELAY_AGENT_{i}_MODEL", "")
        provider = os.getenv(f"RELAY_AGENT_{i}_PROVIDER", "")
        key = os.getenv(f"RELAY_AGENT_{i}_KEY")
        webhook_secret = os.getenv(f"RELAY_AGENT_{i}_WEBHOOK_SECRET")
        ensure_agent(db, agent_id, name, avatar, role, model, provider, "Idle")
        if key:
            ensure_key(db, agent_id, key)
        # Seed webhook secret into DB if set in env AND agent doesn't already have one
        if webhook_secret:
            ag = db.query(Agent).filter(Agent.id == agent_id).first()
            if ag and not ag.webhook_secret:
                ag.webhook_secret = webhook_secret
                db.add(ag)
        i += 1

    human_id = os.getenv("RELAY_HUMAN_ID", "human")
    human_name = os.getenv("RELAY_HUMAN_NAME", "Human")
    human_key = os.getenv("RELAY_HUMAN_KEY")
    human_webhook_secret = os.getenv(f"RELAY_{human_id.upper()}_WEBHOOK_SECRET")
    ensure_agent(db, human_id, human_name, "👤", "Owner", "", "", "Online")
    if human_key:
        ensure_key(db, human_id, human_key)
    if human_webhook_secret:
        hg = db.query(Agent).filter(Agent.id == human_id).first()
        if hg and not hg.webhook_secret:
            hg.webhook_secret = human_webhook_secret
            db.add(hg)

    db.commit()


def seed(db: Session):
    seed_from_env(db)
