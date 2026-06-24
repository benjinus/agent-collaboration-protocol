#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from _acp import append_jsonl, utc_now


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize an Agent Collaboration Protocol folder.")
    parser.add_argument("--folder", required=True, help="Shared collaboration folder")
    parser.add_argument(
        "--participant",
        action="append",
        required=True,
        help="Participant id; repeat to list all participants. The first participant initializes the workspace.",
    )
    parser.add_argument("--objective", required=True, help="Collaboration objective")
    parser.add_argument(
        "--completion",
        action="append",
        required=True,
        help="Completion gate; repeat for multiple gates",
    )
    parser.add_argument("--resume", action="store_true", help="Return successfully if a collaboration folder already exists")
    args = parser.parse_args()

    objective = args.objective.strip()
    participants = []
    for value in args.participant:
        item = value.strip()
        if item and item not in participants:
            participants.append(item)
    completion_gates = [item.strip() for item in args.completion if item.strip()]
    if not objective:
        parser.error("--objective must not be blank")
    if not participants:
        parser.error("at least one non-blank --participant is required")
    if not completion_gates:
        parser.error("at least one non-blank --completion is required")

    folder = Path(args.folder).expanduser().resolve()
    protocol_path = folder / "protocol.json"
    if protocol_path.exists():
        if args.resume:
            print(f"Collaboration folder already exists: {folder}")
            return 0
        parser.error("collaboration folder already contains protocol.json; use --resume to acknowledge it")

    folder.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    protocol = {
        "objective": objective,
        "participants": [{"id": item} for item in participants],
        "completionGates": completion_gates,
        "currentPhase": "drafting",
        "proposalOwner": participants[0],
        "waitingFor": [participants[0]],
        "createdAt": now,
        "updatedAt": now,
    }
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    gates = "\n".join(f"- {item}" for item in completion_gates)
    gate_checks = "\n".join(f"- [ ] {item}" for item in completion_gates)
    participant_lines = "\n".join(f"- `{item}`" for item in participants)
    write_text(
        folder / "README.md",
        f"""# Agent Collaboration Workspace

Objective:
{objective}

Participants:
{participant_lines}

Completion Gates:
{gates}

Protocol Files:
- `protocol.json`: objective, participants, completion gates, and current phase.
- `events.jsonl`: append-only structured events with continuous `seq` values.
- `proposal.md`: current proposal only.
- `review.md`: structured participant reviews. Review headings must use the matching `review_submitted` event seq.
- `decisions.md`: accepted decisions only.
- `readiness.md`: question classification, blockers, deferred nonblocking items, and implementation readiness.
- `conclusion.md`: final discussion conclusion that states the outcome, rationale, implementation approach, and next action.

Rules:
- Use `scripts/append_event.py` or exactly reproduce its event behavior.
- Use `scripts/next_action.py` to poll for the next portable action when no runtime watcher exists.
- Run `scripts/validate_collaboration.py --folder <folder>` before `readiness_passed` and before `completed`.
- Respect `protocol.json.waitingFor`: only listed participants may advance the current phase.
- After `proposal_submitted`, the proposal owner must wait until all reviewers listed in `waitingFor` submit reviews or block.
- Do not complete until readiness has passed and every completion gate is satisfied.
- `completed` must reference `conclusion.md`; do not finish with only accepted decision fragments.
""",
    )
    write_text(
        folder / "proposal.md",
        f"""# Proposal

## Purpose

{objective}

## Current Proposal

TBD.

## Message/API Contracts

TBD.

## Operational Concerns

TBD.

## Open Questions

- TBD.

## Proposed Decisions

- TBD.
""",
    )
    write_text(
        folder / "review.md",
        """# Review

Append one structured review per `review_submitted` event.

Heading rule:
`## <ISO-8601 UTC> - <participant_id> - seq <review_submitted event seq>`

Template:

## <timestamp> - <participant_id> - seq <event seq>

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
""",
    )
    write_text(
        folder / "decisions.md",
        """# Decisions

Only record accepted decisions here. Do not mix unresolved parameters into this file.

## Accepted Decisions

- TBD.
""",
    )
    write_text(
        folder / "readiness.md",
        """# Readiness

Classify every open question before readiness can pass.

## Open Question Classification

- [unresolved] TBD.

Allowed statuses:
- `[resolved]`
- `[deferred_nonblocking]` with `Reason: ...`
- `[blocking]`

## Blocking Issues

- None.

## Deferred Follow-ups

- None.

## Completion Gates

{gate_checks}

## Final Design Document Checklist

- [ ] Accepted Decisions
- [ ] Assumptions
- [ ] Deferred Follow-ups
- [ ] Implementation Blockers
- [ ] Ready to implement
""",
    )
    write_text(
        folder / "conclusion.md",
        f"""# Conclusion

This file is the final outcome of the collaboration, not a transcript.
Complete it after decisions are accepted and readiness passes.

## Decision Outcome

- [blocked] TBD

Allowed final outcomes:
- `[proceed]` implement now.
- `[do_not_proceed]` do not implement.
- `[defer]` defer until named follow-ups are resolved.
- `[blocked]` cannot complete.

## Rationale

TBD.

## Accepted Decisions

- TBD.

## Implementation Approach

TBD.

## Assumptions

- TBD.

## Deferred Follow-ups

- TBD.

## Implementation Blockers

- TBD.

## Next Action

TBD.
""",
    )
    append_jsonl(
        folder / "events.jsonl",
        {
            "seq": 1,
            "from": participants[0],
            "event": "initialized",
            "at": now,
            "summary": "Collaboration workspace initialized",
            "doc": "protocol.json",
        },
    )
    print(f"Initialized ACP collaboration folder: {folder}")
    print("state seq: 1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
