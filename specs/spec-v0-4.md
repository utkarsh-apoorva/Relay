# Relay Spec v0.4 — Agent Control Plane

## Overview

v0.4 adds the missing control surface for Relay agents. v0.3 defined the Orchestrator and Project Manager as core system roles, but the product still has no usable interface to inspect them, configure them, or talk to them. The result is a dead-end UI: agent cards exist, but clicking them does nothing.

This spec introduces the Agent Control Plane:

1. A dedicated agent detail page at `/agents/:agentId`
2. Model connection and activation flow for every agent
3. Direct chat with any agent through Relay-native backend endpoints
4. Structured Orchestrator actions that emerge from chat and require human approval when they change the system
5. A light theme that coexists with the current dark theme
6. Fixes to the Kanban board and task detail page so the core UI is no longer visibly broken

The point of this release is simple: agents must become operable.

## Design Principles

1. **Agents must be configurable from the product.** If an agent needs a model to run, the UI must expose that directly.
2. **System agents are permanent infrastructure.** Orchestrator and PM are not optional records. They are fixed parts of every project.
3. **Chat is the control surface.** Especially for the Orchestrator, actions should emerge from conversation, not from a dashboard full of special-case buttons.
4. **Every section stays visible.** Empty data should produce an empty state, not missing layout.
5. **Human approval remains the safety gate.** The Orchestrator can propose creation or registration actions, but the human must approve system-changing operations.
6. **Fix visible product breakage now.** The Kanban board and task detail page must stop looking unfinished before more capability is layered on top.

---

## 1. Agent Detail Page

### 1.1 New Route

Add a new route:

- `GET /agents/:agentId`

Frontend route:
- `src/pages/AgentDetailPage.jsx` (or equivalent page location used by the app)

Router behavior:
- Clicking any agent card in the Agent Registry navigates to `/agents/:agentId`
- If `agentId` does not exist, render a standard not-found state
- If the agent exists but has no model configured, the page still renders fully, with an activation empty state inside the Model Connection section

### 1.2 Page Layout

The page renders six sections in this order. All six are always visible.

1. Identity
2. Model Connection
3. Meta Prompt / Soul
4. Capabilities
5. Activity
6. Chat

Each section uses the same card container style. Empty data does not collapse the section.

### 1.3 Identity Section

Purpose: show the agent's core identity at a glance.

Fields:
- Avatar
- Name
- Role
- Status
- Badge list

Rules:
- Orchestrator and PM show a `System Agent` badge
- Worker agents do not show the badge unless a future spec introduces additional system-owned types
- System agents cannot be deleted from this page
- If delete controls exist elsewhere in the product, they must be hidden or disabled for system agents

Status values for MVP:
- `inactive` — no model connected
- `ready` — model connected and last connection test succeeded
- `error` — model configured but last connection test failed
- `busy` — currently processing chat or task work

### 1.4 Model Connection Section

This is the critical interaction in v0.4.

#### Empty State

If the agent has no working model connection, render:

- Title: `Connect a model to activate this agent`
- Provider dropdown
- API key input
- Model name input
- API base URL input, shown only for `Custom` provider
- Save button
- Inline validation and connection test result area

Provider dropdown values:
- `openai`
- `anthropic`
- `openrouter`
- `custom`

Validation:
- Provider is required
- API key is required for all providers in v0.4
- Model name is required
- API base URL is required when provider = `custom`

#### Connected State

If the agent has a valid saved connection, render:

- Provider
- Model name
- Status indicator
- Last tested time
- `Change` button

The API key itself is never shown after save.

When `Change` is clicked, the section returns to edit mode with the current provider, model name, and base URL prefilled. API key input is blank and must be re-entered only if changed. If the backend supports preserving the existing encrypted key when omitted, the UI may show `Leave blank to keep existing key`.

#### Save Flow

On save:
1. Submit the form to the backend
2. Backend stores the API key encrypted at rest
3. Backend updates the agent's provider and model fields
4. Backend performs a connection test using a minimal model call or provider-specific ping
5. Backend returns success or failure
6. UI updates the status state and shows the result inline

Success message:
- `Model connected successfully`

Failure behavior:
- Keep the form open
- Show the backend error message inline
- Do not mark the agent as `ready`

### 1.5 Meta Prompt / Soul Section

Purpose: make the agent's system prompt visible and editable.

UI:
- Markdown editor textarea or markdown editor component
- Preview optional for MVP, edit mode is mandatory
- Save button

Rules:
- Orchestrator and PM are pre-populated with their default meta prompts derived from the v0.3 role definitions
- Worker agents start with an empty prompt
- Empty state text for worker agents: `No meta prompt defined yet`
- This field is read/write in v0.4

Storage behavior:
- The current saved prompt is stored on the agent record
- The default prompt for system agents should still exist in code or seed data so a new project can create them consistently
- Once persisted to the database, the saved value is the active prompt used by chat and runtime calls

### 1.6 Capabilities Section

Purpose: show what the agent can do in plain product terms.

UI:
- List of capabilities as editable rows or tokenized items
- Add capability control
- Remove capability control
- Save button

Empty state:
- `No capabilities defined yet`

Notes:
- Capabilities are product metadata. They are not a replacement for the full meta prompt.
- For system agents, initial capabilities should be seeded from their role definitions.

### 1.7 Activity Section

Purpose: show recent work and current operating state.

Show:
- Current task, if any
- Current task status
- Recent assigned tasks, newest first
- For each recent task: title, status, updated time, link to task detail page

Empty state:
- `No activity yet`

Limit for MVP:
- Show latest 10 task associations

### 1.8 Chat Section

Purpose: allow direct human invocation of any agent.

UI:
- Message list
- Input box
- Send button
- Loading state while waiting for response
- Optional streaming renderer if backend streaming is implemented in this release

Agent-specific behavior:
- **Orchestrator:** direct human invocation, bypasses PM
- **PM:** standard human interaction channel for project operations
- **Worker agents:** direct instruction channel

Empty state rules:
- The section is still visible if no chat history exists
- If no model is connected, disable the input and show: `Connect a model to chat with this agent`

Chat history scope for MVP:
- Load recent messages for that agent within the current project context if project-scoped
- If Relay currently models agents globally, load recent messages for that agent record

---

## 2. Permanent System Agents

### 2.1 Required Agents Per Project

Every project must have exactly two system agents:
- Orchestrator
- Project Manager

These are auto-linked when a project is created.

### 2.2 Creation Rules

On project creation:
1. Create the project record
2. Create or attach the project's Orchestrator agent
3. Create or attach the project's PM agent
4. Mark both as system agents
5. Ensure both appear in the Agent Registry immediately, even with no model connection

Implementation choice:
- If Relay uses project-scoped agents, create one Orchestrator and one PM per project
- If Relay uses shared global system agents, the project must still store explicit links to them

v0.4 recommendation: use **project-scoped system agents**. The Orchestrator and PM are part of the project's operating context and should have project-specific chat history, learnings, and configuration.

### 2.3 Deletion Rules

System agents:
- cannot be deleted
- cannot lose their project link
- always appear in the registry for their project

If a delete API exists, it must reject system agents with a clear error.

---

## 3. Agent Chat API

### 3.1 New Endpoint

Add:

- `POST /api/agents/:agentId/chat`

Purpose:
- send a direct message to an agent
- execute the message against the agent's configured model and meta prompt
- return the agent response
- emit structured action intents when produced by the Orchestrator

### 3.2 Request

```json
{
  "message": "string"
}
```

Optional v0.4 extension if project context is needed explicitly:

```json
{
  "message": "string",
  "projectId": "uuid"
}
```

If the route already resolves the project context through the agent record, `projectId` is not required.

Validation:
- `message` is required
- trim whitespace
- reject empty strings
- reject requests when the agent has no valid model connection

### 3.3 Response

One-shot MVP response:

```json
{
  "agent": {
    "id": "uuid",
    "name": "Orchestrator"
  },
  "message": {
    "role": "assistant",
    "content": "string"
  },
  "actions": [
    {
      "type": "create_task",
      "title": "Draft onboarding flow",
      "payload": {}
    }
  ]
}
```

If no action intents are present:

```json
{
  "agent": {
    "id": "uuid",
    "name": "Project Manager"
  },
  "message": {
    "role": "assistant",
    "content": "string"
  },
  "actions": []
}
```

Streaming is allowed but not required for v0.4. If implemented, use the same final message schema for the completed event.

### 3.4 Backend Execution Rules

When this endpoint is called:
1. Load the agent record
2. Load the agent's model provider, model name, encrypted credentials, and meta prompt
3. Build the system prompt from the saved meta prompt
4. Send the user's message to the configured provider
5. Return the model response
6. Parse any structured action intents if the agent is the Orchestrator
7. Persist the chat exchange
8. If the agent has a current task, log the conversation as a comment on that task

### 3.5 Conversation Logging

Persist every direct chat exchange to an agent chat table or equivalent storage.

Additionally:
- If the agent has an active current task, append a task comment containing the human message and agent response
- Comment format should clearly mark the source as `Agent Chat`
- If there is no current task, do not create a synthetic task just for logging

### 3.6 Error Cases

Return structured errors for:
- agent not found
- no model connected
- invalid provider configuration
- connection/auth failure from provider
- model invocation failure
- action parsing failure, if the assistant response was returned but intents could not be parsed

Recommended format:

```json
{
  "error": "agent_model_not_configured",
  "message": "Connect a model to this agent before sending chat messages."
}
```

---

## 4. Orchestrator Action Intents

### 4.1 Intent Model

The Orchestrator can return structured action intents inside chat responses. These are not separate controls in the page chrome. They emerge from chat.

Supported intent types in v0.4:
- `create_task`
- `assign_task`
- `create_agent`
- `register_agent`

### 4.2 Response Contract

The Orchestrator's backend prompt should instruct the model to emit machine-readable actions separately from natural language output.

Recommended server-side response shape:

```json
{
  "message": {
    "role": "assistant",
    "content": "I recommend creating a researcher agent for competitor analysis."
  },
  "actions": [
    {
      "id": "temp_action_1",
      "type": "create_agent",
      "status": "pending_approval",
      "summary": "Create Researcher Agent",
      "payload": {
        "name": "Competitor Researcher",
        "role": "Researcher",
        "capabilities": ["competitor analysis", "web research"],
        "metaPrompt": "..."
      }
    }
  ]
}
```

### 4.3 UI Rendering

In the chat thread, each action renders as a confirmation card below the assistant message.

Card content:
- action type label
- short summary
- key payload fields in readable form
- `Approve` button
- `Reject` button

Card states:
- `pending_approval`
- `approved`
- `rejected`
- `executed`
- `failed`

### 4.4 Approval Rules

Human approval is required for:
- `create_agent`
- `register_agent`

Recommended rule for v0.4:
- also require approval for `create_task` and `assign_task` when initiated from direct Orchestrator chat by a human, because this is a control plane surface and unintended writes should be explicit

If you want lower friction, `create_task` and `assign_task` may be auto-executable, but the safer default is approval for all four intent types in this release.

### 4.5 Execution Endpoints

Add action execution endpoints:

- `POST /api/agents/:agentId/actions/:actionId/approve`
- `POST /api/agents/:agentId/actions/:actionId/reject`

Approve request body for MVP:

```json
{}
```

Approve response:

```json
{
  "action": {
    "id": "temp_action_1",
    "type": "create_agent",
    "status": "executed"
  },
  "result": {
    "agentId": "uuid"
  }
}
```

Reject response:

```json
{
  "action": {
    "id": "temp_action_1",
    "type": "create_agent",
    "status": "rejected"
  }
}
```

### 4.6 Execution Behavior by Intent Type

#### create_task
Creates a task in the current project.

Payload fields:
- title
- description
- assigneeId, optional
- evalBrief, optional
- priority, optional
- status defaults to `todo`

#### assign_task
Updates an existing task's assignee.

Payload fields:
- taskId
- assigneeId

#### create_agent
Creates a new worker agent and adds it to the registry.

Payload fields:
- name
- role
- metaPrompt
- capabilities
- recommendedProvider, optional
- recommendedModel, optional

Newly created worker agents start as `inactive` until a model is connected.

#### register_agent
Registers an already-existing external or internal agent record with Relay.

Payload fields should be defined against the current registration model used by Relay.

If registration does not yet exist as a concrete backend concept, treat `register_agent` as a deferred write-path and implement only the UI/state contract in v0.4 while marking the backend execution as TODO.

---

## 5. Agent Data Model Changes

Add the following fields to the `agents` table, or equivalent model.

### 5.1 Required Columns

- `is_system_agent` — boolean, default `false`
- `system_role` — nullable enum/string: `orchestrator`, `project_manager`, null
- `provider` — nullable string
- `model` — nullable string
- `api_key_encrypted` — nullable text
- `api_base_url` — nullable text
- `meta_prompt` — nullable text
- `status` — string, default `inactive`
- `last_connection_test_at` — nullable datetime
- `last_connection_status` — nullable string: `success`, `failed`, null
- `project_id` — required if agents are project-scoped

### 5.2 Capability Storage

Choose one:
- `agent_capabilities` join table
- JSON array column on `agents`

Recommendation: use a separate `agent_capabilities` table only if capability querying is already a product need. Otherwise use a JSON/text array for v0.4.

### 5.3 Chat Storage

Add `agent_chats` or equivalent.

Recommended fields:
- `id`
- `agent_id`
- `project_id`, nullable if not needed
- `role` (`user`, `assistant`, `system`)
- `content`
- `actions_json`, nullable
- `created_at`

### 5.4 Pending Action Storage

Add `agent_chat_actions` or equivalent.

Fields:
- `id`
- `agent_id`
- `chat_message_id` or `agent_chat_id`
- `type`
- `status`
- `payload_json`
- `created_by` (`agent`)
- `approved_by`, nullable
- `approved_at`, nullable
- `rejected_at`, nullable
- `executed_at`, nullable
- `error_message`, nullable

---

## 6. Agent API Additions

### 6.1 Get Agent Detail

Add or extend:
- `GET /api/agents/:agentId`

Response should include:
- identity fields
- provider/model connection summary
- meta prompt
- capabilities
- recent activity
- system agent flags

### 6.2 Update Agent Model Connection

Add:
- `PATCH /api/agents/:agentId/model`

Request:

```json
{
  "provider": "openai",
  "apiKey": "sk-...",
  "model": "gpt-4.1",
  "apiBaseUrl": null
}
```

Response:

```json
{
  "agent": {
    "id": "uuid",
    "provider": "openai",
    "model": "gpt-4.1",
    "status": "ready",
    "lastConnectionStatus": "success",
    "lastConnectionTestAt": "2026-04-20T00:00:00.000Z"
  }
}
```

Failure response:

```json
{
  "error": "model_connection_failed",
  "message": "Authentication failed for the supplied API key."
}
```

### 6.3 Update Meta Prompt

Add:
- `PATCH /api/agents/:agentId/meta-prompt`

Request:

```json
{
  "metaPrompt": "# Soul\n..."
}
```

### 6.4 Update Capabilities

Add:
- `PATCH /api/agents/:agentId/capabilities`

Request:

```json
{
  "capabilities": ["task decomposition", "agent design"]
}
```

### 6.5 Get Agent Chat History

Add:
- `GET /api/agents/:agentId/chat`

Response:
- recent messages
- recent action cards with status

---

## 7. Light Theme

### 7.1 Theme Model

Relay currently has a dark UI. v0.4 adds a light skin using CSS custom properties, not hardcoded component-level overrides.

Add a theme toggle in the app shell.

Behavior:
- theme can switch between `dark` and `light`
- selected theme persists in local storage for MVP
- root element gets `data-theme="light"` or `data-theme="dark"`

### 7.2 Required CSS Custom Properties

Define theme tokens at the root level.

#### Shared semantic tokens

```css
:root {
  --color-accent: existing-accent;
  --color-success: existing-success;
  --color-warning: existing-warning;
  --color-danger: existing-danger;
  --radius-card: 12px;
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.08);
}
```

#### Dark theme

Keep current values, but move them under:

```css
[data-theme="dark"] {
  --color-bg-app: #0f1115;
  --color-bg-surface: #171a21;
  --color-bg-card: #1d212b;
  --color-border: rgba(255, 255, 255, 0.08);
  --color-text-primary: #f5f7fb;
  --color-text-secondary: #9aa3b2;
  --color-text-muted: #6f7785;
}
```

#### Light theme

```css
[data-theme="light"] {
  --color-bg-app: #f2f2f2;
  --color-bg-surface: #ebebeb;
  --color-bg-card: #ffffff;
  --color-border: rgba(15, 17, 21, 0.08);
  --color-text-primary: #1c1f26;
  --color-text-secondary: #4b5563;
  --color-text-muted: #6b7280;
}
```

Required usage areas:
- app background
- page background
- card background
- modal background
- text colors
- border colors
- input backgrounds
- input text
- empty states
- column backgrounds in Kanban

Accent colors remain unchanged between themes.

### 7.3 Theme Acceptance Rules

The light skin is not complete unless:
- all text remains readable on light backgrounds
- cards are white
- the app background is light gray
- current accent colors still work without clash
- hover, focus, and disabled states remain distinguishable

---

## 8. Kanban Board Fixes

These are mandatory cleanup items in v0.4.

### 8.1 Column Width and Scrolling

Problems:
- columns are too narrow
- the Done column gets cut off at the viewport edge

Fix:
- set a minimum column width of `240px`
- the board container must support horizontal scrolling
- add right-side padding so the final column is fully visible

Recommended CSS:

```css
.kanban-board {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding: 0 16px 16px 16px;
}

.kanban-column {
  min-width: 240px;
  width: 240px;
  flex: 0 0 240px;
}
```

### 8.2 Card Title Truncation

Problem:
- titles are truncating mid-character and look broken

Fix:
- single-line truncation with ellipsis
- proper inner padding so text does not collide with card edges

Recommended CSS:

```css
.kanban-card__title {
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  padding-right: 8px;
}
```

If two-line titles are preferred later, implement line clamp properly. Do not allow raw clipping.

### 8.3 Add Card Button

Each column must show an `Add card` button or equivalent CTA.

Placement:
- within the column header or directly beneath it

Behavior:
- creates a new task prefilled with that column's status

### 8.4 Priority Tag Bleed

Problem:
- priority tags visually bleed into neighboring columns

Fix:
- ensure cards create a local stacking context
- set overflow and z-index correctly

Recommended CSS:

```css
.kanban-column {
  position: relative;
  overflow: hidden;
}

.kanban-card {
  position: relative;
  z-index: 1;
}
```

If dropdowns or menus need to escape the card boundary, use a portal-based layer rather than uncontrolled z-index escalation.

### 8.5 Avatar Consistency

Problem:
- avatar styles are inconsistent across cards

Fix:
- standardize avatar shape, size, background treatment, and fallback initials

MVP rules:
- 24x24 on cards
- 32x32 on detail headers
- circular mask
- same fallback typography everywhere

---

## 9. Task Detail Page Fixes

The page exists but is visibly broken. Fix it in v0.4.

### 9.1 Title Rendering

Problem:
- task title is missing, leaving blank space above comments

Fix:
- render the task title as the page's primary heading
- if title is empty or null, show `Untitled task`

### 9.2 Status and Priority Null Handling

Problem:
- status and priority show dark dashes or invisible placeholders

Fix:
- normalize null or invalid values before render
- show explicit fallback labels

Fallbacks:
- status: `No status`
- priority: `No priority`

Do not render raw `-` placeholders.

### 9.3 Date Parsing Bug

Problem:
- created and updated timestamps show `Invalid Date`

Fix:
- normalize API date parsing in one utility function
- only format valid ISO strings or timestamps
- show fallback text if parsing fails

Fallbacks:
- `Created date unavailable`
- `Updated date unavailable`

### 9.4 Always-Visible Sections

All task detail sections remain visible even when empty.

Sections and empty states:
- Description → `No description yet`
- Eval Brief → `No eval brief defined`
- Result → `No result yet`
- Judgement → `No judgement yet`
- Comments → `No comments`

This mirrors the agent detail page rule: empty is not hidden.

### 9.5 Wiki Link in Header

Add a wiki link next to the project name in the task header.

Behavior:
- if the project has a wiki URL or wiki route, show a clickable link/icon next to the project name
- if no wiki exists, omit only the link control, not the project name

Recommended label:
- `Wiki`

---

## 10. Interaction Flows

### 10.1 Connect Model to System Agent

1. User opens Orchestrator or PM detail page
2. Model Connection section shows activation empty state
3. User selects provider, enters API key and model, enters base URL if custom
4. User clicks Save
5. Backend encrypts credentials and tests connection
6. On success, agent status becomes `ready`
7. Chat input becomes enabled

### 10.2 Direct Chat with Orchestrator

1. User opens Orchestrator page
2. User sends a message like `Create the task plan for the onboarding redesign`
3. Backend invokes the Orchestrator using its connected model and meta prompt
4. Response returns natural language plus structured actions
5. UI renders the message and action confirmation cards
6. User approves or rejects each action
7. Approved actions execute and update chat card state

### 10.3 Create Worker Agent from Orchestrator Chat

1. Orchestrator recommends a new worker agent in chat
2. UI shows a `create_agent` confirmation card
3. User clicks Approve
4. Backend creates the worker agent record
5. Agent appears in the registry immediately
6. New worker agent starts as `inactive` until a model is connected

### 10.4 Task Detail Empty State Rendering

1. User opens a task with sparse data
2. Page still renders title, metadata, project header, wiki link area, and all content sections
3. Empty sections display the specified fallback copy
4. Page never shows blank gaps where sections should be

---

## 11. Implementation Notes

### 11.1 Seeding System Agent Defaults

The Orchestrator and PM should be seeded with:
- default name
- default role
- `is_system_agent = true`
- `system_role`
- default capabilities
- default meta prompt derived from v0.3 definitions

### 11.2 Security

- API keys must be encrypted at rest
- API keys must never be returned in API responses after save
- Audit logs should record model connection updates without logging secrets

### 11.3 Provider Adapter Layer

Do not scatter provider-specific chat logic across route handlers.

Add or extend a provider adapter layer that takes:
- provider
- model
- api key
- base url
- system prompt
- user message

and returns:
- text response
- optional structured intents

This keeps OpenAI, Anthropic, OpenRouter, and Custom behind one interface.

### 11.4 MVP Boundary

In scope for v0.4:
- agent detail page
- model connection flow
- direct agent chat
- orchestrator action cards with approval/reject path
- light theme
- Kanban fixes
- task detail fixes

Out of scope for v0.4:
- rich chat threading features
- multi-user approvals
- advanced provider failover
- prompt version history
- granular permission model

---

## 12. Open Questions

1. **Streaming:** Do we want to ship one-shot chat first, or implement streaming now? Recommendation: one-shot first unless the provider abstraction already supports streaming cleanly.
2. **Action approval policy:** Should `create_task` and `assign_task` require approval in direct Orchestrator chat? Recommendation: yes, for v0.4 safety.
3. **Registration semantics:** Is `register_agent` already a real backend concept, or only a planned one? If not real yet, keep the UI/action contract but defer backend execution.
4. **Project context for direct chat:** Should every agent chat be explicitly project-scoped in the API payload, or can the system infer it from the agent record? Recommendation: infer from project-scoped agents.

---

## 13. The One Thing

Relay already has agents in the data model. v0.4 makes them usable.

If this release ships correctly, a user can do three things they cannot do today:
- open an agent
- activate it with a model
- talk to it and approve what it wants to change

That is the control plane. Everything else in this spec supports that.