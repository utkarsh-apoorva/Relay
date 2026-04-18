# Relay

**An Orchestration Framework for AI Agents.**

Self-hosted project management and coordination tool purpose-built for human–AI team collaboration. Agents and humans are first-class citizens.

## OpenClaw Integration

Agents run as [OpenClaw](https://github.com/openclaw/openclaw) sessions and receive work via the Relay poller.

| Resource | Description |
|---|---|
| [openclaw-integration/SKILL.md](openclaw-integration/SKILL.md) | Full integration guide: API auth, endpoints, polling |
| [openclaw-integration/AGENTS.md](openclaw-integration/AGENTS.md) | Per-agent configuration examples |
| [poller/SKILL.md](poller/SKILL.md) | OpenClaw skill for the Relay task poller |
| [poller/README.md](poller/README.md) | Poller setup (LaunchAgent on macOS) |

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

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # fill in RELAY_AGENT_*_KEY values
python3 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### Poller (Mac mini only)

```bash
# Install dependency
pip install requests

# Run one-shot poll
source ~/.openclaw/relay-poller.env
python3 poller/poll.py

# Run as daemon
python3 poller/poll.py --daemon --interval 60
```

### Seeding Demo Data

```bash
cd backend
python3 seed.py   # creates demo projects, agents, and tasks
```

## Deployment

### Railway (Production)

The backend runs on Railway with ephemeral deployments.

**Required environment variables** (set in Railway dashboard → Variables):

```bash
# Runtime
RELAY_ENV=production

# CORS
RELAY_CORS_ORIGINS=https://your-frontend-domain.com

# Human owner
RELAY_HUMAN_ID=utkarsh
RELAY_HUMAN_KEY=your-human-key

# Agents — add as many as needed
RELAY_AGENT_1_ID=linus
RELAY_AGENT_1_KEY=your-linus-key
RELAY_AGENT_2_ID=gandalf
RELAY_AGENT_2_KEY=your-gandalf-key
RELAY_AGENT_3_ID=thanos
RELAY_AGENT_3_KEY=your-thanos-key
RELAY_AGENT_4_ID=ive
RELAY_AGENT_4_KEY=your-ive-key
```

**Rate limiting:**
```bash
RELAY_RATE_LIMIT_REQUESTS=120
RELAY_RATE_LIMIT_WINDOW_SECONDS=60
RELAY_MAX_BODY_BYTES=1048576
```

**Railway CLI:**
```bash
railway login
railway init
railway up
railway open   # open deployed URL
```

**Railway `railway.toml`:**
```toml
[railway]
template = "python"
```

### Important Security Notes

- **Never commit `.env`.** The repo's `.gitignore` excludes it.
- Use `.env.example` (committed) with placeholder values for documentation.
- API keys are set in Railway Variables, not in code.
- `RELAY_ENV=production` disables FastAPI docs (`/docs`, `/redoc`) in production.

## Configuration

Key `.env` / Railway Variables:

| Variable | Description |
|---|---|
| `RELAY_ENV` | `development` or `production` |
| `RELAY_CORS_ORIGINS` | Comma-separated allowed origins |
| `RELAY_HUMAN_ID` | ID for the human owner (approval queue) |
| `RELAY_HUMAN_KEY` | API key for the human |
| `RELAY_AGENT_N_ID` | ID for agent N |
| `RELAY_AGENT_N_KEY` | API key for agent N |
| `RELAY_RATE_LIMIT_*` | Abuse limiting |
| `RELAY_MAX_BODY_BYTES` | Max request body size |

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
