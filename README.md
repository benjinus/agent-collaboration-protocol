# Agent Collaboration Protocol

A vendor-neutral file protocol for AI agents that need to collaborate through a
shared filesystem instead of direct messages.

The protocol uses a small state machine, structured events, readiness gates, and
validator checks. Agents must not complete a collaboration only because both
sides accepted text; they must classify open questions, clear blockers, pass
readiness, write a final conclusion, and then complete.

The protocol is turn-owned. After the initiator submits a proposal, the
initiator waits; only the listed reviewer can advance the review phase. The
initiator may poll or block on timeout, but must not keep editing shared
documents while the review is pending.

## Install for an Agent

Preferred install:

```bash
npx skills add benjinus/agent-collaboration-protocol
```

The `skills` CLI detects supported agents and installs the skill into the
selected agent locations.

Manual fallback when the CLI is not available:

```bash
git clone https://github.com/benjinus/agent-collaboration-protocol.git
```

Copy the cloned folder into your agent's skill or instruction directory, or
point the agent at `SKILL.md` inside the cloned repository.

## What It Creates

An ACP collaboration folder contains:

- `protocol.json`: objective, participants, completion gates, and current phase.
- `events.jsonl`: append-only structured event log. `seq` values must be
  continuous.
- `proposal.md`: the current proposal only.
- `review.md`: structured reviews. Each review heading must use the matching
  `review_submitted` event seq.
- `decisions.md`: accepted decisions only.
- `readiness.md`: open question classification, blockers, deferred
  nonblocking items, and final implementation readiness.
- `conclusion.md`: the final answer to the collaboration objective: whether to
  proceed, not proceed, or defer; why; how to implement or why not; and the next
  action.

No extra state files are part of the protocol. Keep one source of truth for
collaboration state.

## Start A Collaboration

Use this prompt to start a collaboration from any agent that has this protocol
installed or can read this repository:

```text
Use Agent Collaboration Protocol to start a file-based collaboration.

Collaboration folder:
<absolute-or-repo-relative-folder>

Participants:
- <participant-a>
- <participant-b>

Current participant:
<participant-a>

Objective:
<one concrete decision or deliverable>

Completion gates:
- <gate that proves the accepted decisions are explicit>
- <gate that proves readiness passed with no blockers>
- <gate that proves every participant completed>
```

## Event Workflow

Allowed events:

- `initialized`
- `proposal_submitted`
- `review_submitted`
- `proposal_revised`
- `question_classified`
- `decision_proposed`
- `decision_accepted`
- `readiness_passed`
- `completed`
- `blocked`

Phases:

- `drafting`: proposal is being prepared.
- `reviewing`: another participant must review.
- `revising`: proposal owner addresses review.
- `decision_review`: open questions are classified, then participants accept
  explicit decisions.
- `readiness_check`: questions are classified and blockers cleared.
- `completed`: collaboration is done.
- `blocked`: collaboration cannot proceed.

## Readiness Gate

Before `readiness_passed` or `completed`, `readiness.md` must show:

- Every open question is marked `[resolved]`, `[deferred_nonblocking]`, or
  `[blocking]`.
- Every `[deferred_nonblocking]` item includes `Reason: ...`.
- No `[blocking]` or `[unresolved]` item remains.
- The checklist item `Ready to implement` is checked.

The same question classification must happen before participants accept
decisions. Acceptance is not valid while unresolved or blocking questions
remain.

## Final Conclusion

After readiness passes, the collaboration must produce `conclusion.md`. It is
the decision document a user can act on: do the feature, do not do it, or defer
it; the rationale; accepted decisions; implementation approach; assumptions;
follow-ups; blockers; and the next action.

## License

MIT. See `LICENSE`.
