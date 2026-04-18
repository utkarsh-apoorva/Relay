# Relay Agent Configurations

Example configurations for OpenClaw agents that work with Relay.

## Agent Registry (from `.env.example`)

```bash
# ── Human owner ─────────────────────────────────────────
RELAY_HUMAN_ID=utkarsh
RELAY_HUMAN_NAME=Utkarsh
RELAY_HUMAN_KEY=utkarsh-key

# ── Agent 1: Linus — Coding agent ───────────────────────
RELAY_AGENT_1_ID=linus
RELAY_AGENT_1_NAME=Linus
RELAY_AGENT_1_AVATAR=🤖
RELAY_AGENT_1_ROLE=Worker
RELAY_AGENT_1_MODEL=openai/gpt-4o
RELAY_AGENT_1_PROVIDER=openai
RELAY_AGENT_1_KEY=RELAY_AGENT_1_KEY

# ── Agent 2: Gandalf — Orchestrator ─────────────────────
RELAY_AGENT_2_ID=gandalf
RELAY_AGENT_2_NAME=Gandalf
RELAY_AGENT_2_AVATAR=🧙
RELAY_AGENT_2_ROLE=Orchestrator
RELAY_AGENT_2_MODEL=anthropic/claude-3-7-sonnet
RELAY_AGENT_2_PROVIDER=anthropic
RELAY_AGENT_2_KEY=RELAY_AGENT_2_KEY

# ── Agent 3: Thanos — Research ───────────────────────────
RELAY_AGENT_3_ID=thanos
RELAY_AGENT_3_NAME=Thanos
RELAY_AGENT_3_AVATAR=💡
RELAY_AGENT_3_ROLE=Researcher
RELAY_AGENT_3_MODEL=openai/gpt-4o
RELAY_AGENT_3_PROVIDER=openai
RELAY_AGENT_3_KEY=RELAY_AGENT_3_KEY

# ── Agent 4: Ive — Design ────────────────────────────────
RELAY_AGENT_4_ID=ive
RELAY_AGENT_4_NAME=Ive
RELAY_AGENT_4_AVATAR=🎨
RELAY_AGENT_4_ROLE=Designer
RELAY_AGENT_4_MODEL=anthropic/claude-3-5-sonnet
RELAY_AGENT_4_PROVIDER=anthropic
RELAY_AGENT_4_KEY=RELAY_AGENT_4_KEY
```

## Per-Agent Relay API Usage

### Linus (Coding)

```bash
# Fetch assigned coding tasks
curl "https://relay-production-c472.up.railway.app/api/tasks?assignee_id=linus" \
  -H "X-API-Key: linus-key"

# Update a task to Done
curl -X PATCH "https://relay-production-c472.up.railway.app/api/tasks/42" \
  -H "X-API-Key: linus-key" \
  -H "Content-Type: application/json" \
  -d '{"status": "Done"}'
```

### Gandalf (Orchestrator)

```bash
# See all tasks across all agents
curl "https://relay-production-c472.up.railway.app/api/tasks" \
  -H "X-API-Key: gandalf-key"

# See approval queue (tasks assigned to human owner)
curl "https://relay-production-c472.up.railway.app/api/approval-queue" \
  -H "X-API-Key: gandalf-key"

# Create a task for Linus
curl -X POST "https://relay-production-c472.up.railway.app/api/tasks" \
  -H "X-API-Key: gandalf-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Add OpenClaw integration docs",
    "description": "Document the Relay ↔ OpenClaw integration",
    "assignee_id": "linus",
    "priority": "P1",
    "status": "To Do"
  }'
```

### Thanos (Research)

```bash
# Fetch research tasks
curl "https://relay-production-c472.up.railway.app/api/tasks?assignee_id=thanos" \
  -H "X-API-Key: thanos-key"
```

## OpenClaw Session Key Format

The relay poller uses session keys to route task notifications to agents:

| Agent | Session Key Pattern |
|---|---|
| Linus | `agent:main:linus:telegram:direct` |
| Gandalf | `agent:main:gandalf:telegram:direct` |
| Thanos | `agent:main:thanos:telegram:direct` |
| Ive | `agent:main:ive:telegram:direct` |

The session key maps to the agent's primary Telegram-connected session in OpenClaw.

## Poller Agent Config

In `~/.openclaw/relay-poller.env`:

```bash
RELAY_AGENTS='[
  {"id": "linus",  "name": "Linus",  "api_key": "RELAY_AGENT_1_KEY"},
  {"id": "gandalf","name": "Gandalf","api_key": "RELAY_AGENT_2_KEY"},
  {"id": "thanos", "name": "Thanos", "api_key": "RELAY_AGENT_3_KEY"},
  {"id": "ive",    "name": "Ive",    "api_key": "RELAY_AGENT_4_KEY"}
]'
```

## Task Assignment Best Practices

1. **Use meaningful priorities:** P0 for urgent, P2 for normal, P3 for nice-to-have
2. **Set due dates** on tasks that have time constraints
3. **Add descriptions** with context so agents don't need to ask clarifying questions
4. **Use `In Review`** when done — human approves before `Done`
5. **Assign to `utkarsh`** for tasks requiring human decision (approval queue)
