# Agent Collaboration Protocol

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

Install the skill with your agent's skill manager, or clone this repository and
point the agent at `SKILL.md`.

## License

MIT. See `LICENSE`.
