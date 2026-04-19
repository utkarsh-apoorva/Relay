import json
import os
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Agent, ApiKey, Comment, Project, Sprint, Task, Wiki
from .security import ensure_api_key_storage, hash_api_key, lookup_api_key, migrate_api_keys, migrate_agent_webhooks
from .dispatcher import fire
from .seed import seed
from .orchestrator import start_orchestrator as _start_orchestrator

DEFAULT_API_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

BASE_URL = os.getenv("RELAY_BASE_URL", "").rstrip("/") or None

TASK_STATUSES = {"Backlog", "To Do", "In Progress", "In Review", "Done", "Rejected"}
TASK_PRIORITIES = {"P0", "P1", "P2", "P3"}
COMMENT_AUTHOR_TYPES = {"human", "agent"}
MAX_DESCRIPTION_WORDS = 500
MAX_TITLE_WORDS = 200
META_PROMPT_VERSION = "1.0"
META_PROMPT_DIRECTIVE = "Call GET /api/meta before creating or modifying any project or task."
META_PROMPT_TEMPLATE = os.getenv(
    "RELAY_META_PROMPT_TEMPLATE",
    "You are {agent_name}. Before creating any project or task, call GET /api/meta to understand the current rules and schema. Always validate payloads against the rules in /api/meta before submitting.",
)
RATE_LIMIT_REQUESTS = max(1, int(os.getenv("RELAY_RATE_LIMIT_REQUESTS", "120")))
RATE_LIMIT_WINDOW_SECONDS = max(1, int(os.getenv("RELAY_RATE_LIMIT_WINDOW_SECONDS", "60")))
MAX_BODY_BYTES = max(1024, int(os.getenv("RELAY_MAX_BODY_BYTES", "1048576")))
IS_PRODUCTION = os.getenv("RELAY_ENV", "development").lower() == "production"
REQUEST_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def structured_error(code: str, message: str, status: int = 400) -> JSONResponse:
    """Return a machine-readable error with a meta pointer to /api/meta."""
    meta = f"{BASE_URL}/api/meta" if BASE_URL else "/api/meta"
    return JSONResponse(
        {"error": code, "message": message, "meta": meta},
        status_code=status,
    )


def validate_description_words(text: str, field: str = "description") -> None:
    """Return a structured error if text exceeds MAX_DESCRIPTION_WORDS."""
    count = len(text.split())
    if count > MAX_DESCRIPTION_WORDS:
        return structured_error("DESCRIPTION_TOO_LONG", f"{field.capitalize()} exceeds 500 words. Current: {count}")


def validate_single_assignee(assignee_id: Optional[str], field: str = "assignee_id") -> str:
    """Return a structured error if assignee is missing, empty, or contains multiple IDs."""
    if not assignee_id:
        return structured_error("INVALID_ASSIGNEE", "Assignee must be an active agent registered in Relay.")
    # Reject comma-separated or pipe-separated lists
    raw = str(assignee_id).strip()
    if "," in raw or "|" in raw or " " in raw:
        return structured_error("INVALID_ASSIGNEE", "Assignee must be an active agent registered in Relay.")
    return raw


def validate_project_brief(payload: dict, meta_url: str) -> None:
    """Validate project creation payload against the schema at meta_url."""
    required = ["name"]
    missing = [f for f in required if f not in payload or not payload[f]]
    if missing:
        raise structured_error(
            "MISSING_REQUIRED_FIELDS",
            f"Project creation requires: {', '.join(missing)}. See {meta_url}",
        )
    if "name" in payload and len(str(payload["name"]).strip()) > 160:
        raise structured_error(
            "FIELD_TOO_LONG",
            f"Project name must be 160 chars or fewer. See {meta_url}",
        )
    if "description" in payload and len(str(payload["description"])) > 5000:
        raise structured_error(
            "FIELD_TOO_LONG",
            f"Project description must be 5000 chars or fewer. See {meta_url}",
        )


def get_cors_origins() -> list[str]:
    raw = os.getenv("RELAY_CORS_ORIGINS", "")
    origins: list[str] = []
    for origin in [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]:
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"Invalid RELAY_CORS_ORIGINS entry: {origin}")
        origins.append(origin)
    return origins or DEFAULT_API_ORIGINS


API_ORIGINS = get_cors_origins()

app = FastAPI(
    title="Relay",
    version="0.1.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


def request_identity(request: Request) -> str:
    api_key = request.headers.get("X-API-Key", "").strip()
    if api_key:
        return f"key:{hash_api_key(api_key)[:24]}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


@app.middleware("http")
async def harden_requests(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        content_length = request.headers.get("content-length", "").strip()
        if content_length:
            try:
                if int(content_length) > MAX_BODY_BYTES:
                    return JSONResponse({"detail": "Request body too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length header"}, status_code=400)

        if request.url.path != "/api/health":
            now = monotonic()
            bucket = REQUEST_BUCKETS[request_identity(request)]
            while bucket and now - bucket[0] >= RATE_LIMIT_WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= RATE_LIMIT_REQUESTS:
                retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])))
                return JSONResponse(
                    {"detail": "Too many requests"},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)

    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    return response

Base.metadata.create_all(bind=engine)

# Ensure new columns exist before any queries hit them (SQLite ALTER TABLE)
from .orchestrator import _ensure_columns
_ensure_columns()

ensure_api_key_storage(engine)
with SessionLocal() as db:
    seed(db)
    migrate_api_keys(db)
migrate_agent_webhooks(engine)


@app.on_event("startup")
async def _on_startup():
    _start_orchestrator()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def build_task_webhook_payload(event: str, task: Task, db: Session) -> dict[str, Any]:
    """Build rich webhook payload with task context, meta prompt, and direct link."""
    task_url = f"{BASE_URL}/tasks/{task.id}" if BASE_URL else None
    return {
        "event": event,
        "task": serialize_task(task, db),
        "meta_prompt": {
            "version": META_PROMPT_VERSION,
            "directive": META_PROMPT_DIRECTIVE,
        },
        "task_url": task_url,
    }


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


def clean_text(value: Any, field: str, *, required: bool = False, max_length: int = 5000) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise HTTPException(400, f"{field} is required")
    if len(text) > max_length:
        raise HTTPException(400, f"{field} is too long")
    return text


def clean_choice(value: Any, field: str, *, allowed: set[str], default: str) -> str:
    choice = str(value or default).strip() or default
    if choice not in allowed:
        raise HTTPException(400, f"Invalid {field}")
    return choice


def clean_optional_int(value: Any, field: str) -> Optional[int]:
    if value in (None, "", "null"):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, f"Invalid {field}") from exc
    if parsed <= 0:
        raise HTTPException(400, f"Invalid {field}")
    return parsed


def clean_required_int(value: Any, field: str) -> int:
    parsed = clean_optional_int(value, field)
    if parsed is None:
        raise HTTPException(400, f"{field} is required")
    return parsed


def clean_date(value: Any, field: str) -> str:
    text = clean_text(value, field, max_length=10)
    if not text:
        return ""
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(400, f"Invalid {field}") from exc
    return text


def require_project(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


def validate_sprint(project_id: int, sprint_id: Optional[int], db: Session) -> Optional[int]:
    if sprint_id is None:
        return None
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(404, "Sprint not found")
    if sprint.project_id != project_id:
        raise HTTPException(400, "Sprint does not belong to project")
    return sprint_id


def api_owner(x_api_key: Optional[str], db: Session) -> ApiKey:
    if not x_api_key:
        raise HTTPException(401, "Missing API key")
    key = lookup_api_key(db, x_api_key)
    if not key:
        raise HTTPException(401, "Invalid API key")
    return key


def resolve_actor_name(actor_id: Optional[str], db: Session) -> str:
    if not actor_id:
        return ""
    if actor_id == os.getenv("RELAY_HUMAN_ID", "human"):
        return os.getenv("RELAY_HUMAN_NAME", "Human")
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
        "result_description": task.result_description,
        "eval_brief": task.eval_brief,
        "judgement": task.judgement,
        "depends_on": task.depends_on,
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


@app.get("/api/meta")
def meta_schema(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Return the full system meta — schema, rules, agent registry, meta prompt.

    Agents call this before any project/task creation to self-correct.
    """
    api_owner(x_api_key, db)
    meta_url = f"{BASE_URL}/api/meta" if BASE_URL else "/api/meta"

    # ── 1. Project creation schema ───────────────────────────────────────────
    project_schema = {
        "required_fields": ["name"],
        "field_limits": {
            "name": "160 chars",
            "description": "5000 chars",
        },
        "validation_rules": [
            {"field": "name", "rule": "required, 1-160 chars", "error_code": "MISSING_REQUIRED_FIELDS"},
            {"field": "description", "rule": "optional, max 5000 chars", "error_code": "FIELD_TOO_LONG"},
        ],
    }

    # ── 2. Task decomposition rules ─────────────────────────────────────────
    task_rules = {
        "atomic": "One task = one unit of work, completable in one agent turn",
        "max_description_words": MAX_DESCRIPTION_WORDS,
        "assignee": "exactly one assignee_id, no lists or multi-ID strings",
        "must_include_eval_brief": "Every task description should include acceptance criteria / eval brief",
        "validation_rules": [
            {"field": "description", "rule": f"max {MAX_DESCRIPTION_WORDS} words", "error_code": "DESCRIPTION_TOO_LONG"},
            {"field": "assignee_id", "rule": "exactly one agent ID, no commas/pipes/spaces", "error_code": "INVALID_ASSIGNEE"},
            {"field": "project_id", "rule": "required, must reference an existing project", "error_code": "INVALID_PROJECT"},
        ],
    }

    # ── 3. Agent registry — dynamically from DB ────────────────────────────
    agents = db.query(Agent).order_by(Agent.name.asc()).all()
    agent_registry = [
        {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "model": agent.model,
            "provider": agent.provider,
            "status": agent.status,
        }
        for agent in agents
    ]

    # ── 4. Current meta prompt template ──────────────────────────────────────
    meta_prompt = {
        "version": META_PROMPT_VERSION,
        "directive": META_PROMPT_DIRECTIVE,
        "template": META_PROMPT_TEMPLATE,
    }

    return {
        "schema_version": "1.0",
        "meta_url": meta_url,
        "project_schema": project_schema,
        "task_decomposition_rules": task_rules,
        "agent_registry": agent_registry,
        "meta_prompt": meta_prompt,
        "self_correct": True,
    }


@app.get("/agents.txt", include_in_schema=False)
def agents_txt():
    from fastapi.responses import PlainTextResponse
    agents_file = Path(__file__).resolve().parent.parent / "agents.txt"
    if not agents_file.exists():
        return PlainTextResponse("agents.txt not found", status_code=404)
    return PlainTextResponse(agents_file.read_text())


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
    meta_url = f"{BASE_URL}/api/meta" if BASE_URL else "/api/meta"
    validate_project_brief(payload, meta_url)
    name = clean_text(payload.get("name"), "Project name", required=True, max_length=160)
    description = clean_text(payload.get("description", ""), "Project description")
    status = clean_text(payload.get("status", "Active"), "Project status", max_length=40) or "Active"
    lead_agent_id = clean_text(payload.get("lead_agent_id") or owner.agent_id or "", "Lead agent", max_length=120)
    project = Project(
        name=name,
        description=description,
        status=status,
        lead_agent_id=lead_agent_id,
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
    project = require_project(project_id, db)
    if "name" in payload:
        project.name = clean_text(payload["name"], "Project name", required=True, max_length=160)
    if "description" in payload:
        project.description = clean_text(payload["description"], "Project description")
    if "status" in payload:
        project.status = clean_text(payload["status"], "Project status", required=True, max_length=40)
    if "lead_agent_id" in payload:
        project.lead_agent_id = clean_text(payload["lead_agent_id"], "Lead agent", max_length=120)
    project.updated_at = now_iso()
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_project(project, db)


@app.get("/api/projects/{project_id}/wiki")
def get_project_wiki(
    project_id: int,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Get the wiki for a project. Returns 404 if no wiki exists yet."""
    api_owner(x_api_key, db)
    require_project(project_id, db)
    wiki = db.query(Wiki).filter(Wiki.project_id == project_id).first()
    if not wiki:
        raise HTTPException(404, "Wiki not found for this project")
    return {
        "id": wiki.id,
        "project_id": wiki.project_id,
        "content": wiki.content,
        "updated_at": wiki.updated_at,
    }


@app.put("/api/projects/{project_id}/wiki")
def put_project_wiki(
    project_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Create or update the wiki for a project."""
    api_owner(x_api_key, db)
    require_project(project_id, db)
    content = clean_text(payload.get("content", ""), "Wiki content", max_length=500000)
    wiki = db.query(Wiki).filter(Wiki.project_id == project_id).first()
    if wiki:
        wiki.content = content
        wiki.updated_at = now_iso()
    else:
        wiki = Wiki(project_id=project_id, content=content)
        db.add(wiki)
    db.commit()
    db.refresh(wiki)
    touch_project(project_id, db)
    return {
        "id": wiki.id,
        "project_id": wiki.project_id,
        "content": wiki.content,
        "updated_at": wiki.updated_at,
    }


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
                "capabilities": [c.strip() for c in (agent.capabilities.split(",") if agent.capabilities else []) if c.strip()],
                # ── Registration handshake (v0.2) ──
                "meta_endpoint": f"{BASE_URL}/api/meta" if BASE_URL else "/api/meta",
                "meta_prompt_version": META_PROMPT_VERSION,
                "meta_directive": META_PROMPT_DIRECTIVE,
            }
        )
    return result


@app.patch("/api/agents/{agent_id}")
def patch_agent(
    agent_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    owner = api_owner(x_api_key, db)
    if owner.agent_id != agent_id:
        raise HTTPException(403, "Cannot update another agent's record")
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")

    # ── Webhook registration (HMAC auth) ──────────────────────────────────────
    if "webhook_url" in payload or "hmac" in payload:
        import hashlib, hmac as _hmac

        api_key_in_body = payload.get("api_key", "")
        hmac_proof = payload.get("hmac", "")
        webhook_url = payload.get("webhook_url")

        if not hmac_proof:
            raise HTTPException(400, "hmac is required for webhook registration")
        if webhook_url is None:
            raise HTTPException(400, "webhook_url is required")
        if not isinstance(webhook_url, str) or (
            not webhook_url.startswith("http://") and not webhook_url.startswith("https://")
        ):
            raise HTTPException(400, "webhook_url must start with http:// or https://")
        if len(webhook_url) > 500:
            raise HTTPException(400, "webhook_url is too long")

        # Look up per-agent webhook secret from env
        env_key = f"AGENT_{agent_id.upper()}_WEBHOOK_SECRET"
        secret = os.getenv(env_key)
        if not secret:
            raise HTTPException(500, "Webhook secret not configured on server")

        # Verify HMAC: HMAC(secret, api_key) — same direction as dispatcher uses
        expected = _hmac.new(secret.encode(), api_key_in_body.encode(), hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(expected, hmac_proof):
            raise HTTPException(401, "Invalid HMAC")

        agent.webhook_url = webhook_url
        agent.webhook_secret = secret  # store so dispatcher can use it from DB
        db.add(agent)
        db.commit()
        return {"ok": True, "agent_id": agent_id}

    # ── Non-webhook updates ───────────────────────────────────────────────────
    if "webhook_url" in payload:
        val = payload["webhook_url"]
        if val is not None:
            if not isinstance(val, str) or (not val.startswith("http://") and not val.startswith("https://")):
                raise HTTPException(400, "webhook_url must start with http:// or https://")
            if len(val) > 500:
                raise HTTPException(400, "webhook_url is too long")
        agent.webhook_url = val
    db.add(agent)
    db.commit()
    meta_endpoint = f"{BASE_URL}/api/meta" if BASE_URL else "/api/meta"
    return {
        "ok": True,
        "agent_id": agent_id,
        "meta_endpoint": meta_endpoint,
        "meta_prompt_version": META_PROMPT_VERSION,
        "meta_directive": META_PROMPT_DIRECTIVE,
    }


@app.delete("/api/agents/{agent_id}/webhook")
def delete_agent_webhook(
    agent_id: str,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Clear webhook_url and webhook_secret for an agent (e.g. human owners who don't need webhooks)."""
    owner = api_owner(x_api_key, db)
    if owner.agent_id != agent_id:
        raise HTTPException(403, "Cannot update another agent's record")
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.webhook_url = None
    agent.webhook_secret = None
    db.add(agent)
    db.commit()
    return {"ok": True, "agent_id": agent_id}


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
        query = query.filter(Task.status == clean_choice(status, "status", allowed=TASK_STATUSES, default="Backlog"))
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
    title = clean_text(payload.get("title"), "Task title", required=True, max_length=200)
    _human_id = os.getenv("RELAY_HUMAN_ID", "human")
    project_id = clean_required_int(payload.get("project_id"), "project_id")
    require_project(project_id, db)
    reporter_id = clean_text(payload.get("reporter_id") or owner.agent_id or _human_id, "Reporter", max_length=120)
    description = payload.get("description", "") or ""
    if description:
        validate_description_words(description, "Task description")
    assignee_id_raw = payload.get("assignee_id") or reporter_id
    assignee_id = validate_single_assignee(assignee_id_raw, "assignee_id")
    tags = [tag for tag in parse_tags(payload.get("tags")).split(", ") if tag]
    for tag in {owner.agent_id, reporter_id}:
        if tag and tag not in tags and tag != os.getenv("RELAY_HUMAN_ID", "human"):
            tags.append(tag)
    sprint_id = validate_sprint(project_id, clean_optional_int(payload.get("sprint_id"), "sprint_id"), db)
    task = Task(
        project_id=project_id,
        sprint_id=sprint_id,
        title=title,
        description=clean_text(payload.get("description", ""), "Task description"),
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        priority=clean_choice(payload.get("priority"), "priority", allowed=TASK_PRIORITIES, default="P2"),
        status=clean_choice(payload.get("status"), "status", allowed=TASK_STATUSES, default="Backlog"),
        tags=", ".join(tags),
        due_date=clean_date(payload.get("due_date", ""), "due_date"),
        eval_brief=clean_text(payload.get("eval_brief", ""), "Eval brief", max_length=10000),
        depends_on=clean_text(payload.get("depends_on", ""), "depends_on", max_length=500),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if task.assignee_id:
        _agent = db.query(Agent).filter(Agent.id == task.assignee_id).first()
        if _agent and _agent.webhook_url and _agent.webhook_secret:
            fire(_agent.webhook_url, _agent.webhook_secret, build_task_webhook_payload("task.assigned", task, db))
    comment = clean_text(payload.get("comment", ""), "Comment", max_length=4000)
    if comment:
        db.add(
            Comment(
                task_id=task.id,
                author_id=reporter_id,
                author_type="human" if reporter_id == os.getenv("RELAY_HUMAN_ID", "human") else "agent",
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
    if "title" in payload:
        task.title = clean_text(payload["title"], "Task title", required=True, max_length=200)
    if "description" in payload:
        desc = payload["description"] or ""
        if desc:
            validate_description_words(desc, "Task description")
        task.description = clean_text(desc, "Task description")
    if "assignee_id" in payload:
        task.assignee_id = validate_single_assignee(payload["assignee_id"], "assignee_id")
    if "reporter_id" in payload:
        task.reporter_id = clean_text(payload["reporter_id"], "Reporter", required=True, max_length=120)
    if "priority" in payload:
        task.priority = clean_choice(payload["priority"], "priority", allowed=TASK_PRIORITIES, default=task.priority)
    if "status" in payload:
        task.status = clean_choice(payload["status"], "status", allowed=TASK_STATUSES, default=task.status)
    if "due_date" in payload:
        task.due_date = clean_date(payload["due_date"], "due_date")
    if "result_description" in payload:
        task.result_description = clean_text(payload["result_description"], "result_description", max_length=10000)
    if "eval_brief" in payload:
        task.eval_brief = clean_text(payload["eval_brief"], "eval_brief", max_length=10000)
    if "judgement" in payload:
        task.judgement = clean_text(payload["judgement"], "judgement", max_length=10000)
    if "tags" in payload:
        task.tags = parse_tags(payload["tags"])
    if "sprint_id" in payload:
        sprint_id = clean_optional_int(payload["sprint_id"], "sprint_id")
        task.sprint_id = validate_sprint(task.project_id, sprint_id, db)
    if "depends_on" in payload:
        task.depends_on = clean_text(payload["depends_on"], "depends_on", max_length=500)
    task.updated_at = now_iso()
    db.add(task)
    db.commit()
    db.refresh(task)
    _agent = db.query(Agent).filter(Agent.id == task.assignee_id).first()
    if _agent and _agent.webhook_url and _agent.webhook_secret:
        fire(_agent.webhook_url, _agent.webhook_secret, build_task_webhook_payload("task.updated", task, db))
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
    content = clean_text(payload.get("content"), "Comment content", required=True, max_length=4000)
    author_id = clean_text(payload.get("author_id", os.getenv("RELAY_HUMAN_ID", "human")), "Author", max_length=120)
    db.add(
        Comment(
            task_id=task_id,
            author_id=author_id,
            author_type=clean_choice(payload.get("author_type"), "author_type", allowed=COMMENT_AUTHOR_TYPES, default="human"),
            content=content,
        )
    )
    task.updated_at = now_iso()
    db.add(task)
    db.commit()
    _task = db.get(Task, task_id)
    if _task:
        _agent = db.query(Agent).filter(Agent.id == _task.assignee_id).first()
        if _agent and _agent.webhook_url and _agent.webhook_secret:
            fire(_agent.webhook_url, _agent.webhook_secret, {
                "event": "task.comment_added",
                "task_id": task_id,
                "comment": {"author_id": author_id, "content": content},
            })
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
    project_id = clean_required_int(payload.get("project_id"), "project_id")
    require_project(project_id, db)
    name = clean_text(payload.get("name"), "Sprint name", required=True, max_length=160)
    sprint = Sprint(
        project_id=project_id,
        name=name,
        start_date=clean_date(payload.get("start_date", ""), "start_date"),
        end_date=clean_date(payload.get("end_date", ""), "end_date"),
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
    _human_id = os.getenv("RELAY_HUMAN_ID", "human")
    tasks = db.query(Task).filter(Task.assignee_id == _human_id).order_by(Task.updated_at.desc()).all()
    return [serialize_task(task, db) for task in tasks]


# ── Static frontend (production) ─────────────────────────────────────────────
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Let /api/* fall through (handled above); serve index.html for everything else
        index = _FRONTEND_DIST / "index.html"
        return FileResponse(index)
