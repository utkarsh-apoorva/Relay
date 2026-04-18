#!/usr/bin/env python3
"""
Relay Poller — runs as a LaunchAgent, polls Relay API, pushes new tasks to OpenClaw agents.

Architecture:
  Mac mini (LaunchAgent) → polls Relay API → OpenClaw Gateway RPC → agent session

Prerequisites:
  - Python 3.9+
  - requests library
  - Config in ~/.openclaw/workspace-linus/workspace/relay-poller.env (gitignored)

Usage:
  python3 poll.py                   # one-shot
  python3 poll.py --daemon           # loop forever
  python3 poll.py --daemon --interval 120  # loop every 120 seconds
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# ── Config ────────────────────────────────────────────────────────────────────

RELAY_BASE_URL = os.getenv("RELAY_BASE_URL", "http://127.0.0.1:8000")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:18789")
GATEWAY_TOKEN = os.getenv("GATEWAY_TOKEN", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))  # seconds
STATE_FILE = Path(os.getenv("STATE_FILE", str(Path.home() / ".openclaw" / "relay-poller-state.json")))

# Map from Relay agent IDs to OpenClaw agent IDs.
# Gandalf in Relay = "main" in OpenClaw. Others are 1:1.
_RELAY_TO_OC: dict[str, str] = {}
def _parse_relay_to_oc() -> dict[str, str]:
    raw = os.getenv("RELAY_TO_OPENCLAW_MAP", "")
    if not raw:
        return {}
    m: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or "→" not in pair:
            continue
        relay_id, oc_id = pair.split("→", 1)
        m[relay_id.strip()] = oc_id.strip()
    return m

def relay_to_openclaw_id(relay_id: str) -> str:
    """Map Relay agent ID to OpenClaw agent ID. Defaults to relay_id."""
    if not _RELAY_TO_OC:
        _RELAY_TO_OC.update(_parse_relay_to_oc())
    return _RELAY_TO_OC.get(relay_id, relay_id)

# Agent config: list of dicts with id, name, api_key
# Loaded from RELAY_AGENTS env var as JSON, e.g.:
#   [{"id": "linus", "name": "Linus", "api_key": "..."}, ...]
def load_agents() -> list[dict]:
    raw = os.getenv("RELAY_AGENTS", "[]")
    try:
        return json.loads(raw)
    except Exception:
        print(f"[relay-poller] WARNING: could not parse RELAY_AGENTS JSON: {raw!r}", file=sys.stderr)
        return []


# ── State ──────────────────────────────────────────────────────────────────────

def load_state() -> dict[str, set[int]]:
    """Returns dict of agent_id → set of seen task IDs."""
    if STATE_FILE.exists():
        try:
            raw = json.loads(STATE_FILE.read_text())
            return {k: set(v) for k, v in raw.items()}
        except Exception as e:
            print(f"[relay-poller] WARNING: could not load state file: {e}", file=sys.stderr)
    return {}


def save_state(state: dict[str, set[int]]) -> None:
    """Persists agent_id → list(task IDs) to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        STATE_FILE.write_text(json.dumps({k: list(v) for k, v in state.items()}))
    except Exception as e:
        print(f"[relay-poller] WARNING: could not save state file: {e}", file=sys.stderr)


# ── Relay API ──────────────────────────────────────────────────────────────────

def fetch_agent_tasks(agent_id: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch all non-Done tasks assigned to an agent."""
    headers = {"X-API-Key": api_key}
    url = f"{RELAY_BASE_URL}/api/tasks"
    params = {"assignee_id": agent_id}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        print(f"[relay-poller] WARN: {agent_id} tasks fetch returned {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return []
    except requests.RequestException as e:
        print(f"[relay-poller] ERROR: fetching {agent_id} tasks failed: {e}", file=sys.stderr)
        return []


def task_summary(task: dict[str, Any]) -> str:
    priority = task.get("priority", "P2")
    status = task.get("status", "")
    title = task.get("title", "Untitled")
    project = task.get("project_name", "")
    due = task.get("due_date", "")
    parts = [f"[{priority}] {title}"]
    if project:
        parts.append(f"Project: {project}")
    if status and status not in ("To Do", "Backlog"):
        parts.append(f"Status: {status}")
    if due:
        parts.append(f"Due: {due}")
    return " | ".join(parts)


# ── OpenClaw Gateway RPC ───────────────────────────────────────────────────────

def gateway_invoke(tool: str, args: dict) -> Optional[dict]:
    """
    Call the OpenClaw gateway /tools/invoke endpoint.
    """
    gw_url = GATEWAY_URL.rstrip("/")
    invoke_url = f"{gw_url}/tools/invoke"
    payload = {
        "tool": tool,
        "args": args,
    }
    try:
        resp = requests.post(
            invoke_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {GATEWAY_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"[relay-poller] gateway invoke {tool} returned {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return None
    except requests.RequestException as e:
        print(f"[relay-poller] gateway invoke error for {tool}: {e}", file=sys.stderr)
        return None


def push_to_session(session_key: str, message: str) -> bool:
    """
    Spawn a fire-and-forget agent turn via sessions_spawn.
    Returns True if the spawn succeeded (agent handles it asynchronously).
    """
    # Extract agent_id from session key: agent:{agent_id}:telegram:direct:{chat_id}
    parts = session_key.split(":")
    agent_id = parts[1] if len(parts) > 1 else "unknown"

    result = gateway_invoke("sessions_spawn", {
        "runtime": "subagent",
        "agentId": agent_id,
        "mode": "run",
        "cleanup": "delete",
        "task": message,
        "lightContext": True,
    })
    if result and result.get("result"):
        return True
    print(f"[relay-poller] sessions.spawn failed for {session_key}: {result}", file=sys.stderr)
    return False


# ── Polling ───────────────────────────────────────────────────────────────────

def poll_agent(agent_id: str, agent_name: str, api_key: str, state: dict[str, set[int]]) -> None:
    """Poll one agent's tasks, notify on new tasks, update state."""
    tasks = fetch_agent_tasks(agent_id, api_key)
    if not isinstance(tasks, list):
        return

    seen = state.setdefault(agent_id, set())
    new_count = 0

    for task in tasks:
        task_id = task.get("id")
        if task_id is None:
            continue
        status = task.get("status", "")
        # Skip Done and Rejected tasks (removes stale state entries on next poll)
        if status in ("Done", "Rejected"):
            if task_id in seen:
                seen.discard(task_id)
            continue
        if task_id in seen:
            # Already notified this session — skip silently
            continue

        # New / unseen task
        new_count += 1

        summary = task_summary(task)
        msg = (
            f"📋 New Relay task for {agent_name}:\n\n"
            f"{summary}\n\n"
            f"Task ID: {task_id}\n"
            f"View in Relay: {RELAY_BASE_URL}"
        )

        # Map Relay agent_id → OpenClaw session key
        oc_id = relay_to_openclaw_id(agent_id)
        chat_id = os.getenv("RELAY_HUMAN_CHAT_ID", "8636971702")
        session_key = f"agent:{oc_id}:telegram:direct:{chat_id}"
        pushed = push_to_session(session_key, msg)
        if pushed:
            seen.add(task_id)
            print(f"[relay-poller] Pushed task {task_id} to {oc_id} ({agent_name})")
            save_state(state)  # persist immediately to avoid re-sending on next poll
        else:
            # Fallback: try without chat_id
            for alt in [
                f"agent:{oc_id}:telegram:direct",
                f"agent:{oc_id}",
            ]:
                if push_to_session(alt, msg):
                    seen.add(task_id)
                    print(f"[relay-poller] Pushed task {task_id} to {alt}")
                    save_state(state)
                    break
            else:
                print(f"[relay-poller] WARN: could not push task {task_id} to {agent_id}", file=sys.stderr)

    if new_count == 0 and tasks:
        print(f"[relay-poller] {agent_id}: {len(tasks)} tasks, no new ones")

    state[agent_id] = seen


def run_poll_once() -> None:
    """One polling cycle across all agents."""
    agents = load_agents()
    if not agents:
        print("[relay-poller] No agents configured (RELAY_AGENTS is empty)", file=sys.stderr)
        return

    print(f"[relay-poller] Polling {len(agents)} agent(s) at {datetime.now(timezone.utc).isoformat()}")
    state = load_state()

    for agent in agents:
        aid = agent.get("id", "?")
        name = agent.get("name", aid)
        key = agent.get("api_key", "")
        if not key:
            print(f"[relay-poller] Skipping {aid}: no API key", file=sys.stderr)
            continue
        poll_agent(aid, name, key, state)

    save_state(state)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Relay → OpenClaw task poller")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL,
                        help=f"Poll interval in seconds (default: {POLL_INTERVAL})")
    args = parser.parse_args()

    if args.daemon:
        print(f"[relay-poller] Daemon mode, polling every {args.interval}s")
        while True:
            run_poll_once()
            time.sleep(args.interval)
    else:
        run_poll_once()


if __name__ == "__main__":
    main()
