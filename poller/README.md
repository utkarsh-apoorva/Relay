# Relay Poller

Polls the Relay API for new tasks assigned to each agent and pushes notifications to OpenClaw sessions.

## Files

```
poller/
├── poll.py              # Main polling script (Python 3)
├── SKILL.md             # OpenClaw skill descriptor
├── README.md            # This file
└── com.relay.poller.plist  # macOS LaunchAgent plist
```

## Quick Start

### 1. Install Python dependency

```bash
pip install requests
```

### 2. Create the poller env file

Create `~/.openclaw/relay-poller.env` (gitignored — never commit secrets):

```bash
# ── Relay ──────────────────────────────────────────────
RELAY_BASE_URL=https://relay-production-c472.up.railway.app
RELAY_AGENTS='[
  {"id": "linus",  "name": "Linus",  "api_key": "RELAY_AGENT_1_KEY"},
  {"id": "gandalf","name": "Gandalf","api_key": "RELAY_AGENT_2_KEY"},
  {"id": "thanos", "name": "Thanos", "api_key": "RELAY_AGENT_3_KEY"}
]'

# ── OpenClaw Gateway ───────────────────────────────────
# Get the token from ~/.openclaw/openclaw.json → gateway.auth.token
GATEWAY_URL=http://127.0.0.1:18789
GATEWAY_TOKEN=your-gateway-token-here

# ── Poller ──────────────────────────────────────────────
POLL_INTERVAL=300   # seconds (5 minutes default)
STATE_FILE=~/.openclaw/relay-poller-state.json
```

### 3. Load as LaunchAgent

```bash
# Copy the plist
cp com.relay.poller.plist ~/Library/LaunchAgents/

# Load it (starts polling immediately)
launchctl load ~/Library/LaunchAgents/com.relay.poller.plist

# Check logs
tail -f /tmp/relay-poller.log
```

### 4. Run manually (no daemon)

```bash
source ~/.openclaw/relay-poller.env
python3 poll.py
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Mac mini (LaunchAgent)                                       │
│                                                              │
│  poll.py                                                     │
│    ├── Reads RELAY_AGENTS from env                           │
│    ├── Polls GET /api/tasks?assignee_id=<id> per agent       │
│    ├── Tracks seen task IDs in state.json                    │
│    └── POSTs new tasks → OpenClaw Gateway RPC                │
│                                                              │
│  OpenClaw Gateway (ws://127.0.0.1:18789)                     │
│    └── sessions.send → agent Telegram session               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Railway (Relay production)                                  │
│                                                              │
│  FastAPI + SQLite                                            │
│  └── /api/tasks?assignee_id=<id>  (API-key auth)            │
└──────────────────────────────────────────────────────────────┘
```

## Why Polling?

Railway uses ephemeral containers with rotating IPs — push webhooks break on every deploy. Polling is reliable, self-healing, and keeps agents stateless.

## Troubleshooting

**No tasks pushed to agents:**
- Check `tail -f /tmp/relay-poller.error.log`
- Verify `GATEWAY_TOKEN` matches `~/.openclaw/openclaw.json` → `gateway.auth.token`
- Verify `RELAY_AGENTS` API keys are correct

**Python import errors:**
```bash
pip install requests
```

**LaunchAgent won't start:**
```bash
launchctl error com.relay.poller
# Check the plist path in ProgramArguments matches actual poll.py location
```

**Gateway unreachable:**
- Ensure OpenClaw gateway is running: `openclaw gateway status`
- Gateway URL should be `http://127.0.0.1:18789` for local access
