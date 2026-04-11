# AgentOS

Multi-agent project management & coordination tool. Self-hosted, dark UI, built for human-AI team coordination.

## Quick Start

```bash
# Backend
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Default API Keys

| Agent    | Key            |
|----------|----------------|
| Utkarsh  | `utkarsh-key`  |
| Gandalf  | `gandalf-key`  |
| Ive      | `ive-key`      |
| Linus    | `linus-key`    |
| Thanos   | `thanos-key`   |

## Features

- **Kanban Board** — drag-and-drop task management across 5 columns
- **Project Master List** — overview with status, progress, lead agent
- **Approval Queue** — tasks assigned to Utkarsh with approve/reject/reassign
- **Calendar View** — read-only view of tasks with due dates
- **Agent Profiles** — per-agent cards with model, status, assigned tasks
- **Token Usage** — reads from OpenClaw session stores, per-agent cost breakdown
- **Sprint Management** — create and filter by sprint within a project
- **REST API** — full CRUD for tasks, projects, sprints, comments

## Tech Stack

- **Backend:** Python 3.9+, FastAPI, SQLAlchemy, SQLite
- **Frontend:** React 18, Vite, @hello-pangea/dnd, Tailwind-free dark CSS
