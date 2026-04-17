# Relay — TODOs

## Push webhooks (ABANDONED)

Railway uses ephemeral containers with rotating Tailscale IPs. Direct push from Railway to Mac mini
fails because Railway's Tailscale WireGuard tunnel can't reliably reach the tailnet.
Tailscale Serve would fix this but requires a paid plan.

**Replaced by:** Polling agent (below)

---

## Polling agent — task delivery to OpenClaw

Instead of Railway pushing webhooks (unreliable with ephemeral Railway containers), a poller
runs on the Mac mini. It polls Relay's API every N minutes, detects new tasks assigned to each
agent, and pushes them to the OpenClaw gateway via HTTP RPC.

**Architecture:**
```
Mac mini — relay-poller (Node.js, LaunchAgent)
  ├── Polls: GET /api/tasks?assignee_id=<agent-id>
  ├── Tracks seen tasks in: ~/Developer/Code/relay-poller/state.json
  └── On new task: POST to OpenClaw gateway RPC
                     → session_push → Linus/thanos/etc. receives task
```

**What's needed:**
- `relay-poller/` directory on Mac mini at `~/Developer/Code/relay-poller/`
- `index.js`: main poller with per-agent poll loops
- `state.json`: persisted set of seen task IDs (survives restarts)
- Per-agent API keys stored in `~/.env` (not in code)
- `relay-poller.plist` LaunchAgent running the poller
- OpenClaw gateway RPC: session_push endpoint to deliver task to agent session
- Config: poll interval (default 5 minutes), agent list

**Why polling over push:**
- Railway ephemeral containers = rotating Tailscale IPs = push breaks on every deploy
- Polling is reliable, self-healing, no firewall/Tailscale issues
- Agents stay stateless — they receive tasks via OpenClaw gateway, not direct HTTP

**Files to create:**
- `~/Developer/Code/relay-poller/index.js`
- `~/Developer/Code/relay-poller/.env` (API keys per agent, RELAY_BASE_URL, POLL_INTERVAL)
- `~/Developer/Code/relay-poller/state.json` (initial: `{}`)
- `~/Library/LaunchAgents/com.relay.poller.plist`
- `README.md`

**LaunchAgent plist:**
- Label: `com.relay.poller`
- ProgramArguments: `/usr/local/bin/node /Users/utkarsh-openclaw/Developer/Code/relay-poller/index.js`
- StandardOutPath/StandardErrorPath: `/tmp/relay-poller.log`
- RunAtLoad: true
- KeepAlive: true

**Files to modify in Relay:**
- `backend/main.py`: OpenClaw gateway RPC — add `POST /rpc` endpoint with `session_push` method
  - Accepts: `{ session_key, message }` — sends a message into the target agent session
  - Requires auth token (OpenClaw gateway auth token from `~/.openclaw/openclaw.json`)

**Agent API keys (known):**
| Agent | API Key |
|-------|---------|
| linus | `linus-key` |
| gandalf | `gandalf-key` |
| ive | `ive-key` |
| thanos | `thanos-key` |
| clay | `clay-key` |

**POLL_INTERVAL default:** 300 seconds (5 minutes)
**RELAY_BASE_URL:** `https://relay-production-c472.up.railway.app`

**Priority:** High — enables reliable task delivery without depending on webhook push.

---

## Webhook delivery acknowledgement ("seen" status)

When the poller successfully pushes a task to an agent via the OpenClaw gateway,
Relay should mark the task as seen by the agent.

**What's needed:**
- `seen_at` timestamp field on Task (nullable) — set when gateway confirms delivery
- PATCH endpoint on Relay to mark seen: `PATCH /api/tasks/:id/seen`
  - Body: `{ agent_id: "linus" }` — poller calls this after gateway push succeeds
- `GET /api/tasks` and task serialization include `seen_at`
- Frontend: small "seen" indicator (eye icon or checkmark) on tasks where `seen_at` is set

**Flow:**
1. Poller polls → finds new task
2. Poller POSTs to OpenClaw gateway RPC → session_push
3. Gateway responds OK
4. Poller calls `PATCH /api/tasks/:id/seen` with `{ agent_id }`
5. Relay sets `seen_at = now_iso()` on the task

**Priority:** Medium — quality-of-life for task tracking and agent observability.

---

## OpenClaw gateway RPC — session_push

The OpenClaw gateway needs a JSON-RPC or REST endpoint that the poller can call to push
a message into an agent's session.

**What's needed:**
- New endpoint: `POST /rpc` on the gateway (127.0.0.1:18789)
- Auth: requires `Authorization: Bearer <gateway-token>` header
- Method: `session_push`
- Body: `{ session_key: "agent:linus:telegram:direct:...", message: { type: "task", task: {...} } }`
- Returns: `{ ok: true }` on success, `{ error: "..." }` on failure

**Context:**
- Gateway auth token is in `~/.openclaw/openclaw.json` → `gateway.auth.token`
- Session key format: `agent:<agent-id>:telegram:direct:<user-id>` or `agent:<agent-id>:chat`
- The poller needs to know the correct session key per agent

**Priority:** High — without this, the poller has no way to deliver tasks to agents.
