# Agent Detail + v0.4 Design Notes for Ive

Context: this is design direction for spec v0.4, not an implementation spec. The job is to make Relay agents feel operable, not decorative. The page should read as a control plane, not a profile screen.

## 1. Agent Detail Page

Reference: spec sections 1.1 to 1.8.

### Core layout
Use a single-page detail view with a clear vertical reading order:
1. Identity
2. Model Connection
3. Meta Prompt / Soul
4. Capabilities
5. Activity
6. Chat

This order matters. The user should understand who the agent is, whether it is active, what drives it, what it can do, what it has been doing, then finally talk to it.

### Visual hierarchy
Identity and Model Connection should carry the most weight above the fold.
Chat should be visually strong, but lower on the page so the user sees configuration state before they try to use it.
All sections should remain visible even when empty. Empty should feel intentional, not broken.

### Identity section
This should feel like a compact control header, not a social profile.
Include:
- avatar
- agent name
- role
- status pill
- badges

Status should be legible at a glance. Treat `inactive`, `ready`, `error`, and `busy` as first-class visual states with distinct color and icon treatment.

### System agent badge
`System Agent` should look infrastructural, not celebratory. Think small high-signal badge, neutral fill, strong outline, compact typography. It should help the user understand why Orchestrator and PM are permanent and non-destructive.

Avoid making worker agents visually second-class. The badge should communicate permanence, not superiority.

## 2. Model Connection Section

Reference: spec section 1.4 and interaction flow 10.1.

This is the most important state transition on the page.

### Empty state
The empty state should feel like activation, not failure.
Use a strong title, short guidance copy, then the form immediately.
Recommended treatment:
- prominent title
- compact helper text explaining that the agent is inactive until connected
- provider, API key, model, base URL if needed
- inline result area reserved even before submission

Do not bury this inside an accordion. This is the primary action.

### Connected state
The connected state should compress into a summary card.
Show:
- provider
- model
- current status
- last tested time
- `Change` action

The summary should look stable and trustworthy. The user should feel the agent is now usable.

### State contrast
The empty state should be visually open and form-led.
The connected state should be visually compact and status-led.
That contrast matters because it tells the user whether they are configuring or operating.

## 3. Chat Interface

Reference: spec sections 1.8, 3, and 10.2.

Chat is the control surface. Design it with operator confidence, not consumer-chat whimsy.

### Design goals
- easy scan of human vs agent messages
- room for long responses without visual fatigue
- action cards should feel native to the conversation, not bolted on
- disabled state should be explicit when no model is connected

### Message layout
Use clean left-right separation or clearly distinct message containers. The agent response should be readable in blocks, not full-width walls.
Timestamps can be secondary or hidden until hover if the thread is dense.

### Empty chat state
When there is no history, the section should still feel alive. A good empty state here should explain what this chat is for, not just say there are no messages.

### Disabled chat state
If no model is connected, keep the chat UI visible but disable the input. The disable treatment should point back to the Model Connection section rather than feeling dead.

## 4. Action Confirmation Cards

Reference: spec section 4.

These are the most novel UI element in v0.4. They need to feel safe, legible, and deliberate.

### Placement
Render each card directly under the assistant message that produced it. The relationship must be obvious.

### Card contents
Prioritize:
- action type
- human-readable summary
- 2 to 4 key payload fields
- clear primary decision controls

Do not dump raw JSON by default. Payload should be translated into product language.

### Approve / Reject UX
`Approve` should feel like explicit system authorization, not a casual CTA.
`Reject` should be equally visible, but lower emphasis.

Recommended pattern:
- full-width card
- compact header row with type + status
- readable payload block
- decision buttons fixed in a clear footer zone

### Card states
The states need to be visually distinct:
- pending approval: waiting, high attention
- approved: acknowledged, transitional
- executed: success, calm
- rejected: final, muted
- failed: final, error-forward

Do not let executed and approved look the same.

## 5. Light Theme Direction

Reference: spec section 7.

The light theme should not feel like a palette inversion of Discord dark. It should feel quieter, more editorial, and more operational.

### Direction
- off-white app background
- true white cards
- very light structural surfaces
- crisp borders instead of heavy fills
- preserve Relay accent colors, but use them with restraint

### Tone
The dark theme can stay denser. The light theme should feel calmer and more precise. Think product control plane, not marketing site.

### What to watch
- muted text must still pass at-a-glance readability
- badges and status pills cannot disappear into pale backgrounds
- drag states, hover states, and disabled states need enough contrast

## 6. Kanban Fixes

Reference: spec section 8.

These are cleanup items, but they affect trust.

### Column treatment
Columns need enough width to read titles and metadata without visual compression. The board should read as horizontally scrollable by design, not accidentally overflowing.

### Card treatment
Cards should have:
- stable padding
- consistent avatar placement
- clean title truncation
- priority tags that stay inside their own card layer

### Add card CTA
The `Add card` control should be obvious in every column. It should feel like part of column management, not a floating global action.

### Avatar consistency
Set one avatar system and apply it everywhere. Relay currently feels inconsistent here. The fix should carry across Kanban, task detail, and agent surfaces.

## 7. Task Detail Page Hierarchy

Reference: spec section 9 and flow 10.4.

The current page feels like fragments. It needs a stronger reading order.

### Recommended section hierarchy
1. Header row: back, project name, wiki link
2. Primary title
3. Metadata band: status, priority, assignee, created, updated
4. Description
5. Eval Brief
6. Result
7. Judgement
8. Comments

### Header behavior
The task title must anchor the page. If metadata becomes more prominent than the title, the page will still feel broken.

### Empty states
Every section should render even when empty. The empty copy should be quiet and structural, not playful.

### Wiki link
Treat `Wiki` as a contextual navigation affordance next to the project label. Small, obvious, not dominant.

## 8. Cross-cutting visual rule

Relay should stop hiding absence by removing UI. Empty sections, disabled chat, unconnected models, and sparse task data should all remain structurally visible. The design language for v0.4 is: the system is complete, even when the data is not.
