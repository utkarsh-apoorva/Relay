from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Agent, ApiKey, Project, Sprint, Task

AGENTS = [
    ("gandalf", "Gandalf", "🧙", "Orchestrator", "zai/glm-5.1", "zai", "Online"),
    ("ive", "Ive", "🎨", "Design & Product", "anthropic/claude-sonnet-4-6", "anthropic", "Idle"),
    ("linus", "Linus", "🐧", "Coding", "openai/gpt-5.4-mini", "openai", "Online"),
    ("thanos", "Thanos", "🟣", "Experimentation", "zai/glm-5.1", "zai", "Idle"),
]


def ensure_agent(db: Session, agent_id: str, name: str, avatar: str, role: str, model: str, provider: str, status: str) -> None:
    agent = db.get(Agent, agent_id)
    if agent:
        agent.name = name
        agent.avatar = avatar
        agent.role = role
        agent.model = model
        agent.provider = provider
        agent.status = status
        agent.last_active = datetime.utcnow().isoformat()
        db.add(agent)
        return
    db.add(
        Agent(
            id=agent_id,
            name=name,
            avatar=avatar,
            role=role,
            model=model,
            provider=provider,
            status=status,
            last_active=datetime.utcnow().isoformat(),
        )
    )


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


def ensure_task(
    db: Session,
    project_id: int,
    sprint_id: int,
    title: str,
    description: str,
    assignee_id: str,
    reporter_id: str,
    priority: str,
    status: str,
    due_date: str,
):
    task = db.query(Task).filter(Task.project_id == project_id, Task.title == title).first()
    if task:
        task.description = description
        task.assignee_id = assignee_id
        task.reporter_id = reporter_id
        task.priority = priority
        task.status = status
        task.sprint_id = sprint_id
        task.due_date = due_date
        task.tags = "agentos"
        task.updated_at = datetime.utcnow().isoformat()
        db.add(task)
        return task
    task = Task(
        project_id=project_id,
        sprint_id=sprint_id,
        title=title,
        description=description,
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        priority=priority,
        status=status,
        tags="agentos",
        due_date=due_date,
    )
    db.add(task)
    return task


def ensure_key(db: Session, agent_id: str, key: str) -> None:
    if not db.query(ApiKey).filter(ApiKey.key == key).first():
        db.add(ApiKey(agent_id=agent_id, key=key))


def seed(db: Session):
    for agent in AGENTS:
        ensure_agent(db, *agent)
    db.commit()

    project = ensure_project(db, "AgentOS", "Multi-agent project management", "Active", "gandalf")
    db.commit()
    db.refresh(project)

    sprint = ensure_sprint(
        db,
        project.id,
        "MVP Sprint",
        datetime.utcnow().date().isoformat(),
        (datetime.utcnow() + timedelta(days=14)).date().isoformat(),
    )
    db.commit()
    db.refresh(sprint)

    due_today = datetime.utcnow().date()
    tasks = [
        (
            "Build backend API",
            "Implement tasks, projects, agents, usage endpoints",
            "linus",
            "gandalf",
            "P1",
            "In Progress",
            due_today + timedelta(days=2),
        ),
        (
            "Design dark UI",
            "Minimal dashboard and navigation",
            "ive",
            "gandalf",
            "P2",
            "To Do",
            due_today + timedelta(days=4),
        ),
        (
            "Usage parser",
            "Read OpenClaw session stores",
            "thanos",
            "linus",
            "P1",
            "Backlog",
            due_today + timedelta(days=5),
        ),
        (
            "Approval flow",
            "Support Utkarsh approvals",
            "utkarsh",
            "gandalf",
            "P0",
            "In Review",
            due_today + timedelta(days=3),
        ),
    ]
    for title, desc, assignee, reporter, priority, status, due in tasks:
        ensure_task(
            db,
            project.id,
            sprint.id,
            title,
            desc,
            assignee,
            reporter,
            priority,
            status,
            due.isoformat(),
        )

    for agent_id in ["gandalf", "ive", "linus", "thanos", "utkarsh"]:
        ensure_key(db, agent_id, f"{agent_id}-key")

    db.commit()
