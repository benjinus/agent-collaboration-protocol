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
- Poll with `next_action.py` and block with `wait_for_turn.py` when no native
  watcher exists.
- Run `validate_collaboration.py` before readiness and completion events.
- Preserve turn ownership from `protocol.json.waitingFor`; participants not
  listed there must wait instead of advancing the phase.
- Treat `events.jsonl` as append-only. Do not rewrite earlier events to fix a
  sequence, phase, or timestamp mistake.
- Keep running the wait/action loop until `completed`, `blocked`, or an
  explicit coordinator deadline. Do not stop after a single event if the
  collaboration is still active.

The canonical behavior is in `SKILL.md`. The helper scripts are part of the protocol contract, not just examples.

## Installation Pattern

Preferred installer:

```bash
npx skills add agi-connect/agent-collaboration-protocol
```

The `skills` CLI detects supported agents and installs the skill into the
selected agent locations.

Manual fallback:

- Clone `https://github.com/agi-connect/agent-collaboration-protocol.git`.
- Copy the cloned folder into the runtime's skill or instruction directory, or
  reference `SKILL.md` from the cloned folder.
- Ensure the runtime can execute or reproduce `init_collaboration.py`,
  `append_event.py`, `next_action.py`, `wait_for_turn.py`, and
  `validate_collaboration.py`.
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
Use wait_for_turn.py to block until it is your turn or the phase is terminal;
the default wait timeout is 30 minutes, and --timeout 0 means no timeout only
when an external supervisor owns cancellation. Run validate_collaboration.py
before readiness_passed and completed. Respect protocol.json.waitingFor; if
your participant id is not listed there, wait instead of editing shared state.
After each event, repeat the wait/action loop until completed or blocked.
```

This is the minimum needed for any capable file-writing agent to participate.
