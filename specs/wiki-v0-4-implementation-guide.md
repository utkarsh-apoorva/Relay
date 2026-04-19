# Relay v0.4 Implementation Guide for Linus

Reference doc: `specs/spec-v0-4.md`

Build order is fixed:
1. Kanban fixes
2. Task detail fixes
3. Agent detail page
4. Model connection flow
5. Agent chat + action cards
6. Light theme pass

Current codebase anchors:
- Frontend routing: `frontend/src/main.jsx`
- Shared shell: `frontend/src/App.jsx`
- Agent registry: `frontend/src/pages/AgentRegistryPage.jsx`
- Project/Kanban: `frontend/src/pages/ProjectPage.jsx`
- Task detail: `frontend/src/pages/TaskDetailPage.jsx`
- API client: `frontend/src/api/client.js`
- Styles: `frontend/src/styles.css`
- Backend routes: `backend/main.py`
- Models: `backend/models.py`
- Seed/runtime defaults: `backend/seed.py`, `backend/orchestrator.py`
- Secret handling: `backend/security.py`

## Step 1. Fix Kanban layout and card rendering

Spec refs: 8.1 to 8.5.

Build:
- widen columns to fixed/min 240px
- make board horizontally scrollable
- add right padding so final column is visible
- fix title truncation with ellipsis, not clipping
- add per-column `Add card` CTA wired to create modal / draft state
- normalize avatar treatment on cards
- stop priority pill bleed with local stacking context

Touch:
- `frontend/src/pages/ProjectPage.jsx`
- `frontend/src/App.jsx` if reusing existing task modal/openTaskModal path
- `frontend/src/styles.css`

API:
- existing `GET /api/tasks`
- existing `PATCH /api/tasks/:taskId`
- existing `POST /api/tasks`

Dependency:
- none

## Step 2. Fix task detail structure and null handling

Spec refs: 9.1 to 9.5, 10.4.

Build:
- always render title, with `Untitled task` fallback
- normalize status / priority fallback labels instead of raw null or `-`
- centralize date parsing, stop `Invalid Date`
- keep Description, Eval Brief, Result, Judgement, Comments visible when empty
- add wiki link in header next to project name when available

Touch:
- `frontend/src/pages/TaskDetailPage.jsx`
- `frontend/src/api/client.js` or local page util for date normalization
- `frontend/src/styles.css`
- `backend/main.py` only if task detail payload needs wiki URL or project wiki presence

API:
- existing `GET /api/tasks/:taskId`
- existing `POST /api/tasks/:taskId/comment`
- existing `PATCH /api/tasks/:taskId`
- existing `GET /api/projects`
- existing `GET /api/projects/:projectId/wiki` if using current wiki route

Dependency:
- do after Step 1 so the basic board-to-detail path feels stable

## Step 3. Extend agent data model and detail API

Spec refs: 2, 5, 6.1.

Build:
- add agent fields needed for v0.4: system flags, system role, model connection state, meta prompt, connection timestamps, project scoping if taking the recommended path
- add chat storage + pending action storage tables, or minimal equivalents
- add `GET /api/agents/:agentId` response shape for identity, connection summary, meta prompt, capabilities, recent activity, system flags
- enforce non-deletion for system agents
- auto-create / attach Orchestrator + PM per project

Touch:
- `backend/models.py`
- `backend/main.py`
- `backend/seed.py`
- `backend/orchestrator.py` if keeping lightweight SQLite migration path there, otherwise move migration logic somewhere cleaner
- maybe `backend/database.py` depending on migration approach

API:
- new `GET /api/agents/:agentId`
- existing `GET /api/agents`
- existing project creation path `POST /api/projects`

Dependency:
- required before frontend agent detail page

## Step 4. Add agent detail page shell

Spec refs: 1.1 to 1.8.

Build:
- add route `/agents/:agentId`
- click-through from agent registry cards
- six fixed sections in order: Identity, Model Connection, Meta Prompt / Soul, Capabilities, Activity, Chat
- keep all sections visible even when empty
- show `System Agent` badge and status states in identity header

Touch:
- `frontend/src/main.jsx`
- new `frontend/src/pages/AgentDetailPage.jsx`
- `frontend/src/pages/AgentRegistryPage.jsx`
- `frontend/src/styles.css`

API:
- new `GET /api/agents/:agentId`

Dependency:
- Step 3

## Step 5. Implement model connection flow

Spec refs: 1.4, 6.2, 10.1, 11.2, 11.3.

Build:
- empty-state connection form
- connected-state summary with `Change`
- provider-specific validation
- encrypted API key storage
- connection test on save
- status transitions: inactive, ready, error, busy
- do not return API key after save

Touch:
- `frontend/src/pages/AgentDetailPage.jsx`
- `frontend/src/styles.css`
- `backend/main.py`
- `backend/models.py`
- `backend/security.py`
- provider adapter module, likely new backend file instead of bloating route handler

API:
- new `PATCH /api/agents/:agentId/model`
- existing/new `GET /api/agents/:agentId`

Dependency:
- Step 4 for UI shell
- Step 3 for fields/storage

## Step 6. Implement meta prompt and capabilities editing

Spec refs: 1.5, 1.6, 6.3, 6.4.

Build:
- editable meta prompt section
- editable capabilities section
- seeded defaults for Orchestrator / PM
- empty state for workers

Touch:
- `frontend/src/pages/AgentDetailPage.jsx`
- existing markdown editor components if reused
- `frontend/src/styles.css`
- `backend/main.py`
- `backend/models.py`
- `backend/seed.py`

API:
- new `PATCH /api/agents/:agentId/meta-prompt`
- new `PATCH /api/agents/:agentId/capabilities`
- existing/new `GET /api/agents/:agentId`

Dependency:
- Step 4 shell
- Step 3 model changes

## Step 7. Implement direct agent chat

Spec refs: 1.8, 3, 5.3, 6.5, 10.2.

Build:
- chat history load
- one-shot send path first, streaming optional
- persist user + assistant messages
- disable input if no valid model connection
- if agent has active task, mirror exchange into task comments per spec

Touch:
- `frontend/src/pages/AgentDetailPage.jsx`
- `frontend/src/api/client.js`
- `frontend/src/styles.css`
- `backend/main.py`
- `backend/models.py`
- provider adapter module

API:
- new `GET /api/agents/:agentId/chat`
- new `POST /api/agents/:agentId/chat`

Dependency:
- Step 5 model connection
- Step 6 meta prompt, since runtime prompt should read persisted value

## Step 8. Implement Orchestrator action cards and approval flow

Spec refs: 4.1 to 4.6.

Build:
- parse structured intents from Orchestrator responses
- persist pending actions with status
- render confirmation cards directly under the producing assistant message
- approve / reject actions
- execute `create_task`, `assign_task`, `create_agent`
- `register_agent` can stay UI/state contract only if backend semantics are not real yet

Touch:
- `frontend/src/pages/AgentDetailPage.jsx`
- `frontend/src/styles.css`
- `backend/main.py`
- `backend/models.py`
- provider adapter / orchestrator prompt logic

API:
- new `POST /api/agents/:agentId/actions/:actionId/approve`
- new `POST /api/agents/:agentId/actions/:actionId/reject`
- chat endpoints from Step 7
- existing task APIs for execution side effects
- existing/new agent creation path if exposed internally, otherwise execute in handler

Dependency:
- Step 7
- Step 3 pending action storage

## Step 9. Apply light theme using tokens, not ad hoc overrides

Spec refs: 7.1 to 7.3.

Build:
- move current colors to semantic custom properties
- add `[data-theme="dark"]` and `[data-theme="light"]`
- persist theme choice in local storage
- add app-shell toggle
- pass through Agent Detail, Kanban, Task Detail, modals, forms, empty states

Touch:
- `frontend/src/styles.css`
- `frontend/src/App.jsx` or shared shell location for theme toggle/state
- any page-level JSX only if theme toggle needs UI plumbing

API:
- none

Dependency:
- do last, after structural fixes, otherwise you restyle broken states twice

## Notes on sequencing

- Do not start with chat. It depends on agent storage, prompt persistence, model connection, and new page structure.
- Do not do light theme before the layout fixes. You will paint over unresolved breakage.
- If project-scoped system agents are adopted, make that call before Step 3 lands. It touches schema, chat scope, activity scope, and project creation.
- Keep provider logic behind one adapter boundary per 11.3. Do not spread OpenAI / Anthropic / OpenRouter conditionals across route handlers.
- Current backend only has `PATCH /api/agents/:agentId` for self-updates. v0.4 needs product-owned agent admin endpoints, not just agent-owned registration paths.
