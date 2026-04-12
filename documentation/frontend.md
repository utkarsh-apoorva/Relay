# Relay — Frontend

## Stack

| Library | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI framework |
| Vite | 6.x | Dev server + bundler |
| @hello-pangea/dnd | 18.x | Drag and drop (React 18 compatible) |
| @vitejs/plugin-react | 4.x | JSX transform |

No CSS framework. All styles are hand-written in `src/styles.css`.

## File Structure

```
frontend/
├── index.html              # Root HTML, mounts #root
├── package.json
├── vite.config.js          # Port 3000, proxies /api → localhost:8000
├── .env.example            # Env var template
├── src/
│   ├── main.jsx            # ReactDOM.createRoot entry point
│   ├── App.jsx             # Entire application (single-file SPA)
│   ├── styles.css          # All styles
│   └── api/
│       └── client.js       # fetch wrapper, reads API key from localStorage
```

## Environment Variables

Set in `frontend/.env` (gitignored):

| Variable | Description | Default |
|---|---|---|
| `VITE_RELAY_API_KEY` | API key sent with every request | — |
| `VITE_RELAY_HUMAN_ID` | ID used for human owner (approval queue, assignee) | `human` |
| `VITE_RELAY_HUMAN_NAME` | Display name for human owner | `Human` |

Accessed in code via `import.meta.env.VITE_*`.

## API Client (`src/api/client.js`)

- Reads API key from `localStorage` (`relay_api_key`) on each call
- Falls back to `VITE_RELAY_API_KEY` env var
- Sets `Content-Type: application/json` and `X-API-Key` on all requests
- Parses JSON response; throws on non-2xx

## App Structure (`src/App.jsx`)

Single component. All state lives at the top level.

### State

| State | Type | Purpose |
|---|---|---|
| `view` | string | Active view: projects / kanban / approval / calendar / agents / usage |
| `projects` | array | All projects |
| `agents` | array | All agents |
| `tasks` | array | All tasks |
| `sprints` | array | All sprints |
| `usage` | object | `{ rows, totals }` token usage data |
| `projectId` | string | Selected project filter |
| `sprintId` | string | Selected sprint filter |
| `calendarScope` | string | `all` or a project id |
| `selectedAgentId` | string | Agent selected in Agents view |
| `taskDraft` | object | Task form state |
| `projectDraft` | object | Project form state |
| `sprintDraft` | object | Sprint form state |
| `taskModalOpen` | bool | Task create/edit modal |
| `projectModalOpen` | bool | Project create modal |
| `sprintModalOpen` | bool | Sprint create modal |
| `approvalTargets` | object | `{ taskId: agentId }` for approval reassignment |

### Views

| View | Description |
|---|---|
| `projects` | Master list of all projects with stats, archive button |
| `kanban` | Drag-and-drop board filtered by project + sprint |
| `approval` | Tasks assigned to the human owner; approve/modify/reject/reassign |
| `calendar` | 35-day grid showing tasks by due date |
| `agents` | Agent cards; click to see assigned tasks |
| `usage` | Token usage table read from OpenClaw session stores |

### Data Loading

`load()` fetches all 5 endpoints in parallel (`Promise.all`) and updates all state at once. Called on mount and after every mutation.

### Drag and Drop

Uses `@hello-pangea/dnd`. `DragDropContext → Droppable (per column) → Draggable (per task)`. On drop, PATCHes the task status and calls `load()`.

## Vite Config

```js
server: {
  port: 3000,
  proxy: { '/api': 'http://localhost:8000' }
}
```

All `/api/*` requests from the browser are proxied to the backend. No CORS issues in dev.

## Running

```bash
cd frontend
cp .env.example .env   # fill in VITE_RELAY_API_KEY etc.
npm install --legacy-peer-deps
npm run dev            # starts on http://localhost:3000
```
