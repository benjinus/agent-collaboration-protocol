---
name: agent-collaboration-protocol
description: Use when coordinating multiple AI agents, coding assistants, teams, repos, or users through a vendor-neutral shared filesystem protocol. ACP schema v2 requires protocol.json, events.jsonl, proposal.md, review.md, decisions.md, readiness.md, conclusion.md, a declared Markdown primary deliverable under deliverables/, deliverable lifecycle events, strict phases, readiness gates, SHA-256 freeze checks, and validator checks.
---

# Agent Collaboration Protocol

ACP is a shared-folder coordination protocol for agents that cannot directly
message each other. It is a state machine with structured JSONL events,
turn ownership, readiness gates, and a frozen deliverable. It is not a loose
Markdown discussion.

Any compatible agent must be able to read and write Markdown/JSON, append JSONL
events, and run or exactly reproduce the bundled script behavior. Do not rely on
hidden thread state, vendor-specific APIs, or conversation memory for protocol
correctness.

## Required Inputs

Before starting, require:

- `collaboration_folder`: absolute or repo-relative shared folder path.
- `objective`: what the collaboration must decide or produce.
- `objective_gates`: objective-specific gates. The protocol generates
  deliverable gates automatically.
- `participants`: all participant ids, such as `server`, `reader`, `reviewer`,
  or `agent-a`.
- `participant_id`: the current agent identity.
- `primary_deliverable_type`: one of `adr`, `design-spec`,
  `implementation-plan`, `decision-memo`, `review-report`, `test-plan`, or
  `custom`.
- `primary_deliverable_file`: optional for built-in types, required for
  `custom`; must be Markdown.
- `primary_deliverable_checklist`: required for `custom`.
- `deliverables_mode`: optional, defaults to `internal`; `external` requires
  `repoRoot`.
- `deliverables_dir`: optional, defaults to `deliverables`.

If any required input is missing, ask before creating files or writing events.
Do not invent objective gates.

## Files

ACP schema v2 folders use these protocol files:

- `protocol.json`: `protocol: "acp"`, `schemaVersion: 2`, objective,
  participants, generated and objective gates, deliverable declaration, current
  phase, proposal owner, waiting participants, and timestamps.
- `events.jsonl`: append-only event log. Each line is one compact JSON object.
- `proposal.md`: current proposal/change summary.
- `review.md`: structured participant reviews.
- `decisions.md`: concise accepted decision index with stable IDs.
- `readiness.md`: open question classification, objective gates, generated
  deliverable gates, deliverable snapshot, blockers, and readiness result.
- `conclusion.md`: final protocol receipt. It is not the primary deliverable.
- `deliverables/`: actual Markdown deliverables and optional attachments.

Do not create or use `state.log`, `discussion.md`, or `opinions.md`. They are
not protocol files and must not appear in gates or instructions.

## Deliverables

ACP separates protocol state from deliverable artifacts:

- Every completable collaboration requires a declared primary Markdown
  deliverable.
- `conclusion.md` is the final receipt; it references the frozen deliverable and
  readiness result.
- Built-in deliverable types are `adr`, `design-spec`, `implementation-plan`,
  `decision-memo`, `review-report`, and `test-plan`.
- `custom` requires an explicit Markdown file and checklist.
- Supporting deliverables are Markdown. Attachments can be non-Markdown files
  under the deliverables directory.
- `internal` mode stores deliverables inside the collaboration folder.
- `external` mode stores deliverables in a repo-root-relative directory and uses
  `external:<file>` references in events, readiness, and conclusion.
- A deliverable must include `Status: Draft`, `Status: In Review`, or
  `Status: Frozen`.
- The proposal owner freezes the primary deliverable with
  `deliverable_frozen`; freeze is strict and has no unfreeze/refreeze path.

## Initialization

Prefer the bundled script:

```bash
python3 <skill>/scripts/init_collaboration.py \
  --folder <collaboration_folder> \
  --participant <participant_id> \
  --participant <other_participant_id> \
  --objective "<objective>" \
  --primary-deliverable-type design-spec \
  --completion "<objective gate>" \
  --completion "<another objective gate>"
```

For external deliverables:

```bash
python3 <skill>/scripts/init_collaboration.py \
  --folder <repo>/.acp/<run> \
  --participant <participant_id> \
  --participant <other_participant_id> \
  --objective "<objective>" \
  --primary-deliverable-type adr \
  --deliverables-mode external \
  --repo-root ../.. \
  --deliverables-dir docs/architecture \
  --completion "<objective gate>"
```

The initializer creates templates for protocol files and the primary
deliverable. It fails if `protocol.json` already exists unless `--resume` is
provided.

## Events

Use `scripts/append_event.py` or exactly reproduce its behavior. Required event
fields:

- `seq`: continuous integer in `events.jsonl`.
- `from`: participant id listed in `protocol.json`.
- `event`: allowed event name.
- `at`: ISO-8601 UTC timestamp.
- `summary`: one short sentence.

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

All events after `initialized` require `reply_to` pointing to an earlier event.
`doc` references are relative to the collaboration folder in internal mode, or
`external:<file>` in external mode.

All `deliverable_*` events require:

- `doc`: the resolved deliverable reference.
- `role`: `primary` or `supporting`.

`deliverable_frozen` also requires top-level `sha256`, a 64-character lowercase
hex SHA-256 of the referenced file. Once frozen, the file content must keep
matching the hash.

## Phases

Agents must act according to `protocol.json.currentPhase` and
`protocol.json.waitingFor`:

- `drafting`: proposal owner drafts the primary deliverable, appends
  `deliverable_drafted`, updates `proposal.md`, then appends
  `proposal_submitted`.
- `reviewing`: listed reviewers review both `proposal.md` and the primary
  deliverable, append structured reviews to `review.md`, then append
  `review_submitted`.
- `revising`: proposal owner updates `proposal.md` and deliverables as needed,
  appends `deliverable_revised` if a deliverable changed, then appends
  `proposal_revised`.
- `decision_review`: proposal owner classifies every open question in
  `readiness.md` and appends `question_classified`; participants then accept
  explicit `decisions.md` entries with `decision_accepted`.
- `readiness_check`: proposal owner freezes required deliverables, records
  snapshots in `readiness.md`, runs validation, then appends
  `readiness_passed`.
- `completed`: stop unless the user explicitly starts a new round.
- `blocked`: stop until the blocker is resolved or a new round starts.

`completed` is valid only after `readiness_passed` and must reference
`conclusion.md`.

## Review Format

Every `review_submitted` event must have a matching `review.md` heading whose
seq equals that event's `seq`:

```markdown
## <ISO-8601 UTC> - <participant_id> - seq <review_submitted event seq>

Context:
- Read `proposal.md` after event seq `<seq>`.
- Reviewed primary deliverable: `<resolved path>`
- Reviewed supporting deliverables: `<paths or none>`

Review Scope:
- Proposal coherence
- Primary deliverable completeness
- Accepted decision traceability
- Implementation readiness

Position:
- ...

Concerns:
- ...

Required Changes:
- ...

Questions:
- ...
```

## Decisions

`decisions.md` is an accepted decision index, not the deliverable. Every accepted
decision must use a stable ID:

```markdown
### D1. <short title>

- Decision: ...
- Rationale: ...
- Reflected in: `deliverables/design-spec.md#section`
```

IDs must be sequential (`D1`, `D2`, ...). `Reflected in:` must point to a
declared primary or supporting deliverable.

## Readiness Gate

Before `readiness_passed` or `completed`:

- Every open question is `[resolved]`, `[deferred_nonblocking]`, or
  `[blocking]`.
- Every `[deferred_nonblocking]` item includes `Reason: ...`.
- No `[blocking]` or `[unresolved]` item remains.
- Objective gates are checked.
- Generated deliverable gates are checked.
- The primary deliverable has `Status: Frozen`.
- The primary deliverable SHA-256 snapshot is recorded.
- `Ready to implement` is checked.
- `validate_collaboration.py` passes.

Blocking or unresolved readiness items also prevent `decision_accepted`.

## Final Conclusion

Before `completed`, write `conclusion.md` as a final receipt. It must include:

- Decision Outcome: exactly one of `[proceed]`, `[do_not_proceed]`, or
  `[defer]`.
- Rationale.
- Deliverable Receipt: primary path, type, SHA-256, supporting deliverables, and
  attachments.
- Accepted Decisions Summary.
- Readiness Result.
- Assumptions.
- Deferred Follow-ups.
- Implementation Blockers.
- Next Action.

`blocked` is a phase/event, not a completable outcome.

## Polling And Watchers

Participants must stay alive for the collaboration loop until the phase is
`completed`, `blocked`, or an explicit coordinator deadline is reached.

If there is no watcher, use:

```bash
python3 <skill>/scripts/next_action.py \
  --folder <collaboration_folder> \
  --participant <participant_id>
```

For autonomous participants, prefer:

```bash
python3 <skill>/scripts/wait_for_turn.py \
  --folder <collaboration_folder> \
  --participant <participant_id>
```

`wait_for_turn.py` returns when the participant is listed in `waitingFor`, or
when the collaboration becomes `completed` or `blocked`. It defaults to a
30-minute timeout; use `--timeout 0` only when an external supervisor owns
cancellation.

## Validation

Run:

```bash
python3 <skill>/scripts/validate_collaboration.py --folder <collaboration_folder>
```

The validator checks required protocol files, schema v2 fields, deliverable
declarations, path safety, event shape, deliverable roles and hashes, phase
transitions, review headings, decision IDs, readiness gates, frozen deliverable
content, conclusion receipt, and completion ordering.

Exit codes:

- `0`: validation passed.
- `1`: validation passed with warnings.
- `2`: validation failed.
