---
name: file-collaboration-protocol
description: Use when coordinating multiple agents, teams, repos, or users through a shared filesystem folder and append-only files. Supports asynchronous plan discussion, handoff, proposal review, cross-agent negotiation, status signaling, and explicit collaboration exit conditions. Requires a collaboration folder plus a stated objective and completion conditions before starting.
---

# File Collaboration Protocol

Use a shared folder as a small coordination bus for agents that cannot directly
message each other. The protocol is append-only except for the shared discussion
document, which may be edited by participants.

## Required Inputs

Before starting a collaboration, require:

- `collaboration_folder`: an absolute or repo-relative folder path shared by all participants.
- `objective`: what the collaboration is trying to decide or produce.
- `completion_conditions`: concrete conditions for ending the collaboration.
- `participant_id`: the current agent identity, such as `server`, `reader`, `frontend`, `reviewer`, or `agent-a`.

If any required input is missing, ask for it before creating files or writing
state. Do not invent completion conditions.

## Files

Create or use these files in the collaboration folder:

- `README.md`: purpose, participants, file contract, completion conditions.
- `state.log`: append-only JSONL state events.
- `discussion.md`: shared proposal/design document.
- `opinions.md`: append-only structured opinions and responses.

Optional files:

- `decisions.md`: durable accepted decisions if the collaboration becomes long.
- `archive/`: completed rounds or older drafts.

## Initialization

Prefer the bundled script:

```bash
python3 <skill>/scripts/init_collaboration.py \
  --folder <collaboration_folder> \
  --participant <participant_id> \
  --objective "<objective>" \
  --completion "<completion condition>" \
  --completion "<another condition>"
```

The script is idempotent: it creates missing files and appends a
`collaboration-started` event. It refuses to start without objective and at
least one completion condition.

## State Log Protocol

`state.log` is JSONL. Append one compact JSON object per line. Never edit or
delete previous lines.

Required fields:

- `seq`: monotonically increasing integer in that file.
- `from`: participant id.
- `event`: event name.
- `at`: ISO-8601 UTC timestamp.

Recommended fields:

- `doc`: path relative to collaboration folder.
- `summary`: one short sentence.
- `reply_to`: prior `seq` when responding to an event.

Allowed event names:

- `collaboration-started`
- `proposal-updated`
- `opinion-written`
- `decision-proposed`
- `decision-accepted`
- `question-raised`
- `blocked`
- `waiting`
- `completed`

Processing rule:

- Process only events where `from != participant_id`.
- Track the last processed `seq`.
- Ignore duplicate or already processed events.
- After writing an opinion, append `opinion-written`, then append `waiting`.

## Opinion Format

Append to `opinions.md` using this exact shape:

```markdown
## <ISO-8601 UTC> - <participant_id> - seq <state_seq>

Context:
- Read `<discussion.md>` after `<other participant>` event seq `<seq>`.

Position:
- ...

Concerns:
- ...

Suggested Changes:
- ...

Open Questions:
- ...
```

Keep each section. Write `- None.` if a section has no content. Do not rewrite
another participant's opinion.

## Shared Discussion Document

Use `discussion.md` for the current proposal. Keep it easy to merge:

- Purpose
- Current Proposal
- Message/API Contracts
- Operational Concerns
- Open Questions
- Proposed Decisions

Do not hide unresolved disagreement by editing it away. Move accepted decisions
to a `Decisions` section or `decisions.md`.

## Watcher Pattern

If using a subagent or background watcher, keep it dumb:

- It watches `state.log` for new lines.
- It notifies the main agent when a relevant `from != participant_id` event appears.
- It does not analyze the proposal or write opinions.

The main agent reads `discussion.md`, writes `opinions.md`, and appends state
events. This keeps judgment in the main conversation context.

## Completion

End collaboration only when a completion condition is met. Append:

```json
{"seq":N,"from":"<participant_id>","event":"completed","at":"<UTC>","summary":"<condition met>"}
```

Then stop watching unless the user explicitly asks to reopen the collaboration.
