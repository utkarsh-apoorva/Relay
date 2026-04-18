---
name: relay-openclaw
description: >
  Integrate Relay with OpenClaw agents. Covers API authentication, webhook setup,
  the task-polling skill, and how agents should interact with the Relay API.
  Use when: setting up a new OpenClaw agent to work with Relay, or when you need
  to understand the full Relay ↔ OpenClaw integration architecture.
metadata:
  { "openclaw": { "emoji": "🔗" } }
---

# Relay ↔ OpenClaw Integration

## Overview

Relay is the project management backend. OpenClaw agents are workers that pick up tasks from Relay. This integration defines how agents authenticate, receive work, and update task state.

```
Human (Gandalf orchestrator)
    └── Relay (project management, task assignment)
            └── OpenClaw agents (workers — Linus, Thanos, Ive, etc.)
                    └── relay-poller (LaunchAgent → pushes new tasks to agent sessions)
```

## Agent API Authentication

Every Relay API call requires the `X-API-Key` header:

```bash
curl https://relay-production-c472.up.railway.app/api/tasks \
  -H "X-API-Key: your-agent-api-key"
```

API keys are configured per-agent in the Relay `.env`:

```bash
RELAY_AGENT_1_ID=linus
RELAY_AGENT_1_KEY=your-linus-key
RELAY_AGENT_2_ID=gandalf
RELAY_AGENT_2_KEY=your-gandalf-key
```

## Key Endpoints for Agents

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/tasks?assignee_id=<id>` | Tasks assigned to you |
| `PATCH` | `/api/tasks/:id` | Update task status |
| `POST` | `/api/tasks` | Create a task |
| `POST` | `/api/tasks/:id/comment` | Add a comment |
| `GET` | `/api/projects` | List projects |
| `GET` | `/api/agents` | List all agents + their task counts |
| `GET` | `/api/approval-queue` | Tasks assigned to human owner |

### Example: Fetch your tasks (as Linus)

```bash
curl https://relay-production-c472.up.railway.app/api/tasks?assignee_id=linus \
  -H "X-API-Key: your-linus-key"
```

Response:
```json
[
  {
    "id": 42,
    "title": "Fix auth bug",
    "description": "...",
    "status": "In Progress",
    "priority": "P1",
    "project_name": "Relay Backend",
    "due_date": "2026-04-20"
  }
]
```

### Example: Update a task status

```bash
curl -X PATCH https://relay-production-c472.up.railway.app/api/tasks/42 \
  -H "X-API-Key: your-linus-key" \
  -H "Content-Type: application/json" \
  -d '{"status": "Done"}'
```

## Task Lifecycle

```
Backlog → To Do → In Progress → In Review → Done
                ↘ Rejected
```

Agents should:
1. Pick up `To Do` tasks assigned to them
2. Move to `In Progress` when starting work
3. Move to `In Review` when done (human may need to approve)
4. Human moves to `Done` or rejects

## Webhook Setup (Optional)

Agents can register a webhook to be notified when their tasks change:

```bash
curl -X POST https://relay-production-c472.up.railway.app/api/agents/linus/webhook \
  -H "X-API-Key: your-linus-key" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://your-webhook-url.example.com/hook/linus"}'
```

Note: Railway's ephemeral IPs make push webhooks unreliable. Use the [relay-poller](../poller/SKILL.md) instead.

## Poller Architecture

Instead of push webhooks, a LaunchAgent poller runs on the Mac mini:

1. Polls `GET /api/tasks?assignee_id=<id>` every N minutes
2. Tracks seen task IDs in `~/.openclaw/relay-poller-state.json`
3. Pushes new tasks to agent sessions via OpenClaw `sessions.send` RPC

See [poller/SKILL.md](../poller/SKILL.md) for full setup.

## Production URL

- **Relay API:** `https://relay-production-c472.up.railway.app`
- **API docs:** `https://relay-production-c472.up.railway.app/docs`

## Environment Variables

These live in each agent's environment or in the poller's `~/.openclaw/relay-poller.env`:

| Variable | Description |
|---|---|
| `RELAY_BASE_URL` | Relay API base URL |
| `RELAY_AGENT_<N>_ID` | Agent ID (e.g., `linus`) |
| `RELAY_AGENT_<N>_KEY` | Agent's API key |

## Security Rules

- **Never commit `.env` files.** Use `.env.example` with placeholder values.
- The poller config (`relay-poller.env`) is gitignored on the Mac mini.
- API keys are rotated in Railway environment variables, not in code.
- Agents should only read/write tasks assigned to them (Relay enforces this via `api_owner`).
