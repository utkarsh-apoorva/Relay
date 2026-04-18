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
| Eval Brief | Orchestrator | How this task will be evaluated. Acceptance criteria, test cases, expected output. Markdown in, rendered out. |
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

The orchestrator writes the eval brief for each task. Evaluating agents should reference the eval brief when writing their judgement.

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

### 7. Relay-Native Agents

Relay has its own agent runtime. Integration with OpenClaw is not mandatory — it is one integration path, not a dependency.

- Relay agents have their own models, fallbacks, personality, and skills
- The orchestrator agent (see below) is a Relay-native agent
- OpenClaw agents can be connected as an integration, but Relay must function without OpenClaw
- Specialized Relay agents: orchestrator, evaluator, etc. — these are not general-purpose chat agents

### 8. Orchestrator Agent

Every project is created and managed by an orchestrator agent.

- The orchestrator decomposes a goal into tasks, sequences them, assigns them to agents, and sets deadlines
- Humans receive review tasks, not execution tasks (unless they opt in)
- The orchestrator acts as a spec quality gate — projects are never just a bag of unstructured tasks
- If a human creates a project, it goes to the orchestrator as a task to refine before any execution begins. The orchestrator structures the human's intent into proper tasks with assignments and deadlines.

### 9. Task Assignment is Metadata, Not Content

Task descriptions never specify which agent should execute them. Assignment is a metadata concern — the task is already assigned to an agent by the time it reaches them. The task description is pure spec.

### 10. Task Detail Page

Each task opens in its own dedicated detail page (not a popup).

- The page renders: task description (markdown), result description (markdown), evaluation/judgement description (markdown), and other metadata (assignee, deadline, status, project)
- A dedicated page means a dedicated URL — useful for linking between tasks and for agents to reference specific tasks
- The inline card view on the Kanban board shows a summary; the detail page shows everything

### 11. Atomic Tasks

Tasks must be atomic and assignable to exactly one agent in the system.

- Task descriptions cannot exceed 500 words. If a task needs more, split it into multiple tasks with dependencies.
- Each task has exactly one assignee — no shared ownership.
- The 500-word limit forces clarity and prevents agents from receiving ambiguous mega-tasks.

### 12. Eval Brief

The orchestrator must create an eval brief for every task — a short description of how this task will be evaluated.

- The eval brief could include: acceptance criteria, test cases, expected output format, or a simple pass/fail checklist.
- This lives in the task as a separate field (not part of the task description).
- Evaluating agents use the eval brief to write their judgement. Humans can read it to understand what "done" looks like.

### 13. Project Creation UI

The primary CTA on the project creation screen is "Start Orchestration" — not "Create Project."

- This signals clearly that the human is providing intent, not structuring the project. The orchestrator does the structuring.
- The human provides a brief (goal, context, constraints). The orchestrator decomposes it into tasks.
- "Start Orchestration" sends the brief to the orchestrator as a task to refine and decompose.

### 14. Meta API

Relay exposes a `GET /api/meta` endpoint that provides the system's rules to any agent — internal or external.

The endpoint returns:
1. **Project creation schema** — what fields a project needs, what the orchestrator expects in the initial brief
2. **Task decomposition rules** — atomic, max 500 words, single assignee, must include eval brief
3. **Agent registry** — what agents exist in the system and their capabilities, so any orchestrator (internal or external) knows who to assign to
4. **Current meta prompt template** — the same prompt attached to tasks, so any agent can self-educate before acting

The meta prompt is served from the API, not hardcoded. When rules update, every agent gets the current version on next call. No stale prompts.

This also enables external harness-based orchestrators: an external agent calls `GET /api/meta` first, learns the rules, then creates a project with a proper brief. The internal orchestrator picks it up and decomposes, OR the external agent decomposes itself using the rules from the meta endpoint.

### 15. Agent Registration Handshake

When an agent registers with Relay, the registration response includes the meta endpoint URL and a directive to store it and use it on every subsequent interaction with Relay.

- This is the proactive path — agents learn the rules before they act.
- The registration response includes: meta endpoint URL, current version of the meta prompt, and a directive to call `/api/meta` before any project/task creation.
- Agents are expected to cache this and reference it. But compliance is not assumed — validation (see below) is the enforcement layer.

### 16. API Validation with Structured Errors

Every API call that creates or modifies projects/tasks is validated against the system rules. If validation fails, Relay returns a structured, machine-parseable error.

Error format:
```json
{
  "error": "<machine_readable_code>",
  "message": "<human and agent readable explanation>",
  "meta": "GET /api/meta for full creation rules"
}
```

Example:
```json
{
  "error": "task_description_exceeds_limit",
  "message": "Task description is 812 words. Maximum is 500. Split into multiple tasks.",
  "meta": "GET /api/meta for full creation rules"
}
```

Key properties:
- Errors are consistent and machine-parseable — agents can programmatically correct their requests without guessing.
- Every error includes a pointer to `/api/meta` so agents can self-correct without human intervention.
- This is the reactive path — catches non-compliant agents that didn't read the manual, and makes Relay resilient to badly-behaved agents.
- Validation is the enforcement layer. Registration is the education layer. Both are needed.
