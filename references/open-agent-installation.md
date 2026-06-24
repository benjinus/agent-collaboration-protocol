# Open Agent Installation

ACP defines a vendor-neutral file protocol and a small portable script
toolchain. Native skill packaging is allowed, but no participant may depend on a
vendor-specific mechanism for the collaboration state.

## Portable Contract

An agent runtime is compatible when it can:

- Read local Markdown and JSON instructions.
- Create and read files in a shared folder.
- Append compact JSON objects to `events.jsonl`.
- Write Markdown entries to `proposal.md`, `review.md`, `decisions.md`, and
  `readiness.md`.
- Write `conclusion.md` as the final actionable conclusion before completion.
- Execute the Python standard-library scripts in `scripts/`, or exactly
  reproduce their behavior.
- Poll with `next_action.py` when no native watcher exists.
- Run `validate_collaboration.py` before readiness and completion events.
- Preserve turn ownership from `protocol.json.waitingFor`; participants not
  listed there must wait instead of advancing the phase.
- Treat `events.jsonl` as append-only. Do not rewrite earlier events to fix a
  sequence, phase, or timestamp mistake.

The canonical behavior is in `SKILL.md`. The helper scripts are part of the protocol contract, not just examples.

## Installation Pattern

Preferred installer:

```bash
npx skills add benjinus/agent-collaboration-protocol
```

The `skills` CLI detects supported agents and installs the skill into the
selected agent locations.

Manual fallback:

- Clone `https://github.com/benjinus/agent-collaboration-protocol.git`.
- Copy the cloned folder into the runtime's skill or instruction directory, or
  reference `SKILL.md` from the cloned folder.
- Ensure the runtime can execute or reproduce `init_collaboration.py`,
  `append_event.py`, `next_action.py`, and `validate_collaboration.py`.
- Do not translate the protocol into a private state format unless it still
  reads and writes the same shared files.
- Do not create compatibility files such as `state.log`, `discussion.md`, or
  `opinions.md`.
- Do not mark completion unless `conclusion.md` states the final outcome,
  rationale, implementation approach, and next action.

## Minimum Manual Setup

When no native skill mechanism exists, give the agent this instruction:

```text
Use Agent Collaboration Protocol from <path>/SKILL.md. Your participant_id
is <id>. The collaboration folder is <folder>. The objective is <objective>.
The participants are <participants>. The completion gates are <gates>. Read
protocol.json, events.jsonl, proposal.md, review.md, decisions.md, and
readiness.md. Write conclusion.md before completion. Use append_event.py or
exactly reproduce its event behavior. Use next_action.py when no watcher exists.
Run validate_collaboration.py before readiness_passed and completed. Respect
protocol.json.waitingFor; if your participant id is not listed there, wait
instead of editing shared state.
```

This is the minimum needed for any capable file-writing agent to participate.
