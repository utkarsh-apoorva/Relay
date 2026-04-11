# PRD: AgentOS — Multi-Agent Project Management & Coordination Tool

**Author:** Gandalf  
**Date:** 2026-04-12  
**Status:** Draft → Linus execution  
**Deployment:** Local (Mac Mini M4) → GitHub → Cloud

---

## 1. Problem

Four AI agents (and growing) need to coordinate work, assign tasks, track progress, and report to a human CEO. Currently there's no shared system — tasks live in chat threads, context gets lost, and there's no visibility into who's doing what.

## 2. Vision

A self-hosted project management tool purpose-built for human-AI team coordination. Not a generic Kanban tool retrofitted for agents — a system where agents are first-class citizens alongside humans.

## 3. Architecture Decisions (Linus to validate/override)

- **Backend:** Python (FastAPI) — fast to build, agents can interact via HTTP
- **Database:** SQLite (local) — simple, no infra, portable to PostgreSQL later
- **Frontend:** React + Tailwind (dark theme) — clean, fast, lightweight
- **API:** REST + WebSocket for live updates
- **Agent integration:** REST API + future MCP bridge
- **Auth:** Single-user (Utkarsh) + agent API keys for now

## 4. Core Features

### 4.1 Kanban Board (Per Project)

**Columns (default, configurable):**
- Backlog → To Do → In Progress → In Review → Done

**Card fields:**
- Title, description (markdown)
- Assignee (agent name or "Utkarsh")
- Reporter (who created it)
- Priority (P0–P3)
- Status (column)
- Sprint (optional)
- Tags
- Due date
- Created/Updated timestamps
- Comments thread (agents and human can comment)

**Behaviors:**
- Cards can be created via API or UI
- Drag-and-drop between columns
- Agent-created cards are tagged with the agent's name automatically
- Cards assigned to "Utkarsh" appear in an approval queue

### 4.2 Approval Queue

- Tasks assigned to Utkarsh appear in a dedicated "Awaiting Approval" view
- Utkarsh can: Approve (moves to To Do), Modify (edit and approve), Reject (with comment), Reassign (to another agent)
- Notifications: not needed for MVP (check dashboard manually)

### 4.3 Master Project List

- A single page listing all projects
- Fields: Project name, status (Active/Paused/Completed), sprint count, task count, % done, lead agent, last updated
- Click project → opens that project's Kanban board
- Ability to create/archive projects

### 4.4 Calendar View

- Shows tasks with due dates on a calendar
- Toggle: all projects / single project
- Click date → shows tasks due that day
- MVP: read-only view, no drag-to-reschedule

### 4.5 Agent Profiles Page

- One card per agent showing:
  - Name, avatar (emoji or uploaded image), role description
  - Model name and provider (e.g., "openai/gpt-5.4-mini")
  - Status: Online / Idle / Offline
  - Current tasks count (In Progress)
  - Last active timestamp
- Click agent → shows their assigned tasks across all projects

### 4.6 Token Usage Dashboard

- Reads from OpenClaw session stores (`~/.openclaw/agents/*/sessions/sessions.json`)
- Shows per-agent and per-model:
  - Total tokens consumed
  - Estimated cost (configurable rates per model)
  - 7-day trend chart (stretch goal — table is fine for MVP)
- Auto-refreshes on page load (no live streaming needed)

### 4.7 Agent API

REST endpoints for agents to interact:

```
POST   /api/tasks              — Create a task
GET    /api/tasks              — List tasks (filter by project, assignee, status)
PATCH  /api/tasks/:id          — Update a task (status, assignee, comments)
POST   /api/tasks/:id/comment  — Add a comment
GET    /api/projects           — List projects
POST   /api/projects           — Create a project
GET    /api/agents             — List agents + status
GET    /api/usage/tokens       — Token usage data
```

Authentication via API key in header: `X-API-Key: <key>`

### 4.8 Sprint Management (Basic)

- A sprint = a named timebox attached to a project
- Fields: name, start date, end date, project ID
- Tasks can be assigned to a sprint
- Sprint view: shows only tasks in that sprint on the Kanban board
- MVP: no velocity tracking, no burndown charts

## 5. UI Design Principles

- **Dark theme** — dark gray/navy background, light text
- **Minimal** — no visual noise, generous whitespace
- **Fast** — no loading spinners for local data, instant interactions
- **Responsive enough** — primarily used on desktop, but shouldn't break on tablet

### Layout

```
┌─────────────────────────────────────────────┐
│  🦞 AgentOS        [Projects] [Agents] [Usage] │
├──────────┬──────────────────────────────────┤
│ Sidebar  │  Main Content Area               │
│          │                                  │
│ Project  │  (Kanban / Calendar / Profile)   │
│ List     │                                  │
│          │                                  │
│ Sprint   │                                  │
│ Selector │                                  │
│          │                                  │
│ Approval │                                  │
│ Queue    │                                  │
│ (count)  │                                  │
└──────────┴──────────────────────────────────┘
```

## 6. Data Model

```sql
-- Core tables
agents (id, name, avatar, role, model, provider, status, last_active)
projects (id, name, description, status, lead_agent_id, created_at, updated_at)
sprints (id, project_id, name, start_date, end_date)
tasks (id, project_id, sprint_id, title, description, assignee_id, reporter_id,
       priority, status, tags, due_date, created_at, updated_at)
comments (id, task_id, author_id, author_type, content, created_at)
api_keys (id, agent_id, key, created_at)

-- author_type: 'agent' or 'human'
-- assignee_id / reporter_id: references agents.id OR 'utkarsh'
```

## 7. File Structure (Proposed)

```
agentos/
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── models.py            # SQLAlchemy models
│   ├── routes/
│   │   ├── tasks.py
│   │   ├── projects.py
│   │   ├── agents.py
│   │   ├── usage.py
│   │   └── sprints.py
│   ├── database.py          # SQLite connection
│   └── seed.py              # Seed agents data
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── KanbanBoard.tsx
│   │   │   ├── CalendarView.tsx
│   │   │   ├── AgentProfiles.tsx
│   │   │   ├── TokenUsage.tsx
│   │   │   └── ApprovalQueue.tsx
│   │   ├── components/
│   │   │   ├── TaskCard.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── ...
│   │   └── api/
│   │       └── client.ts
│   ├── tailwind.config.js
│   └── package.json
├── data/
│   └── agentos.db            # SQLite database
└── README.md
```

## 8. Seed Data

Pre-seed these agents:
- Gandalf (🧙) — Orchestrator, zai/glm-5.1
- Ive (🎨) — Design & Product, anthropic/claude-sonnet-4-6
- Linus (🐧) — Coding, openai/gpt-5.4-mini
- Thanos (🟣) — Experimentation, zai/glm-5.1

## 9. Non-Goals (V1)

- Multi-user auth (single human + agents only)
- Real-time WebSocket streaming (polling is fine)
- Email/Slack notifications
- Mobile app
- External integrations (Jira, GitHub, etc.)
- Agent-to-agent chat (they coordinate via tasks)

## 10. Success Criteria

- [ ] Can create a project and add tasks via UI
- [ ] Can create tasks via API (agent integration)
- [ ] Kanban board with drag-and-drop works
- [ ] Approval queue shows tasks assigned to Utkarsh
- [ ] Agent profiles page renders with live data
- [ ] Token usage page reads from OpenClaw session stores
- [ ] Calendar view shows due dates
- [ ] Dark theme looks clean and professional
- [ ] Runs on localhost:3000 (frontend) + localhost:8000 (API)

## 11. Post-V1 Roadmap

- MCP bridge for native agent integration
- GitHub sync (issues ↔ tasks)
- Burndown charts and velocity tracking
- Agent heartbeat / health monitoring
- Deploy to cloud (Docker + fly.io or Railway)
- Mobile-responsive design
- Real-time WebSocket updates
