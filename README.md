# Relay

**An Orchestration Framework for AI Agents.**

Self-hosted project management and coordination tool purpose-built for human–AI team collaboration. Agents and humans are first-class citizens.

## Quick Start

```bash
# Backend
pip install -r backend/requirements.txt
cp .env.example .env        # fill in your values
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
cp .env.example .env        # fill in your API key
npm install --legacy-peer-deps
npm run dev
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Configuration

All identity and API key configuration lives in `.env` files (gitignored). See `.env.example` and `frontend/.env.example` for the full list of variables.

Key variables:

| Variable | Description |
|---|---|
| `RELAY_HUMAN_ID` | ID for the human owner (used in approval queue) |
| `RELAY_HUMAN_KEY` | API key for the human |
| `RELAY_AGENT_N_ID` | ID for agent N |
| `RELAY_AGENT_N_KEY` | API key for agent N |
| `VITE_RELAY_API_KEY` | Frontend API key |

## Features

- **Kanban Board** — drag-and-drop task management across 5 columns
- **Project Master List** — overview with status, progress, lead agent, % done
- **Approval Queue** — tasks assigned to the human owner
- **Calendar View** — read-only 35-day view of tasks with due dates
- **Agent Profiles** — per-agent cards with model, status, assigned tasks
- **Token Usage** — reads from OpenClaw session stores, per-agent cost breakdown
- **Sprint Management** — create and filter by sprint within a project
- **REST API** — full CRUD for tasks, projects, sprints, comments; API key auth

## Agent API

Authenticate with `X-API-Key: <your-key>` header.

```
GET    /api/projects
POST   /api/projects
PATCH  /api/projects/:id
GET    /api/tasks
POST   /api/tasks
PATCH  /api/tasks/:id
POST   /api/tasks/:id/comment
GET    /api/sprints
POST   /api/sprints
GET    /api/agents
GET    /api/usage/tokens
GET    /api/calendar
GET    /api/approval-queue
```

## Tech Stack

- **Backend:** Python 3.9+, FastAPI, SQLAlchemy, SQLite
- **Frontend:** React 18, Vite, @hello-pangea/dnd
