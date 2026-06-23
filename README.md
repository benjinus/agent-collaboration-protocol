# Agent Collaboration Protocol

A reusable file-based collaboration protocol for AI agents that cannot directly
message each other.

The project is also a Codex-compatible skill. Install it as a skill, or use the
protocol files and initialization script directly in any agent workflow.

## What It Does

The protocol creates a shared workspace folder where agents coordinate through
plain files:

- `README.md`: objective, participants, rules, and completion conditions.
- `state.log`: append-only JSONL events.
- `discussion.md`: shared proposal or design document.
- `opinions.md`: append-only structured opinions and responses.

The important rule is simple: agents use `state.log` to signal changes, read
`discussion.md` for the current proposal, append their response to `opinions.md`,
then append another state event when they are waiting for the next participant.

## Install as a Codex Skill

Copy this folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R agent-collaboration-protocol ~/.codex/skills/file-collaboration-protocol
```

Then ask Codex to use the `file-collaboration-protocol` skill for a shared
folder collaboration.

## Initialize a Collaboration Folder

```bash
python3 scripts/init_collaboration.py \
  --folder /path/to/shared-collaboration \
  --participant server \
  --objective "Align the reader collaboration architecture" \
  --completion "A shared proposal is accepted by both sides" \
  --completion "Both participants write completed events"
```

The script refuses to start without an objective and at least one completion
condition. This is intentional: participants need to know when to stop.

## State Log Example

Each line in `state.log` is one compact JSON event:

```json
{"seq":1,"from":"server","event":"collaboration-started","at":"2026-06-23T10:00:00Z","summary":"Collaboration workspace initialized","doc":"discussion.md"}
{"seq":2,"from":"reader","event":"proposal-updated","at":"2026-06-23T10:05:00Z","summary":"Reader endpoint proposal added","doc":"discussion.md"}
{"seq":3,"from":"server","event":"opinion-written","at":"2026-06-23T10:08:00Z","summary":"Server concerns added","doc":"opinions.md","reply_to":2}
```

Agents should process only events where `from` is not their own participant id.

## Opinion Format

Append entries to `opinions.md` in this format:

```markdown
## 2026-06-23T10:08:00Z - server - seq 3

Context:
- Read `discussion.md` after reader event seq 2.

Position:
- ...

Concerns:
- ...

Suggested Changes:
- ...

Open Questions:
- ...
```

## Project Layout

```text
.
├── SKILL.md
├── agents/openai.yaml
├── scripts/init_collaboration.py
└── README.md
```

## License

No license has been added yet. Add a license before publishing this repository
for public reuse.
