# Agent Collaboration Protocol

Agent Collaboration Protocol (ACP) is a vendor-neutral file protocol for AI
agents that collaborate through a shared filesystem instead of direct messages.

ACP schema v2 is deliverable-aware. A completed run must include a declared
Markdown primary deliverable, deliverable lifecycle events, a SHA-256 freeze
snapshot, readiness gates, and a final `conclusion.md` receipt. Old
non-deliverable ACP folders are not supported by this schema.

## Install for an Agent

Preferred install:

```bash
npx skills add benjinus/agent-collaboration-protocol
```

Manual fallback:

```bash
git clone https://github.com/benjinus/agent-collaboration-protocol.git
```

Copy the cloned folder into your agent's skill or instruction directory, or
point the agent at `SKILL.md`.

## What It Creates

An internal-mode ACP folder contains:

```text
<collaboration-folder>/
├── protocol.json
├── events.jsonl
├── proposal.md
├── review.md
├── decisions.md
├── readiness.md
├── conclusion.md
└── deliverables/
    └── <primary>.md
```

Protocol files stay at the collaboration root. Deliverable artifacts live under
`deliverables/`. `conclusion.md` is the final protocol receipt, not the primary
deliverable.

## Start A Collaboration

```bash
python3 scripts/init_collaboration.py \
  --folder <collaboration-folder> \
  --participant <participant-a> \
  --participant <participant-b> \
  --objective "<one concrete decision or deliverable>" \
  --primary-deliverable-type design-spec \
  --completion "<objective gate>" \
  --completion "<another objective gate>"
```

Built-in primary deliverable types:

- `adr`
- `design-spec`
- `implementation-plan`
- `decision-memo`
- `review-report`
- `test-plan`

Use `custom` only with `--primary-deliverable-file` and one or more
`--primary-deliverable-check` values.

For external deliverables:

```bash
python3 scripts/init_collaboration.py \
  --folder <repo>/.acp/<run> \
  --participant <participant-a> \
  --participant <participant-b> \
  --objective "<objective>" \
  --primary-deliverable-type adr \
  --deliverables-mode external \
  --repo-root ../.. \
  --deliverables-dir docs/architecture \
  --completion "<objective gate>"
```

External mode stores artifacts under the repo-root-relative deliverables dir and
uses `external:<file>` references in events, readiness, and conclusion.

## Event Workflow

Allowed events:

- `initialized`
- `deliverable_drafted`
- `deliverable_revised`
- `deliverable_frozen`
- `proposal_submitted`
- `review_submitted`
- `proposal_revised`
- `question_classified`
- `decision_proposed`
- `decision_accepted`
- `readiness_passed`
- `completed`
- `blocked`

All events after `initialized` require `reply_to`. All `deliverable_*` events
require `doc` and `role`. `deliverable_frozen` also requires a top-level
`sha256` field.

Phases remain:

- `drafting`
- `reviewing`
- `revising`
- `decision_review`
- `readiness_check`
- `completed`
- `blocked`

## Participant Run Loop

When no native watcher exists:

```bash
python3 scripts/wait_for_turn.py \
  --folder <collaboration-folder> \
  --participant <participant-id>
```

Then inspect the next action:

```bash
python3 scripts/next_action.py \
  --folder <collaboration-folder> \
  --participant <participant-id>
```

Perform only the allowed action, append the required event, and loop until the
phase is `completed` or `blocked`.

## Readiness Gate

Before `readiness_passed` or `completed`, `readiness.md` must show:

- Open questions are resolved, deferred with reasons, or blocking.
- No blocking or unresolved questions remain.
- Objective gates are checked.
- Generated deliverable gates are checked.
- The primary deliverable has `Status: Frozen`.
- The primary deliverable SHA-256 snapshot is recorded.
- `Ready to implement` is checked.

Decision acceptance is invalid while unresolved or blocking readiness items
remain.

## Final Conclusion

`conclusion.md` is a final receipt. It must state the outcome
(`[proceed]`, `[do_not_proceed]`, or `[defer]`), rationale, deliverable receipt,
accepted decisions summary, readiness result, assumptions, deferred follow-ups,
implementation blockers, and next action.

`blocked` is a phase/event, not a completable outcome.

## Validate

```bash
python3 scripts/validate_collaboration.py --folder <collaboration-folder>
```

Exit codes:

- `0`: validation passed.
- `1`: validation passed with warnings.
- `2`: validation failed.

## License

MIT. See `LICENSE`.
