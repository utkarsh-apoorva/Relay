---
name: relay-poller
description: >
  Relay task poller for OpenClaw agents. Periodically polls the Relay API for new
  tasks assigned to each agent and pushes notifications to their OpenClaw sessions.
  Use when: Relay tasks need to reach OpenClaw agents automatically, or when an
  agent needs to be notified of new work without manually checking Relay.
metadata:
  { "openclaw": { "emoji": "🔔" } }
---

# Relay Poller Skill

Polls the [Relay](https://github.com/utkarsh-apoorva/Relay) API for new tasks assigned to each agent and pushes notifications to their OpenClaw sessions via the gateway RPC.

## How It Works

```
LaunchAgent (macOS) → poll.py → Relay API → OpenClaw Gateway RPC → Agent Session
```

The poller runs as a `launchd` LaunchAgent on the Mac mini. It:
1. Loads agent configs from the environment
2. Polls `GET /api/tasks?assignee_id=<agent-id>` for each agent
3. Tracks seen task IDs in `~/.openclaw/relay-poller-state.json`
4. Pushes new tasks to the agent's OpenClaw session via `sessions.send` RPC

## Prerequisites

- Python 3.9+
- `requests` library (`pip install requests`)
- OpenClaw gateway running on the Mac mini
- Relay backend accessible (local or production URL)

## Setup

### 1. Install dependencies

```bash
pip install requests
```

### 2. Create the environment config file

Create `~/.openclaw/relay-poller.env` (never commit this):

```bash
# ── Relay ──────────────────────────────────────────────
RELAY_BASE_URL=https://relay-production-c472.up.railway.app
# RELAY_BASE_URL=http://127.0.0.1:8000   # for local dev

# Agent entries — JSON array of {id, name, api_key}
# Get API keys from your Relay .env or the OpenClaw shared TOOLS.md
RELAY_AGENTS='[
  {"id": "linus",  "name": "Linus",  "api_key": "linus-key"},
  {"id": "gandalf","name": "Gandalf","api_key": "gandalf-key"},
  {"id": "thanos", "name": "Thanos", "api_key": "thanos-key"}
]'

# ── OpenClaw Gateway ───────────────────────────────────
# Gateway token from ~/.openclaw/openclaw.json → gateway.auth.token
GATEWAY_URL=http://127.0.0.1:18789
GATEWAY_TOKEN=your-gateway-token-here

# ── Poller ──────────────────────────────────────────────
POLL_INTERVAL=300   # seconds between polls (default: 300 = 5 min)
STATE_FILE=~/.openclaw/relay-poller-state.json
```

### 3. Install the LaunchAgent

Copy the plist to LaunchAgents and load it:

```bash
# Edit poller/com.relay.poller.plist and set the path to your poll.py
cp poller/com.relay.poller.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.relay.poller.plist
```

Or run manually (no daemon):
```bash
source ~/.openclaw/relay-poller.env
python3 ~/Developer/Code/Relay/poller/poll.py --daemon --interval 300
```

### 4. Verify

```bash
# One-shot poll to check for errors
source ~/.openclaw/relay-poller.env
python3 ~/Developer/Code/Relay/poller/poll.py
```

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `RELAY_BASE_URL` | Yes | `http://127.0.0.1:8000` | Relay API base URL |
| `RELAY_AGENTS` | Yes | `[]` | JSON array of agent configs |
| `GATEWAY_URL` | Yes | `http://127.0.0.1:18789` | OpenClaw gateway URL |
| `GATEWAY_TOKEN` | Yes | — | Gateway auth token |
| `POLL_INTERVAL` | No | `300` | Seconds between polls |
| `STATE_FILE` | No | `~/.openclaw/relay-poller-state.json` | Persisted task IDs |

## Skills that use this

- `relay-tasks` — work with Relay tasks directly via the API
- `openclaw-integration` — full OpenClaw ↔ Relay integration guide
