---
name: agent-collaboration-protocol
description: Use when coordinating multiple AI agents, coding assistants, teams, repos, or users through a vendor-neutral shared filesystem protocol. Uses protocol.json, events.jsonl, proposal.md, review.md, decisions.md, readiness.md, strict phases, readiness gates, and validator checks. Requires a collaboration folder, participants, objective, and completion gates before starting.
---

# Agent Collaboration Protocol

Use a shared folder as a portable coordination bus for agents that cannot
directly message each other. ACP is a breaking protocol: it is a state
machine with structured events and readiness gates, not a loose Markdown
conversation.

Any compatible agent must be able to read Markdown and JSON, write Markdown,
append JSONL events, and run or exactly reproduce the bundled script behavior.
Do not rely on Codex thread APIs, Claude-specific hooks, OpenCode-only state,
Kiro-only metadata, or hidden conversation memory for correctness.

## Required Inputs

Before starting, require:

- `collaboration_folder`: absolute or repo-relative shared folder path.
- `objective`: what the collaboration must decide or produce.
- `completion_gates`: concrete gates for ending collaboration.
- `participants`: all participant ids, such as `server`, `reader`, `reviewer`,
  or `agent-a`.
- `participant_id`: the current agent identity.

If any required input is missing, ask for it before creating files or writing
events. Do not invent completion gates.

## Files

ACP folders use these files:

- `protocol.json`: objective, participants, completion gates,
  current phase, proposal owner, waiting participants, and timestamps.
- `events.jsonl`: append-only event log. Each line is one compact JSON object.
- `proposal.md`: current proposal only.
- `review.md`: structured participant reviews.
- `decisions.md`: accepted decisions only.
- `readiness.md`: open question classification, blockers, deferred
  nonblocking items, and implementation readiness.
- `conclusion.md`: final discussion conclusion. It states whether to proceed,
  not proceed, defer, or block; why; how to implement or why not; and the next
  action.

Do not create or use `state.log`, `discussion.md`, or `opinions.md`. They are
not protocol files and must not appear in completion gates or instructions.

## Initialization

Prefer the bundled script:

```bash
python3 <skill>/scripts/init_collaboration.py \
  --folder <collaboration_folder> \
  --participant <participant_id> \
  --participant <other_participant_id> \
  --objective "<objective>" \
  --completion "<completion gate>" \
  --completion "<another gate>"
```

The initializer fails if `protocol.json` already exists unless `--resume` is
provided. Repeated initialization is not an append operation.

## Events

Use `scripts/append_event.py` or exactly reproduce its behavior. Do not hand
write events unless the runtime cannot execute scripts.

Required event fields:

- `seq`: continuous integer in `events.jsonl`.
- `from`: participant id listed in `protocol.json`.
- `event`: allowed event name.
- `at`: ISO-8601 UTC timestamp.
- `summary`: one short sentence.

Recommended fields:

- `doc`: path relative to collaboration folder.
- `reply_to`: earlier event `seq`.

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

All responses must use `reply_to` when they are responding to a prior event.
`reply_to` must point to an earlier existing event.
Event timestamps must not move backward as `seq` increases. If a mistake is
discovered, append `blocked` or a new corrective event; do not rewrite earlier
events.

## Phases

Agents must act according to `protocol.json.currentPhase` and
`protocol.json.waitingFor`:

- `drafting`: proposal owner updates `proposal.md`, then appends
  `proposal_submitted`.
- `reviewing`: only participants listed in `waitingFor` append structured
  reviews to `review.md`, then append `review_submitted`.
- `revising`: proposal owner addresses required changes and appends
  `proposal_revised`.
- `decision_review`: proposal owner first classifies every open question in
  `readiness.md` and appends `question_classified`; only then do participants
  listed in `waitingFor` accept explicit decisions in `decisions.md` by
  appending `decision_accepted`.
- `readiness_check`: participants classify every question, clear blockers, and
  pass readiness, then the proposal owner writes `conclusion.md`.
- `completed`: stop unless the user explicitly starts a new round.
- `blocked`: stop until the blocker is resolved.

`completed` is valid only after a prior `readiness_passed` event.
`completed` must reference `conclusion.md`. Do not complete with only
`decisions.md`; decisions are inputs, while `conclusion.md` is the final answer
to the collaboration objective.

The proposal owner must wait after `proposal_submitted`. While phase is
`reviewing`, the owner may poll for the next action or append `blocked` for a
real timeout/blocker, but must not edit `proposal.md`, `decisions.md`,
`readiness.md`, or `protocol.json`, and must not append advancing events until
the required review is submitted.

## Review Format

Every `review_submitted` event must have a matching `review.md` heading whose
seq equals that event's `seq`:

```markdown
## <ISO-8601 UTC> - <participant_id> - seq <review_submitted event seq>

Context:
- Read `proposal.md` after event seq `<seq>`.

Position:
- ...

Concerns:
- ...

Required Changes:
- ...

Questions:
- ...
```

Do not use the replied-to event seq in the review heading. Put replied-to
context in `Context` and `reply_to`.

## Readiness Gate

Before `readiness_passed` or `completed`:

- Every open question must be classified as `[resolved]`,
  `[deferred_nonblocking]`, or `[blocking]`.
- Every `[deferred_nonblocking]` item must include `Reason: ...`.
- No `[blocking]` or `[unresolved]` item may remain.
- The final design checklist must include and check `Ready to implement`.
- `validate_collaboration.py` must pass.

Blocking readiness items also prevent `decision_accepted`.
Unresolved questions and deferred items missing `Reason: ...` also prevent
`decision_accepted`.

Final design documents must separate:

- Accepted Decisions
- Assumptions
- Deferred Follow-ups
- Implementation Blockers
- Ready to Implement

## Final Conclusion

Before `completed`, write `conclusion.md` as a conclusion document, not a log.
It must include:

- Decision Outcome: exactly one of `[proceed]`, `[do_not_proceed]`, or
  `[defer]`.
- Rationale.
- Accepted Decisions.
- Implementation Approach.
- Assumptions.
- Deferred Follow-ups.
- Implementation Blockers.
- Next Action.

Use `[proceed]` when implementation should start now, `[do_not_proceed]` when
the feature or plan should not be done, and `[defer]` when follow-up work must
happen before implementation. A `[blocked]` outcome may exist while the
collaboration is blocked, but it is not completable.

## Polling And Watchers

Participants must stay alive for the collaboration loop until the phase is
`completed`, `blocked`, or an explicit user/coordinator deadline is reached.
Do not stop merely because you appended one valid event. After every action,
read `protocol.json` again and either take the next allowed action or wait for
the next event.

If the runtime has a watcher, it may notify the participant when `events.jsonl`
or `protocol.json` changes. The watcher must stay dumb: it only notices changes
and never writes analysis or decisions.

If there is no watcher, use:

```bash
python3 <skill>/scripts/next_action.py \
  --folder <collaboration_folder> \
  --participant <participant_id>
```

For autonomous participants, prefer the blocking helper:

```bash
python3 <skill>/scripts/wait_for_turn.py \
  --folder <collaboration_folder> \
  --participant <participant_id>
```

`wait_for_turn.py` returns when the participant is listed in `waitingFor`, or
when the collaboration becomes `completed` or `blocked`. It defaults to a
30-minute timeout to avoid permanently stuck participant processes; use
`--timeout 0` only when an external supervisor owns cancellation. On return,
inspect `next_action.py`, act if it is your turn, append the required event, and
repeat the wait/action loop. Manual user prompts such as "check the new opinion"
are a fallback only, not the intended collaboration loop.

Coordinator prompts that launch participants should ask each participant to run
this loop instead of doing one phase and exiting. A participant that is not
listed in `waitingFor` may block in `wait_for_turn.py`, but must not edit shared
state while waiting.

## Validation

Run:

```bash
python3 <skill>/scripts/validate_collaboration.py --folder <collaboration_folder>
```

The validator checks required files, absence of obsolete files, event shape,
seq continuity, timestamp monotonicity, phase transitions, `waitingFor`
ownership, `reply_to`, review heading seqs, readiness classification,
conclusion completeness, and completion ordering.

Exit codes:

- `0`: valid.
- `1`: valid with warnings.
- `2`: invalid.
