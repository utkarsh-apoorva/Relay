# Relay — Contributing & Working on the Codebase

## Before You Start

**Read the documentation first.**

- `documentation/architecture.md` — system layout, design decisions
- `documentation/backend.md` — API, DB schema, seeding, libraries
- `documentation/frontend.md` — components, state, env vars, data flow

This is the context. Don't start coding without reading it.

## Repo Location

```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault 1.0/Code/Relay/
```

All coding work happens here. Never work from `workspace-linus` or any other copy.

## Git Workflow

```bash
cd "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault 1.0/Code/Relay"
git status
git add <files>
git commit -m "clear description of what changed"
git push origin main
```

Commit message must describe what changed, not what you did. Bad: `fix stuff`. Good: `Fix approval queue not filtering by project`.

After every code push, update the relevant documentation file and push that too.

## Environment Setup

```bash
# Backend
cp .env.example .env
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Frontend (separate terminal)
cd frontend
cp .env.example .env
npm install --legacy-peer-deps
npm run dev
```

## Adding a New Agent

In your `.env`:
```
RELAY_AGENT_N_ID=your-agent-id
RELAY_AGENT_N_NAME=Your Agent
RELAY_AGENT_N_AVATAR=🤖
RELAY_AGENT_N_ROLE=Role description
RELAY_AGENT_N_MODEL=provider/model-name
RELAY_AGENT_N_PROVIDER=provider
RELAY_AGENT_N_KEY=your-agent-api-key
```

Restart the backend. The agent is seeded automatically.

## Adding a New API Endpoint

1. Add the route handler in `backend/main.py`
2. If new table needed, add model in `backend/models.py`
3. Update `documentation/backend.md` with the new endpoint and any schema changes
4. Push code + docs together

## Adding a New Frontend View

1. Add the view id to `VIEWS` array in `App.jsx`
2. Add the render block inside the `<main>` section
3. Add any new state variables at the top of the component
4. Update `documentation/frontend.md`
5. Push code + docs together

## Security Rules

- Never hardcode IDs, names, API keys, or credentials in source files
- All identity config lives in `.env` (gitignored)
- `.env` files are never committed
- Read `skills/security/SKILL.md` before touching auth, HTTP endpoints, or data storage
