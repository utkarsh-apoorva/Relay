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
cp .env.example .env
npm install --legacy-peer-deps
npm run dev
# then enter your API key in the UI
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Configuration

Backend identity, API key, and CORS configuration lives in `.env` files (gitignored). The frontend should not bundle secrets. Enter the API key in the UI, where it is stored in session storage only.

Key variables:

| Variable | Description |
|---|---|
| `RELAY_CORS_ORIGINS` | Comma-separated allowed origins for the API |
| `RELAY_HUMAN_ID` | ID for the human owner (used in approval queue) |
| `RELAY_HUMAN_KEY` | API key for the human |
| `RELAY_AGENT_N_ID` | ID for agent N |
| `RELAY_AGENT_N_KEY` | API key for agent N |
| `RELAY_ENV` | Set to `production` to disable FastAPI docs |

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
