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
- Execute the Python standard-library scripts in `scripts/`, or exactly
  reproduce their behavior.
- Poll with `next_action.py` when no native watcher exists.
- Run `validate_collaboration.py` before readiness and completion events.

The canonical behavior is in `SKILL.md`. The helper scripts are part of the protocol contract, not just examples.

## Installation Patterns

Codex:

- Place this folder under a Codex skill root, such as `~/.codex/skills/`.
- Use the skill by asking Codex to set up or participate in ACP.

Claude Code:

- Install the folder wherever Claude Code can read project or user-level custom
  instructions.
- Point Claude Code at `SKILL.md` as the instruction source.
- Ensure the runtime can run the bundled scripts or reproduce their behavior.

OpenCode:

- Install the folder under the workspace or user instruction area used by the
  local OpenCode setup.
- Configure the agent prompt or command to load `SKILL.md` before
  participating.

Kiro:

- Install the folder under the project or user-level agent instruction area used
  by the local Kiro setup.
- Configure the agent/spec workflow to load `SKILL.md` and use the shared
  collaboration folder as the durable state source.

Other agents:

- Copy or reference `SKILL.md`.
- Ensure the runtime can execute or reproduce `init_collaboration.py`,
  `append_event.py`, `next_action.py`, and `validate_collaboration.py`.
- Do not translate the protocol into a private state format unless it still
  reads and writes the same shared files.

## Minimum Manual Setup

When no native skill mechanism exists, give the agent this instruction:

```text
Use Agent Collaboration Protocol from <path>/SKILL.md. Your participant_id
is <id>. The collaboration folder is <folder>. The objective is <objective>.
The participants are <participants>. The completion gates are <gates>. Read
protocol.json, events.jsonl, proposal.md, review.md, decisions.md, and
readiness.md. Use append_event.py or exactly reproduce its event behavior. Use
next_action.py when no watcher exists. Run validate_collaboration.py before
readiness_passed and completed.
```

This is the minimum needed for any capable file-writing agent to participate.
