# Relay Spec v0.3 — Agent Roles: Orchestrator & Project Manager

## Overview

v0.3 defines the two core agent roles that run Relay projects: the Orchestrator and the Project Manager. Together they form the brain and the nervous system of any project. Orchestrator thinks. PM runs.

Worker agents (executors, researchers, evaluators) are created by the Orchestrator per-project and are not specified here — they will be defined in a future spec.

## Design Principles

1. **Orchestrator is a CTO, not a scheduler.** It hires, fires, restructures, does root-cause analysis, and self-heals the organization of agents working on a project. It does not merely decompose tasks — it architects the team and the system.
2. **Orchestrator is event-driven, not continuous.** It is invoked on: project creation, PM escalation, and healing cycle trigger. It does not sit in the loop on every task completion.
3. **PM is the nervous system.** The Project Manager runs continuously — monitoring progress, keeping humans informed, running evals, and escalating to the Orchestrator when needed.
4. **Root cause, not symptom.** When human feedback indicates dissatisfaction, the system traces back to the root cause (bad brief? wrong skill? wrong agent?) rather than patching the surface-level output.
5. **Human approval gates.** Agents are created, deleted, or modified only after human confirmation. The Orchestrator recommends; the human decides.
6. **The system self-heals.** Orchestrator periodically reads learnings logged by the PM and adjusts meta-prompts, skills, agent rosters, and even its own configuration to fix systemic issues.

---

## 1. Orchestrator

### 1.1 Role

The Orchestrator is the most intelligent agent in the system. It runs on the most capable (and typically most expensive) model available. Its job is to deliver highly polished outcomes to the human — and it is bound by an oath to not deliver poor quality.

### 1.2 Personality

The Orchestrator is:
- **Ruthlessly quality-driven.** It will not ship mediocre work. If the team can't deliver the standard, it restructures the team.
- **Intellectually honest.** It points out gaps and contradictions in the human's thinking, even when uncomfortable.
- **Transparent about iteration.** From the outset, it sets expectations: the first output may not match the human's vision, and feedback will be needed to improve.
- **Root-cause oriented.** When feedback arrives, it traces deviations to their source — not the surface symptom. A wrong button color may indicate a flawed design system, not a bad color choice.

### 1.3 Scope

The Orchestrator is responsible for:

1. **Project creation and decomposition.** Taking a human brief and decomposing it into atomic tasks with dependency chains, eval briefs, and assignments.
2. **Agent architecture.** Creating worker-agents, assigning skills to them, and recommending models and configuration to the human for approval.
3. **Root-cause analysis.** When the PM escalates human feedback, the Orchestrator identifies what part of the task chain deviated from the human's intent and fixes the root cause.
4. **System healing.** Periodically reading PM learnings and adjusting: meta-prompts of worker agents, adding/removing skills, changing its own model or personality, deleting old agents, creating new ones.
5. **Research spawning.** When the Orchestrator identifies a knowledge gap, it can spawn a researcher agent (scoped to the project) to discover more, then use that feedback to refine the plan or alert the human to simpler/better alternatives.

### 1.4 Invocation Model

The Orchestrator is **not continuously running.** It is invoked on:

- **Project creation** — human submits brief, Orchestrator decomposes.
- **PM escalation** — PM encounters an issue it cannot resolve (stuck task, ambiguous feedback, agent failure, circular dependency).
- **Healing cycle** — triggered at a user-configurable frequency (default: once per day). Orchestrator reviews PM learnings and heals the system.
- **Direct human request** — human can explicitly invoke the Orchestrator via chat, bypassing the PM.

Between invocations, the Orchestrator is dormant. All ongoing project operations are handled by the PM.

### 1.5 Constraints

- **Cannot create, delete, or modify agents without human approval.** The Orchestrator recommends; the human confirms.
- **Cannot directly message the human.** All communication flows through the PM, unless the human explicitly opens a direct channel.
- **Cannot modify tasks after creation without PM escalation.** If a task needs to change mid-flight, the PM escalates and the Orchestrator decides.
- **Must log all decisions and reasoning.** Every decomposition, agent creation, healing action, and root-cause analysis is logged for audit and learning.

### 1.6 Healing Cycle

The healing cycle is the Orchestrator's self-correction mechanism:

1. PM logs learnings continuously (human feedback, eval results, task failures, agent issues).
2. At the configured frequency, the Orchestrator reads all new learnings since the last healing cycle.
3. The Orchestrator identifies systemic issues: repeated failures in a specific agent type, consistent human dissatisfaction with a specific output category, skills that are never used, etc.
4. The Orchestrator proposes changes: modify meta-prompts, add/remove skills from agents, change agent models, delete underperforming agents, create new agents with different configurations.
5. All proposed changes are sent to the PM for human approval.
6. Once approved, the PM executes the changes.

Healing does NOT modify in-flight tasks. It adjusts the system for future work.

---

## 2. Project Manager (PM)

### 2.1 Role

The Project Manager is the operational backbone of every Relay project. It runs on a cheaper model than the Orchestrator — it handles tactical, continuous work that doesn't require deep reasoning. Its job is to keep everything moving, keep the human informed, and escalate when it can't resolve something on its own.

### 2.2 Personality

The PM is:
- **Diligent and persistent.** It doesn't let things stall. It follows up, checks in, and keeps the ball moving.
- **Transparent.** The human always knows the state of the project. The PM proactively sends status updates.
- **Escalation-happy.** When in doubt, the PM escalates to the Orchestrator rather than guessing. It knows its limits.

### 2.3 Scope

The PM is responsible for:

1. **Continuous monitoring.** Tracking task progress, agent health, and project status.
2. **Human communication.** All project updates, questions, and approval requests go through the PM to the human.
3. **Eval execution.** Running evals on completed tasks using the eval briefs created by the Orchestrator.
4. **Stale task detection.** Identifying tasks that haven't moved, agents that have stopped responding, or dependencies that are blocking progress.
5. **Circular dependency detection.** Flagging when tasks form a dependency loop.
6. **Learning logging.** Recording all human feedback, eval results, agent issues, and task failures as structured learnings for the Orchestrator's healing cycle.
7. **Orchestrator relay.** Passing human feedback, escalation requests, and healing inputs to the Orchestrator. Passing Orchestrator recommendations back to the human for approval.
8. **Agent health checks.** Monitoring whether worker agents are operational and responsive. If an agent goes silent unexpectedly, the PM escalates to the Orchestrator.

### 2.4 Interaction Model

The PM is **continuously running** for the duration of a project. It:

- Checks project status at a configurable interval (default: every 10 minutes).
- Sends the human a digest update at a configurable frequency (default: every 4 hours, or immediately on blockers).
- Escalates to the Orchestrator when: a task is stuck for 30+ minutes, an agent is unresponsive, human feedback requires root-cause analysis, or a systemic issue is detected.
- Executes approved changes from the Orchestrator (agent creation/deletion, skill changes, meta-prompt updates).

### 2.5 Constraints

- **Cannot modify the project plan.** The PM does not add, remove, or restructure tasks. That is the Orchestrator's job.
- **Cannot create or delete agents.** Only the Orchestrator can recommend that.
- **Cannot change agent configuration (model, skills, meta-prompts).** It executes approved changes from the Orchestrator but does not originate them.
- **Must log all interactions and decisions.** For audit and for the Orchestrator's healing cycle.

---

## 3. Orchestrator–PM Interaction Protocol

### 3.1 Communication Flow

```
Human ←→ PM ←→ Orchestrator
                  ↕
            Worker Agents
```

- **Human → PM:** Feedback, questions, approval responses
- **PM → Human:** Status updates, approval requests, eval results
- **PM → Orchestrator:** Escalations (stuck tasks, feedback requiring root-cause analysis, agent failures)
- **Orchestrator → PM:** Recommendations (agent changes, task restructuring, healing actions)
- **Orchestrator → Worker Agents:** (only via PM) New assignments, meta-prompt updates, skill changes

### 3.2 Escalation Triggers

The PM escalates to the Orchestrator when:

1. A task is stuck for 30+ minutes with no progress.
2. An agent is unresponsive for 15+ minutes.
3. Human feedback expresses dissatisfaction (the PM cannot determine root cause).
4. A circular dependency is detected.
5. Multiple evals fail on tasks from the same agent.
6. The PM cannot determine the correct next action.

### 3.3 Healing Cycle Flow

```
1. PM logs learnings (continuous)
2. Healing trigger fires (scheduled or manual)
3. Orchestrator reads learnings since last cycle
4. Orchestrator identifies systemic issues
5. Orchestrator proposes changes
6. PM sends changes to human for approval
7. Human approves/rejects
8. PM executes approved changes
9. PM logs healing results as new learnings
```

---

## 4. Worker Agents (Outline)

Worker agents are created by the Orchestrator per-project. This section outlines the shape; full specification will be in a future spec.

### 4.1 Types

- **Executor agents** — do the work (code, design, write, etc.)
- **Researcher agents** — investigate and discover (spawned per-project as needed, not permanent)
- **Evaluator agents** — assess quality against eval briefs

### 4.2 Lifecycle

1. Orchestrator identifies a need for a new agent (skill gap, capacity need).
2. Orchestrator defines: agent type, required skills, recommended model, meta-prompt.
3. PM sends the proposal to the human for approval.
4. On approval, PM creates the agent in Relay.
5. Agent operates within its defined scope.
6. On healing cycle, Orchestrator may recommend modifying or deleting the agent.

---

## 5. v0.2 Tasks Moving to v0.3

The following v0.2 tasks are deferred to v0.3 because they depend on the Orchestrator/PM architecture:

- **Build Relay-native orchestrator agent** (v0.2 #30) — now fully specified here, implementation is v0.3 scope.
- **Build project creation UI with Start Orchestration CTA** (v0.2 #29) — the UI depends on the Orchestrator API, which is defined in v0.3.

---

## 6. Open Questions

- Orchestrator model selection: should the system auto-select the best available model, or should the human configure it?
- PM model selection: same question. Default to a capable but cheaper model?
- Healing cycle: what is the maximum frequency the human can set? Minimum?
- Researcher agent: should it have access to the internet, or only to provided knowledge bases?
- When the Orchestrator is dormant, does it retain state across invocations, or does it reconstruct context from the project wiki and PM logs each time?
