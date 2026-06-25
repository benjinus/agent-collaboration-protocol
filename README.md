# Agent Collaboration Protocol

![License](https://img.shields.io/github/license/agi-connect/agent-collaboration-protocol)
![Skill](https://img.shields.io/badge/skill-agent--collaboration--protocol-blue)
![Deliverables](https://img.shields.io/badge/deliverables-Markdown-1f6feb)
![AI Collaboration](https://img.shields.io/badge/AI-collaboration-7c3aed)

[中文](README.zh-CN.md)

Agent Collaboration Protocol (ACP) helps AI agents work together when they
share a workspace but cannot rely on a single conversation thread.

ACP is designed for collaborations where agents need to make a concrete
decision, review each other's work, resolve open questions, and leave behind a
clear deliverable that a human or another agent can use later.

## Collaboration Scenario

ACP supports a structured exchange between agents:

- One agent starts the collaboration with an objective, participants, and the
  expected deliverable.
- The owner drafts a proposal and the primary deliverable.
- Other participants review the proposal and deliverable from their own roles.
- The owner revises the work, records accepted decisions, and resolves open
  questions.
- Participants confirm whether the result is ready to use.
- The collaboration ends with a stable deliverable and a short final receipt.

This process is useful for architecture decisions, implementation planning,
design reviews, test planning, handoffs between coding agents, and any workflow
where agents need more discipline than a free-form chat transcript.

ACP keeps the collaboration focused on observable artifacts instead of hidden
conversation memory. Each participant can understand what has been proposed,
what has been reviewed, what has been accepted, and what remains blocked.

## Deliverables

Every completed ACP collaboration produces a primary Markdown deliverable.
Supported deliverable types include:

- Architecture decision records
- Design specifications
- Implementation plans
- Decision memos
- Review reports
- Test plans
- Custom Markdown deliverables

The final receipt is separate from the primary deliverable. It summarizes the
outcome, accepted decisions, readiness result, assumptions, blockers, and next
action.

## Install for an Agent

The recommended installation method is `npx skills add`:

```bash
npx skills add agi-connect/agent-collaboration-protocol
```

This installs the skill into the local skills directory used by compatible
agents.

If your agent does not support `skills add`, clone the repository manually:

```bash
git clone https://github.com/agi-connect/agent-collaboration-protocol.git
```

Then point your agent at the repository's `SKILL.md`, or copy the repository
into the skill or instruction directory your agent reads from.

## Use the Skill

ACP works best when each agent is given an explicit role in the collaboration.
One agent should act as the initiator, and the other agents should join as
participants.

As the initiator, ask your agent to start an ACP collaboration. Provide:

- The shared collaboration location.
- The collaboration objective.
- The participant names or roles.
- The expected primary deliverable type.
- The objective-specific completion criteria.

Use one of these deliverable types for `<deliverable-type>`:

- `adr` for an architecture decision record.
- `design-spec` for a design specification.
- `implementation-plan` for an implementation plan.
- `decision-memo` for a concise decision memo.
- `review-report` for a structured review report.
- `test-plan` for a test plan.
- `custom` for another Markdown deliverable agreed by the participants.

`<completion-criteria>` should describe the objective-specific conditions that
make the collaboration complete. Good criteria are observable and reviewable,
for example: "the design tradeoffs are documented", "the implementation phases
are actionable", or "all security review concerns have an accepted resolution".

Example initiator request:

```text
Use the agent-collaboration-protocol skill to start a collaboration in
<shared-folder>. I am the initiator. The participants are <participant-a> and
<participant-b>. The objective is <objective>. The primary deliverable should
be <deliverable-type>. The collaboration is complete when <completion-criteria>.
```

As a participant, ask your agent to join the existing ACP collaboration. Provide:

- The same shared collaboration location.
- The participant identity this agent should use.
- Any role-specific review responsibility.

`<role-or-responsibility>` should describe the perspective this participant is
responsible for during review. Use a concrete responsibility such as
"implementation feasibility", "security review", "API design", "test coverage",
"product requirements", or "documentation clarity".

Example participant request:

```text
Use the agent-collaboration-protocol skill to join the collaboration in
<shared-folder>. I am participating as <participant-a>. Review the current
proposal and deliverable from the perspective of <role-or-responsibility>.
```

The initiator is responsible for moving the collaboration toward a final
deliverable. Participants are responsible for reading the current state,
reviewing the proposal and deliverable, raising concerns, accepting decisions,
or identifying blockers when the work is not ready.

## License

MIT. See `LICENSE`.
