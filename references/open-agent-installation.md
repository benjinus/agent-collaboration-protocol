# Open Agent Installation

This skill defines a vendor-neutral file protocol. Native skill packaging is
allowed, but no participant may depend on a vendor-specific mechanism for the
collaboration state.

## Portable Contract

An agent runtime is compatible when it can:

- Read local Markdown instructions.
- Create and read files in a shared folder.
- Append compact JSON objects to `state.log`.
- Write Markdown entries to `opinions.md`.
- Optionally watch or poll `state.log` for new lines.

The canonical behavior is in `SKILL.md`. The helper script
`scripts/init_collaboration.py` is optional but recommended.

## Installation Patterns

Codex:

- Place this folder under a Codex skill root, such as `~/.codex/skills/`.
- Use the skill by asking Codex to set up or participate in the file
  collaboration protocol.

Claude Code:

- Install the folder wherever Claude Code can read project or user-level custom
  instructions.
- Point Claude Code at `SKILL.md` as the instruction source.
- If native skill folders are supported in the local Claude Code version, use
  that native skill location and keep this folder intact.

OpenCode:

- Install the folder under the workspace or user instruction area used by the
  local OpenCode setup.
- Configure the agent prompt or command to load `SKILL.md` before participating.

Kiro:

- Install the folder under the project or user-level agent instruction area used
  by the local Kiro setup.
- Configure the agent/spec workflow to load `SKILL.md` and use the shared
  collaboration folder as the durable state source.

Other agents:

- Copy or reference `SKILL.md`.
- Ensure the runtime can execute or replicate `scripts/init_collaboration.py`.
- Do not translate the protocol into a private state format unless it still
  reads and writes the same shared files.

## Minimum Manual Setup

When no native skill mechanism exists, give the agent this instruction:

```text
Use the Agent Collaboration Protocol from <path>/SKILL.md. Your participant_id
is <id>. The collaboration folder is <folder>. The objective is <objective>. The
completion conditions are <conditions>. Read state.log, discussion.md, and
opinions.md; process only events from other participants; append your response
using the protocol format.
```

This is enough for any capable file-writing agent to participate.
