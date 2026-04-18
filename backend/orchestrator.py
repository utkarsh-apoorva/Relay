"""
Relay-native orchestrator runtime (MVP).

Processes orchestration kickoff tasks: decomposes a project brief into child
tasks, assigns them to agents, and transitions the project from
Orchestrating → Active (or → Failed).

Design choices (MVP):
  - Runs as a background thread, started at app boot when RELAY_ORCHESTRATOR_ENABLED=1.
  - Polls for tasks tagged "orchestration-kickoff" in status "To Do".
  - If RELAY_ORCHESTRATOR_MODEL is set with valid credentials, uses an LLM to plan.
  - Otherwise falls back to deterministic heuristic decomposition.
  - All planning respects Relay rules: max 500-word descriptions, exactly one
    assignee, eval_brief on every child task.
"""

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Agent, Comment, Project, Task
from .dispatcher import fire

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

ORCHESTRATOR_ID = os.getenv("RELAY_ORCHESTRATOR_ID", "orchestrator")
ORCHESTRATOR_NAME = os.getenv("RELAY_ORCHESTRATOR_NAME", "Orchestrator")
ORCHESTRATOR_AVATAR = os.getenv("RELAY_ORCHESTRATOR_AVATAR", "🎯")
ORCHESTRATOR_ROLE = os.getenv("RELAY_ORCHESTRATOR_ROLE", "Orchestrator")

ORCHESTRATOR_MODEL = os.getenv("RELAY_ORCHESTRATOR_MODEL", "")  # e.g. "openai/gpt-5.4"
ORCHESTRATOR_API_KEY = os.getenv("RELAY_ORCHESTRATOR_API_KEY", "")
ORCHESTRATOR_API_BASE = os.getenv("RELAY_ORCHESTRATOR_API_BASE", "")
ORCHESTRATOR_FALLBACK_MODEL = os.getenv("RELAY_ORCHESTRATOR_FALLBACK_MODEL", "")

POLL_INTERVAL = max(2, int(os.getenv("RELAY_ORCHESTRATOR_POLL_SECONDS", "5")))
MAX_DESCRIPTION_WORDS = 500
MIN_BRIEF_WORDS = 10  # If project description is shorter, reject as too vague.

# ── Lightweight migration: ensure new columns exist ──────────────────────────

_migrated = False


def _ensure_columns() -> None:
    """Add depends_on / capabilities columns if missing (SQLite ALTER TABLE)."""
    global _migrated
    if _migrated:
        return
    _migrated = True
    from .database import engine
    import sqlite3
    conn = sqlite3.connect(str(engine.url).replace("sqlite:///", ""))
    cur = conn.cursor()
    # Task.depends_on
    cur.execute("PRAGMA table_info(tasks)")
    cols = {row[1] for row in cur.fetchall()}
    if "depends_on" not in cols:
        cur.execute("ALTER TABLE tasks ADD COLUMN depends_on TEXT DEFAULT ''")
        logger.info("Added depends_on column to tasks")
    # Agent.capabilities
    cur.execute("PRAGMA table_info(agents)")
    cols = {row[1] for row in cur.fetchall()}
    if "capabilities" not in cols:
        cur.execute("ALTER TABLE agents ADD COLUMN capabilities TEXT DEFAULT ''")
        logger.info("Added capabilities column to agents")
    if "webhook_url" not in cols:
        cur.execute("ALTER TABLE agents ADD COLUMN webhook_url TEXT")
        logger.info("Added webhook_url column to agents")
    if "webhook_secret" not in cols:
        cur.execute("ALTER TABLE agents ADD COLUMN webhook_secret TEXT")
        logger.info("Added webhook_secret column to agents")
    conn.commit()
    conn.close()


# ── Ensure orchestrator agent exists ─────────────────────────────────────────

def _ensure_orchestrator_agent(db: Session) -> None:
    agent = db.get(Agent, ORCHESTRATOR_ID)
    if agent:
        agent.name = ORCHESTRATOR_NAME
        agent.avatar = ORCHESTRATOR_AVATAR
        agent.role = ORCHESTRATOR_ROLE
        agent.status = "Idle"
        agent.last_active = datetime.utcnow().isoformat()
        db.add(agent)
        return
    db.add(Agent(
        id=ORCHESTRATOR_ID,
        name=ORCHESTRATOR_NAME,
        avatar=ORCHESTRATOR_AVATAR,
        role=ORCHESTRATOR_ROLE,
        model=ORCHESTRATOR_MODEL or "heuristic",
        provider="relay-internal",
        status="Idle",
        last_active=datetime.utcnow().isoformat(),
    ))


# ── Agent capability matching ────────────────────────────────────────────────

# Role → capability heuristics (when capabilities field is empty)
ROLE_CAPABILITIES: dict[str, list[str]] = {
    "coding": ["coding", "implementation", "debugging", "review"],
    "design": ["design", "ui", "ux", "frontend", "styling"],
    "orchestrator": ["planning", "coordination", "decomposition"],
    "worker": ["implementation", "general"],
    "agent": ["implementation", "general"],
    "reviewer": ["review", "qa", "testing"],
}

CAPABILITY_KEYWORDS: dict[str, list[str]] = {
    "coding": ["code", "implement", "build", "develop", "api", "backend", "function", "class", "module", "fix", "debug", "refactor"],
    "design": ["design", "ui", "ux", "frontend", "style", "layout", "component", "page", "mockup", "prototype"],
    "review": ["review", "test", "qa", "validate", "check", "audit", "verify"],
    "planning": ["plan", "architect", "design system", "spec", "define", "document"],
    "general": [],  # fallback
}


def _agent_capabilities(agent: Agent) -> list[str]:
    """Return capability list from explicit field or role heuristics."""
    if agent.capabilities and agent.capabilities.strip():
        return [c.strip() for c in agent.capabilities.split(",") if c.strip()]
    role_lower = (agent.role or "").lower()
    for role_key, caps in ROLE_CAPABILITIES.items():
        if role_key in role_lower:
            return caps
    return ["general"]


def _pick_agent(task_title: str, task_desc: str, agents: list[Agent], exclude: set[str] = None) -> Optional[Agent]:
    """Pick the best agent for a task based on capability heuristics."""
    exclude = exclude or set()
    text = f"{task_title} {task_desc}".lower()
    best: Optional[Agent] = None
    best_score = -1
    for agent in agents:
        if agent.id in exclude:
            continue
        if agent.id == ORCHESTRATOR_ID:
            continue
        caps = _agent_capabilities(agent)
        score = 0
        for cap, keywords in CAPABILITY_KEYWORDS.items():
            if cap in caps:
                score += sum(1 for kw in keywords if kw in text)
        # Bonus for being Idle
        if agent.status == "Idle":
            score += 1
        if score > best_score:
            best_score = score
            best = agent
    # If no match, pick first non-excluded non-orchestrator agent
    if not best:
        for agent in agents:
            if agent.id not in exclude and agent.id != ORCHESTRATOR_ID:
                best = agent
                break
    # If still no match (all excluded), allow reuse of first non-orchestrator agent
    if not best:
        for agent in agents:
            if agent.id != ORCHESTRATOR_ID:
                best = agent
                break
    return best


# ── Deterministic heuristic planner ──────────────────────────────────────────

def _heuristic_plan(project: Project, agents: list[Agent]) -> list[dict]:
    """
    Deterministic task decomposition when no LLM is available.
    Splits project description by paragraphs/sections into tasks.
    """
    desc = project.description.strip()
    if not desc:
        return []

    # Try splitting by numbered sections (1. ..., 2. ...) or double newlines
    sections = re.split(r'\n\s*\n|\n(?=\d+\.\s)', desc)
    sections = [s.strip() for s in sections if s.strip()]

    if len(sections) <= 1:
        # Single block — decompose by sentences into 2-4 tasks
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', desc) if s.strip()]
        if len(sentences) <= 2:
            sections = [desc]
        else:
            # Group into ~3 chunks
            chunk_size = max(1, len(sentences) // 3)
            sections = []
            for i in range(0, len(sentences), chunk_size):
                sections.append(" ".join(sentences[i:i + chunk_size]))

    tasks = []
    used_agents: set[str] = set()
    for i, section in enumerate(sections):
        # Truncate to 500 words
        words = section.split()
        if len(words) > MAX_DESCRIPTION_WORDS:
            section = " ".join(words[:MAX_DESCRIPTION_WORDS])

        # Generate title from first line or first few words
        first_line = section.split("\n")[0][:80]
        title = re.sub(r'^\d+[\.\)]\s*', '', first_line).strip()
        if not title:
            title = f"Task {i + 1}"

        agent = _pick_agent(title, section, agents, exclude=used_agents)
        if agent:
            used_agents.add(agent.id)

        # Generate eval brief
        eval_brief = f"Complete: {title}. Acceptance: the described work is implemented and functional."

        # Due date: stagger 1-3 days out
        due = (datetime.utcnow() + timedelta(days=i + 1)).strftime("%Y-%m-%d")

        tasks.append({
            "title": title,
            "description": section,
            "assignee_id": agent.id if agent else "",
            "eval_brief": eval_brief,
            "priority": "P2",
            "due_date": due,
            "depends_on": "",
        })

    # Add sequencing: each task depends on previous (lightweight chain)
    for i in range(1, len(tasks)):
        tasks[i]["depends_on"] = ""  # Will be filled after task creation with IDs

    return tasks


# ── LLM-based planner ────────────────────────────────────────────────────────

def _llm_plan(project: Project, agents: list[Agent], meta: dict) -> Optional[list[dict]]:
    """Use an LLM to decompose the project. Returns None on failure."""
    if not ORCHESTRATOR_MODEL or not ORCHESTRATOR_API_KEY:
        return None

    agent_descriptions = []
    for a in agents:
        if a.id == ORCHESTRATOR_ID:
            continue
        caps = _agent_capabilities(a)
        agent_descriptions.append(f"- id={a.id} name={a.name} role={a.role} capabilities={', '.join(caps)} status={a.status}")

    prompt = f"""You are the Relay orchestrator. Decompose this project into concrete, actionable tasks.

PROJECT: {project.name}
DESCRIPTION: {project.description}

AVAILABLE AGENTS:
{chr(10).join(agent_descriptions)}

RULES:
- Each task description must be ≤ {MAX_DESCRIPTION_WORDS} words
- Each task has exactly one assignee (from available agents above)
- Each task must have an eval_brief (acceptance criteria)
- Set priority P0-P3 and a due_date (YYYY-MM-DD)
- If tasks have dependencies, list them by title reference
- Be specific and actionable — no vague tasks

Respond with ONLY a JSON array:
[
  {{
    "title": "...",
    "description": "...",
    "assignee_id": "...",
    "eval_brief": "...",
    "priority": "P2",
    "due_date": "YYYY-MM-DD",
    "depends_on_titles": ["title of prerequisite task"]
  }}
]"""

    try:
        import urllib.request
        import urllib.error

        # Determine API base from model prefix
        model = ORCHESTRATOR_MODEL
        api_base = ORCHESTRATOR_API_BASE
        if not api_base:
            if model.startswith("openai"):
                api_base = "https://api.openai.com/v1"
            elif model.startswith("anthropic"):
                api_base = "https://api.anthropic.com/v1"
            else:
                api_base = "https://openrouter.ai/api/v1"

        # Build request based on provider
        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ORCHESTRATOR_API_KEY}",
        }
        if model.startswith("anthropic"):
            headers["x-api-key"] = ORCHESTRATOR_API_KEY
            headers["anthropic-version"] = "2023-06-01"
            url = f"{api_base.rstrip('/')}/messages"
            body = json.dumps({
                "model": model.split("/", 1)[-1] if "/" in model else model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }).encode()
        else:
            body = json.dumps({
                "model": model.split("/", 1)[-1] if "/" in model else model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.3,
            }).encode()

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        # Extract content
        if model.startswith("anthropic"):
            text = result.get("content", [{}])[0].get("text", "")
        else:
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse JSON from response
        # Try to find JSON array in response
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            logger.warning("LLM response did not contain JSON array")
            return None

        items = json.loads(match.group())
        tasks = []
        for item in items:
            desc = item.get("description", "")
            # Enforce 500-word limit
            words = desc.split()
            if len(words) > MAX_DESCRIPTION_WORDS:
                desc = " ".join(words[:MAX_DESCRIPTION_WORDS])
            tasks.append({
                "title": item.get("title", "Untitled")[:200],
                "description": desc,
                "assignee_id": item.get("assignee_id", ""),
                "eval_brief": item.get("eval_brief", ""),
                "priority": item.get("priority", "P2"),
                "due_date": item.get("due_date", ""),
                "depends_on_titles": item.get("depends_on_titles", []),
            })
        return tasks

    except Exception as exc:
        logger.warning("LLM planning failed: %s", exc)
        return None


# ── Core orchestration logic ─────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _add_comment(db: Session, task_id: int, content: str) -> None:
    db.add(Comment(
        task_id=task_id,
        author_id=ORCHESTRATOR_ID,
        author_type="agent",
        content=content,
    ))


def _fire_webhook_if_configured(db: Session, task: Task, event: str) -> None:
    """Fire webhook to assignee if configured."""
    agent = db.query(Agent).filter(Agent.id == task.assignee_id).first()
    if agent and agent.webhook_url and agent.webhook_secret:
        from .main import build_task_webhook_payload
        payload = build_task_webhook_payload(event, task, db)
        fire(agent.webhook_url, agent.webhook_secret, payload)


def _resolve_depends_on_titles(plan_items: list[dict], created_tasks: list[Task]) -> str:
    """Fill depends_on from depends_on_titles by looking up created task IDs."""
    title_to_id: dict[str, int] = {}
    for t in created_tasks:
        title_to_id[t.title.lower()] = t.id

    # Update depends_on for the last task in the list if it has deps
    for item in plan_items:
        dep_titles = item.get("depends_on_titles", [])
        if dep_titles:
            dep_ids = []
            for dt in dep_titles:
                tid = title_to_id.get(dt.lower())
                if tid:
                    dep_ids.append(str(tid))
            if dep_ids:
                return ",".join(dep_ids)
    return ""


def orchestrate_project(project: Project, kickoff_task: Task, db: Session) -> bool:
    """
    Process one orchestration kickoff. Returns True on success.
    On success: project → Active, kickoff task → Done.
    On failure: project → Failed, kickoff task → Failed.
    """
    # ── Spec quality gate ────────────────────────────────────────────────
    desc = project.description.strip()
    word_count = len(desc.split()) if desc else 0
    if word_count < MIN_BRIEF_WORDS:
        msg = f"Project brief is too vague ({word_count} words, minimum {MIN_BRIEF_WORDS}). Add more detail and retry."
        _add_comment(db, kickoff_task.id, msg)
        kickoff_task.result_description = msg
        kickoff_task.judgement = "Rejected"
        kickoff_task.status = "Rejected"
        kickoff_task.updated_at = _now_iso()
        project.status = "Failed"
        project.updated_at = _now_iso()
        db.add_all([kickoff_task, project])
        db.commit()
        return False

    # ── Gather context ───────────────────────────────────────────────────
    agents = db.query(Agent).order_by(Agent.name.asc()).all()
    meta = {
        "agents": [{"id": a.id, "role": a.role, "capabilities": _agent_capabilities(a)} for a in agents],
    }

    # ── Plan ─────────────────────────────────────────────────────────────
    plan = _llm_plan(project, agents, meta)
    if plan is None:
        logger.info("LLM planning unavailable or failed, using heuristic planner for project %d", project.id)
        plan = _heuristic_plan(project, agents)

    if not plan:
        msg = "Could not decompose project into tasks. Brief may be too short or unstructured."
        _add_comment(db, kickoff_task.id, msg)
        kickoff_task.result_description = msg
        kickoff_task.judgement = "Failed"
        kickoff_task.status = "Failed"
        project.status = "Failed"
        project.updated_at = _now_iso()
        kickoff_task.updated_at = _now_iso()
        db.add_all([kickoff_task, project])
        db.commit()
        return False

    # ── Validate plan: enforce assignee rule ──────────────────────────────
    valid_agent_ids = {a.id for a in agents if a.id != ORCHESTRATOR_ID}
    for item in plan:
        aid = item.get("assignee_id", "")
        if not aid or aid not in valid_agent_ids:
            # Reassign to best available agent
            agent = _pick_agent(item["title"], item.get("description", ""), agents)
            item["assignee_id"] = agent.id if agent else ""

    # ── Create tasks ─────────────────────────────────────────────────────
    created: list[Task] = []
    created_ids: list[int] = []

    for i, item in enumerate(plan):
        # Resolve depends_on from titles (for LLM plan)
        depends_on = ""
        dep_titles = item.get("depends_on_titles", [])
        if dep_titles and created:
            title_to_id = {t.title.lower(): str(t.id) for t in created}
            dep_ids = [title_to_id[dt.lower()] for dt in dep_titles if dt.lower() in title_to_id]
            depends_on = ",".join(dep_ids)

        # Heuristic plan: chain deps (sequential)
        if not depends_on and i > 0 and not dep_titles and created:
            depends_on = str(created[-1].id)

        task = Task(
            project_id=project.id,
            title=item["title"][:200],
            description=item.get("description", ""),
            assignee_id=item.get("assignee_id", ""),
            reporter_id=ORCHESTRATOR_ID,
            priority=item.get("priority", "P2"),
            status="To Do",
            eval_brief=item.get("eval_brief", ""),
            due_date=item.get("due_date", ""),
            depends_on=depends_on,
            tags="orchestrated",
        )
        db.add(task)
        db.flush()  # get task.id
        created.append(task)
        created_ids.append(task.id)

    # ── Finalize ─────────────────────────────────────────────────────────
    summary = f"Orchestrated into {len(created)} tasks: " + ", ".join(
        f"#{t.id} {t.title}" for t in created
    )
    _add_comment(db, kickoff_task.id, summary)
    kickoff_task.result_description = summary
    kickoff_task.judgement = "Done"
    kickoff_task.status = "Done"
    kickoff_task.updated_at = _now_iso()

    project.status = "Active"
    project.updated_at = _now_iso()
    db.add_all([kickoff_task, project])

    # Fire webhooks for all created tasks
    for task in created:
        _fire_webhook_if_configured(db, task, "task.assigned")

    db.commit()
    logger.info("Project %d orchestrated: %d tasks created", project.id, len(created))
    return True


# ── Worker loop ──────────────────────────────────────────────────────────────

_running = False


def _worker() -> None:
    """Background thread: polls for orchestration kickoff tasks."""
    global _running
    _running = True
    logger.info("Orchestrator worker started (poll every %ds)", POLL_INTERVAL)

    # Ensure columns exist on first run
    _ensure_columns()

    while _running:
        try:
            db = SessionLocal()
            try:
                # Find kickoff tasks: status "To Do" with tag "orchestration-kickoff"
                # or title containing "Orchestrate" on an Orchestrating project
                kickoff_tasks = db.query(Task).filter(
                    Task.status == "To Do",
                    Task.tags.contains("orchestration-kickoff"),
                ).all()

                # Also check for projects in Orchestrating state without kickoff tag
                if not kickoff_tasks:
                    orchestrating_projects = db.query(Project).filter(
                        Project.status == "Orchestrating"
                    ).all()
                    for proj in orchestrating_projects:
                        # Check if there's already a kickoff task for this project
                        existing = db.query(Task).filter(
                            Task.project_id == proj.id,
                            Task.reporter_id == ORCHESTRATOR_ID,
                            Task.status.in_(["To Do", "In Progress"]),
                        ).first()
                        if not existing:
                            # Create kickoff task
                            kickoff = Task(
                                project_id=proj.id,
                                title=f"Orchestrate: {proj.name}",
                                description=f"Decompose project '{proj.name}' into actionable tasks.",
                                assignee_id=ORCHESTRATOR_ID,
                                reporter_id=ORCHESTRATOR_ID,
                                priority="P1",
                                status="In Progress",
                                tags="orchestration-kickoff",
                                eval_brief="Project is decomposed into assignable tasks.",
                            )
                            db.add(kickoff)
                            db.commit()
                            kickoff_tasks = [kickoff]
                            break

                for kickoff_task in kickoff_tasks:
                    if kickoff_task.status != "To Do":
                        continue

                    # Mark in-progress
                    kickoff_task.status = "In Progress"
                    kickoff_task.updated_at = _now_iso()
                    db.add(kickoff_task)
                    db.commit()

                    project = db.get(Project, kickoff_task.project_id)
                    if not project:
                        kickoff_task.status = "Failed"
                        kickoff_task.result_description = "Project not found"
                        kickoff_task.updated_at = _now_iso()
                        db.add(kickoff_task)
                        db.commit()
                        continue

                    orchestrate_project(project, kickoff_task, db)

            finally:
                db.close()
        except Exception:
            logger.exception("Orchestrator worker error")
        time.sleep(POLL_INTERVAL)


def start_orchestrator() -> None:
    """Start the orchestrator background worker if enabled."""
    enabled = os.getenv("RELAY_ORCHESTRATOR_ENABLED", "").lower() in ("1", "true", "yes")
    if not enabled:
        logger.info("Orchestrator disabled (set RELAY_ORCHESTRATOR_ENABLED=1 to enable)")
        return

    # Ensure orchestrator agent is seeded
    db = SessionLocal()
    try:
        _ensure_columns()
        _ensure_orchestrator_agent(db)
        # Seed API key for orchestrator if configured
        orch_key = os.getenv("RELAY_ORCHESTRATOR_KEY")
        if orch_key:
            from .security import hash_api_key
            from .models import ApiKey
            key_hash = hash_api_key(orch_key)
            existing = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
            if not existing:
                db.add(ApiKey(agent_id=ORCHESTRATOR_ID, key=None, key_hash=key_hash))
        db.commit()
    finally:
        db.close()

    thread = threading.Thread(target=_worker, daemon=True, name="relay-orchestrator")
    thread.start()
    logger.info("Orchestrator thread started")


def stop_orchestrator() -> None:
    """Signal the worker to stop."""
    global _running
    _running = False
