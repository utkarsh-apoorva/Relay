import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Agent, ApiKey, Comment, Project, Sprint, Task
from .seed import seed

API_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(title="Relay", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed(db)


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def parse_tags(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        items = [part.strip() for part in str(value).replace("\n", ",").split(",") if part.strip()]
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return ", ".join(deduped)


def api_owner(x_api_key: Optional[str], db: Session) -> ApiKey:
    if not x_api_key:
        raise HTTPException(401, "Missing API key")
    key = db.query(ApiKey).filter(ApiKey.key == x_api_key).first()
    if not key:
        raise HTTPException(401, "Invalid API key")
    return key


def resolve_actor_name(actor_id: Optional[str], db: Session) -> str:
    if not actor_id:
        return ""
    if actor_id == "utkarsh":
        return "Utkarsh"
    agent = db.query(Agent).filter(Agent.id == actor_id).first()
    return agent.name if agent else actor_id


def touch_project(project_id: int, db: Session) -> None:
    project = db.get(Project, project_id)
    if project:
        project.updated_at = now_iso()
        db.add(project)
        db.commit()


def serialize_comments(task_id: int, db: Session) -> list[dict[str, Any]]:
    comments = db.query(Comment).filter(Comment.task_id == task_id).order_by(Comment.created_at.asc()).all()
    return [
        {
            "id": c.id,
            "author_id": c.author_id,
            "author_type": c.author_type,
            "content": c.content,
            "created_at": c.created_at,
        }
        for c in comments
    ]


def serialize_task(task: Task, db: Session) -> dict[str, Any]:
    payload = {
        "id": task.id,
        "project_id": task.project_id,
        "sprint_id": task.sprint_id,
        "title": task.title,
        "description": task.description,
        "assignee_id": task.assignee_id,
        "assignee_name": resolve_actor_name(task.assignee_id, db),
        "reporter_id": task.reporter_id,
        "reporter_name": resolve_actor_name(task.reporter_id, db),
        "priority": task.priority,
        "status": task.status,
        "tags": task.tags,
        "due_date": task.due_date,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "comments": serialize_comments(task.id, db),
    }
    project = db.get(Project, task.project_id)
    sprint = db.get(Sprint, task.sprint_id) if task.sprint_id else None
    payload["project_name"] = project.name if project else ""
    payload["sprint_name"] = sprint.name if sprint else ""
    return payload


def serialize_project(project: Project, db: Session) -> dict[str, Any]:
    tasks = db.query(Task).filter(Task.project_id == project.id).all()
    total = len(tasks)
    done = sum(1 for task in tasks if task.status == "Done")
    lead_name = resolve_actor_name(project.lead_agent_id, db)
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "lead_agent_id": project.lead_agent_id,
        "lead_agent_name": lead_name,
        "sprint_count": db.query(Sprint).filter(Sprint.project_id == project.id).count(),
        "task_count": total,
        "% done": round((done / total * 100) if total else 0, 1),
        "last_updated": project.updated_at,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"ok": "true"}


@app.get("/api/projects")
def list_projects(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    return [serialize_project(project, db) for project in db.query(Project).order_by(Project.updated_at.desc()).all()]


@app.post("/api/projects")
def create_project(
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    owner = api_owner(x_api_key, db)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "Project name is required")
    project = Project(
        name=name,
        description=str(payload.get("description", "")).strip(),
        status=payload.get("status", "Active"),
        lead_agent_id=payload.get("lead_agent_id") or owner.agent_id or "gandalf",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_project(project, db)


@app.patch("/api/projects/{project_id}")
def patch_project(
    project_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for field in ["name", "description", "status", "lead_agent_id"]:
        if field in payload:
            setattr(project, field, payload[field])
    project.updated_at = now_iso()
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_project(project, db)


@app.get("/api/agents")
def list_agents(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    agents = db.query(Agent).order_by(Agent.name.asc()).all()
    result = []
    for agent in agents:
        tasks = db.query(Task).filter(Task.assignee_id == agent.id).all()
        in_progress = sum(1 for task in tasks if task.status == "In Progress")
        result.append(
            {
                "id": agent.id,
                "name": agent.name,
                "avatar": agent.avatar,
                "role": agent.role,
                "model": agent.model,
                "provider": agent.provider,
                "status": agent.status,
                "last_active": agent.last_active,
                "current_tasks": in_progress,
                "total_tasks": len(tasks),
            }
        )
    return result


@app.get("/api/tasks")
def list_tasks(
    project_id: Optional[int] = None,
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
    sprint_id: Optional[int] = None,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    query = db.query(Task)
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)
    if status is not None:
        query = query.filter(Task.status == status)
    if sprint_id is not None:
        query = query.filter(Task.sprint_id == sprint_id)
    tasks = query.order_by(Task.updated_at.desc()).all()
    return [serialize_task(task, db) for task in tasks]


@app.post("/api/tasks")
def create_task(
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    owner = api_owner(x_api_key, db)
    title = str(payload.get("title", "")).strip()
    if not title:
        raise HTTPException(400, "Task title is required")
    reporter_id = str(payload.get("reporter_id") or owner.agent_id or "utkarsh")
    assignee_id = str(payload.get("assignee_id") or reporter_id)
    tags = [tag for tag in parse_tags(payload.get("tags")).split(", ") if tag]
    for tag in {owner.agent_id, reporter_id}:
        if tag and tag not in tags and tag != "utkarsh":
            tags.append(tag)
    sprint_id = payload.get("sprint_id")
    sprint_id = int(sprint_id) if sprint_id not in (None, "", "null") else None
    task = Task(
        project_id=int(payload["project_id"]),
        sprint_id=sprint_id,
        title=title,
        description=str(payload.get("description", "")).strip(),
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        priority=payload.get("priority", "P2"),
        status=payload.get("status", "Backlog"),
        tags=", ".join(tags),
        due_date=str(payload.get("due_date", "")).strip(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    comment = str(payload.get("comment", "")).strip()
    if comment:
        db.add(
            Comment(
                task_id=task.id,
                author_id=reporter_id,
                author_type="human" if reporter_id == "utkarsh" else "agent",
                content=comment,
            )
        )
        db.commit()
    touch_project(task.project_id, db)
    return serialize_task(task, db)


@app.patch("/api/tasks/{task_id}")
def patch_task(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    for field in ["title", "description", "assignee_id", "reporter_id", "priority", "status", "due_date"]:
        if field in payload:
            setattr(task, field, payload[field])
    if "tags" in payload:
        task.tags = parse_tags(payload["tags"])
    if "sprint_id" in payload:
        sprint_id = payload["sprint_id"]
        task.sprint_id = int(sprint_id) if sprint_id not in (None, "", "null") else None
    task.updated_at = now_iso()
    db.add(task)
    db.commit()
    db.refresh(task)
    touch_project(task.project_id, db)
    return serialize_task(task, db)


@app.post("/api/tasks/{task_id}/comment")
def add_comment(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    content = str(payload.get("content", "")).strip()
    if not content:
        raise HTTPException(400, "Comment content is required")
    author_id = str(payload.get("author_id", "utkarsh"))
    db.add(
        Comment(
            task_id=task_id,
            author_id=author_id,
            author_type=payload.get("author_type", "human"),
            content=content,
        )
    )
    task.updated_at = now_iso()
    db.add(task)
    db.commit()
    touch_project(task.project_id, db)
    return {"ok": True}


@app.get("/api/sprints")
def list_sprints(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    query = db.query(Sprint)
    if project_id is not None:
        query = query.filter(Sprint.project_id == project_id)
    return [
        {
            "id": sprint.id,
            "project_id": sprint.project_id,
            "name": sprint.name,
            "start_date": sprint.start_date,
            "end_date": sprint.end_date,
        }
        for sprint in query.order_by(Sprint.id.desc()).all()
    ]


@app.post("/api/sprints")
def create_sprint(
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "Sprint name is required")
    sprint = Sprint(
        project_id=int(payload["project_id"]),
        name=name,
        start_date=str(payload.get("start_date", "")).strip(),
        end_date=str(payload.get("end_date", "")).strip(),
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    touch_project(sprint.project_id, db)
    return {
        "id": sprint.id,
        "project_id": sprint.project_id,
        "name": sprint.name,
        "start_date": sprint.start_date,
        "end_date": sprint.end_date,
    }


@app.get("/api/usage/tokens")
def usage_tokens(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    root = Path.home() / ".openclaw" / "agents"
    rates = {
        "openai/gpt-5.4-mini": 0.000015,
        "anthropic/claude-sonnet-4-6": 0.00003,
        "zai/glm-5.1": 0.00001,
    }
    rows: list[dict[str, Any]] = []
    totals: dict[tuple[str, str], int] = {}
    if root.exists():
        for agent_dir in root.iterdir():
            session_file = agent_dir / "sessions" / "sessions.json"
            if not session_file.exists():
                continue
            try:
                data = json.loads(session_file.read_text())
            except Exception:
                continue
            entries = data if isinstance(data, list) else data.get("sessions", [])
            for entry in entries:
                model = entry.get("model", "unknown")
                usage = entry.get("usage", {}) if isinstance(entry, dict) else {}
                tokens = int(usage.get("total_tokens", entry.get("total_tokens", 0))) if isinstance(entry, dict) else 0
                cost = round(tokens / 1000 * rates.get(model, 0.0), 4)
                agent = agent_dir.name
                rows.append({"agent": agent, "model": model, "tokens": tokens, "estimated_cost": cost})
                totals[(agent, model)] = totals.get((agent, model), 0) + tokens
    if not rows:
        for agent in db.query(Agent).order_by(Agent.name.asc()).all():
            rows.append({"agent": agent.name, "model": agent.model, "tokens": 0, "estimated_cost": 0.0})
            totals[(agent.name, agent.model)] = 0
    return {
        "rows": rows,
        "totals": [
            {"agent": agent, "model": model, "tokens": tokens}
            for (agent, model), tokens in totals.items()
        ],
    }


@app.get("/api/calendar")
def calendar_view(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    query = db.query(Task).filter(Task.due_date != "")
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    tasks = query.order_by(Task.due_date.asc(), Task.title.asc()).all()
    result = []
    for task in tasks:
        project = db.get(Project, task.project_id)
        result.append(
            {
                "id": task.id,
                "title": task.title,
                "due_date": task.due_date,
                "project_id": task.project_id,
                "project_name": project.name if project else "",
                "status": task.status,
                "assignee_id": task.assignee_id,
                "assignee_name": resolve_actor_name(task.assignee_id, db),
            }
        )
    return result


@app.get("/api/approval-queue")
def approval_queue(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    api_owner(x_api_key, db)
    tasks = db.query(Task).filter(Task.assignee_id == "utkarsh").order_by(Task.updated_at.desc()).all()
    return [serialize_task(task, db) for task in tasks]
