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

def gateway_rpc(method: str, params: dict) -> Optional[dict]:
    """
    Send a JSON-RPC request to the OpenClaw gateway WebSocket HTTP endpoint.
    Uses the gateway's HTTP /rpc route.
    """
    gw_url = GATEWAY_URL.rstrip("/")
    # Try the HTTP RPC endpoint first
    rpc_url = f"{gw_url}/rpc"
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params,
    }
    try:
        resp = requests.post(
            rpc_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {GATEWAY_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        # Fallback: try as plain request (gateway may handle differently)
        print(f"[relay-poller] gateway RPC {method} returned {resp.status_code}", file=sys.stderr)
        return None
    except requests.RequestException as e:
        print(f"[relay-poller] gateway RPC error for {method}: {e}", file=sys.stderr)
        return None


def push_to_session(session_key: str, message: str) -> bool:
    """
    Push a message to an OpenClaw agent session via sessions.send.
    Returns True on success.
    """
    result = gateway_rpc("sessions.send", {
        "sessionKey": session_key,
        "message": message,
        "role": "system",
    })
    if result and result.get("result"):
        return True
    print(f"[relay-poller] sessions.send failed for {session_key}: {result}", file=sys.stderr)
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
        # Skip Done and Rejected tasks
        if status in ("Done", "Rejected"):
            if task_id in seen:
                seen.discard(task_id)
            continue
        if task_id in seen:
            continue

        # New / unseen task
        seen.add(task_id)
        new_count += 1

        summary = task_summary(task)
        msg = (
            f"📋 New Relay task for {agent_name}:\n\n"
            f"{summary}\n\n"
            f"Task ID: {task_id}\n"
            f"View in Relay: {RELAY_BASE_URL}"
        )

        # Map agent_id to the correct OpenClaw session key for Telegram direct
        # Session key format: agent:{agent_id}:telegram:direct:{chat_id}
        # chat_id is the human's Telegram ID (stored in RELAY_HUMAN_CHAT_ID)
        chat_id = os.getenv("RELAY_HUMAN_CHAT_ID", "8636971702")
        session_key = f"agent:{agent_id}:telegram:direct:{chat_id}"
        pushed = push_to_session(session_key, msg)
        if pushed:
            print(f"[relay-poller] Pushed task {task_id} to {agent_id} ({agent_name})")
        else:
            # Fallback: try without chat_id
            for alt in [
                f"agent:{agent_id}:telegram:direct",
                f"agent:{agent_id}",
            ]:
                if push_to_session(alt, msg):
                    print(f"[relay-poller] Pushed task {task_id} to {alt}")
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
