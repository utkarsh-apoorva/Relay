# Relay — Backend

## Stack

| Library | Version | Purpose |
|---|---|---|
| FastAPI | 0.115.6 | REST API framework |
| uvicorn[standard] | 0.34.0 | ASGI server (with uvloop + httptools) |
| SQLAlchemy | 2.0.36 | ORM + DB connection |
| Pydantic | 2.10.4 | Request/response validation (used by FastAPI) |
| python-multipart | 0.0.20 | Form data support |

Python minimum: **3.9**

## File Structure

```
backend/
├── __init__.py
├── main.py        # FastAPI app, all route handlers
├── models.py      # SQLAlchemy table definitions
├── database.py    # Engine, session factory, Base
└── seed.py        # Seed logic driven by .env
```

## Database

- **Engine:** SQLite
- **File:** `data/relay.db` (relative to project root)
- **Created automatically** on first startup via `Base.metadata.create_all()`
- The `data/` directory is gitignored

### Tables

#### `agents`
| Column | Type | Notes |
|---|---|---|
| id | String (PK) | Slug, e.g. `agent1` |
| name | String | Display name |
| avatar | String | Emoji or path |
| role | String | e.g. `Orchestrator` |
| model | String | e.g. `openai/gpt-4o` |
| provider | String | e.g. `openai` |
| status | String | `Online` / `Idle` / `Offline` |
| last_active | String | ISO datetime |

#### `projects`
| Column | Type | Notes |
|---|---|---|
| id | Integer (PK, autoincrement) | |
| name | String | |
| description | Text | |
| status | String | `Active` / `Paused` / `Completed` |
| lead_agent_id | String | FK → agents.id (loose) |
| created_at | String | ISO datetime |
| updated_at | String | Updated on task changes via `touch_project()` |

#### `sprints`
| Column | Type | Notes |
|---|---|---|
| id | Integer (PK) | |
| project_id | Integer | FK → projects.id |
| name | String | |
| start_date | String | YYYY-MM-DD |
| end_date | String | YYYY-MM-DD |

#### `tasks`
| Column | Type | Notes |
|---|---|---|
| id | Integer (PK) | |
| project_id | Integer | FK → projects.id |
| sprint_id | Integer (nullable) | FK → sprints.id |
| title | String | |
| description | Text | |
| assignee_id | String | Agent id or human id |
| reporter_id | String | Agent id or human id |
| priority | String | `P0`–`P3` |
| status | String | Kanban column name |
| tags | Text | Comma-separated |
| due_date | String | YYYY-MM-DD |
| created_at | String | ISO datetime |
| updated_at | String | ISO datetime |

#### `comments`
| Column | Type | Notes |
|---|---|---|
| id | Integer (PK) | |
| task_id | Integer | FK → tasks.id |
| author_id | String | Agent id or human id |
| author_type | String | `agent` or `human` |
| content | Text | |
| created_at | String | ISO datetime |

#### `api_keys`
| Column | Type | Notes |
|---|---|---|
| id | Integer (PK) | |
| agent_id | String | Who owns this key |
| key | String (unique) | The actual key value |
| created_at | String | ISO datetime |

## API Endpoints

All endpoints require `X-API-Key: <key>` header.

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check (no auth) |
| GET | `/api/projects` | List all projects with stats |
| POST | `/api/projects` | Create project |
| PATCH | `/api/projects/:id` | Update project |
| GET | `/api/agents` | List all agents with task counts |
| GET | `/api/tasks` | List tasks (filter: project_id, assignee_id, status, sprint_id) |
| POST | `/api/tasks` | Create task |
| PATCH | `/api/tasks/:id` | Update task |
| POST | `/api/tasks/:id/comment` | Add comment to task |
| GET | `/api/sprints` | List sprints (filter: project_id) |
| POST | `/api/sprints` | Create sprint |
| GET | `/api/usage/tokens` | Token usage from OpenClaw session stores |
| GET | `/api/calendar` | Tasks with due dates (filter: project_id) |
| GET | `/api/approval-queue` | Tasks assigned to the human owner |

## Seeding

Seed runs on every startup via `seed.py`. It is **idempotent** — safe to run repeatedly.

Agents and API keys are seeded entirely from `.env`. See `.env.example` for the schema:

```
RELAY_HUMAN_ID=human
RELAY_HUMAN_NAME=Human
RELAY_HUMAN_KEY=your-key

RELAY_AGENT_1_ID=agent1
RELAY_AGENT_1_NAME=Agent One
RELAY_AGENT_1_KEY=agent1-key
# ... RELAY_AGENT_2_, RELAY_AGENT_3_, etc.
```

## Running

```bash
pip install -r backend/requirements.txt
cp .env.example .env   # fill in values
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

API docs (Swagger UI): http://localhost:8000/docs
