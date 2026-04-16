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
