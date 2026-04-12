# Relay — Architecture Overview

## Summary

Relay is a self-hosted project management tool for human–AI team coordination. Agents and humans are first-class citizens. It runs entirely on localhost with no external dependencies beyond what's installed.

## System Layout

```
┌──────────────────────────────────────────────┐
│  Browser (localhost:3000)                    │
│  React SPA — Vite dev server                 │
│  Proxies /api/* → localhost:8000             │
└──────────────────────┬───────────────────────┘
                       │ HTTP (proxied)
┌──────────────────────▼───────────────────────┐
│  FastAPI backend (localhost:8000)             │
│  Python 3.9+, uvicorn                        │
│  REST API, API key auth                       │
└──────────────────────┬───────────────────────┘
                       │ SQLAlchemy ORM
┌──────────────────────▼───────────────────────┐
│  SQLite (data/relay.db)                      │
│  Single file, no infra needed                 │
└──────────────────────────────────────────────┘
```

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Database | SQLite | Zero infra, portable, easily migrated to Postgres later |
| ORM | SQLAlchemy 2.0 | Typed mapped columns, clean migration path |
| API framework | FastAPI | Fast to build, auto-docs, native async |
| Frontend | React 18 + Vite | Fast HMR, no heavy build config |
| Styling | Plain CSS (no Tailwind) | Zero runtime cost, full control |
| Drag and drop | @hello-pangea/dnd | React 18 compatible fork of react-beautiful-dnd |
| Auth | API key in header | Simple, agent-friendly, no session management |
| Config | `.env` files | Gitignored, no secrets in repo |

## Ports

| Service | Port |
|---|---|
| Frontend (Vite dev) | 3000 |
| Backend (uvicorn) | 8000 |

## Data Flow

1. Frontend fetches all data on load via `Promise.all` across all endpoints.
2. After any mutation (create/patch/comment), frontend calls `load()` to refresh all state.
3. No WebSocket or polling — manual refresh on action.
4. API key is stored in `localStorage` and sent as `X-API-Key` header on every request.
5. Backend validates the key against `api_keys` table. If missing or invalid → 401.
