# Agent Collaboration Protocol

A vendor-neutral file protocol for AI agents that need to collaborate through a
shared filesystem instead of direct messages.

The protocol uses a small state machine, structured events, readiness gates, and validator
checks. Agents must not complete a collaboration only because both sides
accepted text; they must classify open questions, clear blockers, pass readiness,
and then complete.

## What It Creates

An ACP collaboration folder contains:

- `protocol.json`: objective, participants, completion gates,
  and current phase.
- `events.jsonl`: append-only structured event log. `seq` values must be
  continuous.
- `proposal.md`: the current proposal only.
- `review.md`: structured reviews. Each review heading must use the matching
  `review_submitted` event seq.
- `decisions.md`: accepted decisions only.
- `readiness.md`: open question classification, blockers, deferred
  nonblocking items, and final implementation readiness.

## Initialize

```bash
python3 scripts/init_collaboration.py \
  --folder /path/to/shared-collaboration \
  --participant server \
  --participant reader \
  --objective "Align the reader collaboration architecture" \
  --completion "Accepted decisions are explicit" \
  --completion "Readiness passes with no blockers" \
  --completion "Both participants write completed events"
```

Initialization uses the current protocol structure:

- Re-running initialization fails when `protocol.json` already exists unless
  `--resume` is provided.
- Current protocol folders should use the scripts below instead of hand-writing events.

## Event Workflow

Append events with the portable helper:

```bash
python3 scripts/append_event.py \
  --folder /path/to/shared-collaboration \
  --participant server \
  --event proposal_submitted \
  --summary "Initial proposal ready for review" \
  --doc proposal.md \
  --reply-to 1
```

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
- `decision_review`: participants accept explicit decisions.
- `readiness_check`: questions are classified and blockers cleared.
- `completed`: collaboration is done.
- `blocked`: collaboration cannot proceed.

Use `next_action.py` when no runtime-specific watcher exists:

```bash
python3 scripts/next_action.py \
  --folder /path/to/shared-collaboration \
  --participant reader
```

## Readiness Gate

Before `readiness_passed` or `completed`, `readiness.md` must show:

- Every open question is marked `[resolved]`, `[deferred_nonblocking]`, or
  `[blocking]`.
- Every `[deferred_nonblocking]` item includes `Reason: ...`.
- No `[blocking]` or `[unresolved]` item remains.
- The checklist item `Ready to implement` is checked.

Validate before passing readiness and before completing:

```bash
python3 scripts/validate_collaboration.py --folder /path/to/shared-collaboration
```

Exit codes:

- `0`: valid.
- `1`: valid with warnings.
- `2`: invalid.

## Install for an Agent

Codex example:

```bash
mkdir -p ~/.codex/skills
cp -R agent-collaboration-protocol ~/.codex/skills/agent-collaboration-protocol
```

For Claude Code, OpenCode, Kiro, or another file-capable assistant, install this
folder in that runtime's local skill or instruction area, or point the agent at
`SKILL.md`.

## Project Layout

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/open-agent-installation.md
├── scripts/
│   ├── _acp.py
│   ├── append_event.py
│   ├── init_collaboration.py
│   ├── next_action.py
│   └── validate_collaboration.py
└── tests/
    └── test_collaboration_scripts.py
```

## License

MIT. See `LICENSE`.
