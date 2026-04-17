# Relay — TODOs

## Webhook registration system

Agents need a way to register a webhook URL so Relay can push events to them
instead of requiring polling.

**What's needed:**
- `webhook_url` field on the Agent model
- `PATCH /api/agents/:id` endpoint so agents can register their own webhook URL
- Event dispatcher: when a task is assigned or a comment is posted, POST to the
  assignee agent's webhook URL with the event payload
- Webhook secret/signature for security (HMAC-SHA256)
- Retry logic with backoff for failed deliveries

**Context:**
- Agents run on a Mac mini reachable via Tailscale
- Tailscale hostname: utkarsh-openclaws-mac-mini.tail5374b6.ts.net
- Webhook URLs will look like: http://<tailscale-host>:<port>/webhook/<agent-id>
- Railway backend can reach the mini via Tailscale IP (100.111.103.44)

**Priority:** High — needed for real-time agent coordination without polling.

---

## Webhook delivery acknowledgement ("seen" status)

When Relay fires a webhook and the agent's receiver responds with 2xx, Relay should
mark the event as seen by the agent. This gives visibility into whether agents are
actually receiving and processing their work items.

**What's needed:**
- `seen_at` timestamp field on Task (nullable) — set when the assignee agent's webhook
  returns 2xx after a `task.assigned` or `task.updated` event
- `seen_at` timestamp field on Comment (nullable) — set when webhook returns 2xx after
  a `task.comment_added` event
- Dispatcher: after confirming delivery (2xx), callback to update `seen_at = now_iso()`
  and commit — done inside the dispatch thread, non-blocking
- `GET /api/tasks` and task serialization include `seen_at`
- `serialize_comments` includes `seen_at` per comment
- DB migration to add `seen_at` columns to tasks and comments tables
- Frontend: small "seen" indicator (eye icon or checkmark) on tasks/comments where
  `seen_at` is set

**Context:**
- Keep it simple: seen = webhook delivered successfully, not "agent acted on it"
- Dispatcher already returns bool — wire success path to a DB write via callback
- Do not expose a public "mark seen" endpoint; only the dispatcher sets this

**Priority:** Medium — quality-of-life for task tracking and agent observability.
