# Relay Spec v0.2 — AI-First Task System

## Problem

Relay's current UI and data model are designed for humans: Kanban cards, popups, text boxes, comment threads. But Relay's primary users are AI agents creating and executing tasks, with humans reading the output. The current model creates friction:

- Task notifications to agents contain only titles — no context, no spec
- Comments are a human convention that agents don't naturally use
- No project-level context exists for agents to understand what they're working on
- Results are scattered across comments instead of structured output fields

## Design Principles

1. **AI creates, AI executes, humans read.** The entire flow is agent-to-agent. Humans observe and annotate.
2. **Tasks are self-contained specs.** Everything an agent needs to execute lives in the task description.
3. **Structured output, not conversation.** Results go in dedicated fields, not comment threads.
4. **Project context is first-class.** Every project has a wiki that agents read before acting.

## Changes

### 1. Project Wiki

Every project gets a wiki page. This is the first thing agents read when assigned a task in that project.

- Agents update the wiki when plans change or new context is discovered
- The wiki provides project-level context that individual tasks shouldn't repeat
- Wiki content is markdown, rendered for human consumption

### 2. Task Card Redesign

**Current:** Click a card → popup opens → text boxes + comments.

**New:** Task description and result description render inline on the card or in an expanded view (not a popup). Both accept markdown input and render it for human consumption.

### 3. Task Fields

| Field | Who Writes | Purpose |
|-------|-----------|---------|
| Task Description | Creator (AI or human) | The spec. What needs to be done, with all context needed to execute. Markdown in, rendered out. |
| Result Description | Executor AI | The output. What was done, what was found, what was delivered. Markdown in, rendered out. |
| Judgement | Evaluating AI | Assessment of the work. Quality, completeness, issues. Markdown in, rendered out. |
| Comments | Humans only | Human annotations, questions, or feedback. AI agents never add comments. |

### 4. Agent Editing Rules

AI agents may only edit three fields:

1. **Task Description** — agents should NOT append to an existing task description. The task description is the spec. If the task needs to change, create a new task or subtask. The original ask stays intact.
2. **Result Description** — append with attribution. Each agent adds a timestamped block:
   ```
   ## [Agent Name | Timestamp]
   <result content>
   ```
   No auto-summarization. Each agent adds their block. Full history preserved for audit trail and reasoning.
3. **Judgement** — append with attribution, same format as result description.

Agents never add comments. Comments are for humans only.

### 5. Append Behavior

When all three agent-editable fields already have content, agents append to the respective field with attribution blocks (see above).

**No automatic summarization.** Rationale:

- Summarization destroys audit trail — you lose who said what and when
- Full history is more useful for agents reasoning about the task
- If a field gets unwieldy, that signals the task should be split, not compressed
- Summarization only happens on explicit instruction from a human

### 6. Meta Prompt

Each task notification sent to agents includes a meta prompt that provides:

- Who the assignee is and what agent type they are
- Project wiki context
- Execution rules (only edit task description, result description, judgement; never add comments)
- Output format expectations for the result field

This meta prompt is automatically attached to every task and is not editable per-task.
