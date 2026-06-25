#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from _acp import (
    DELIVERABLE_TYPE_NAMES,
    append_jsonl,
    default_deliverable_file,
    path_has_escape,
    render_deliverable_template,
    utc_now,
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize an ACP schema v2 collaboration folder.")
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
        help="Objective-specific completion gate; repeat for multiple gates",
    )
    parser.add_argument("--primary-deliverable-type", required=True, choices=sorted(DELIVERABLE_TYPE_NAMES))
    parser.add_argument("--primary-deliverable-file", help="Primary Markdown deliverable file relative to deliverables dir")
    parser.add_argument(
        "--primary-deliverable-check",
        action="append",
        default=[],
        help="Required checklist section for custom primary deliverables; repeat for multiple sections",
    )
    parser.add_argument("--deliverables-mode", choices=["internal", "external"], default="internal")
    parser.add_argument("--deliverables-dir", default="deliverables")
    parser.add_argument("--repo-root", help="Required for external mode; path relative to collaboration folder")
    parser.add_argument("--resume", action="store_true", help="Return successfully if a collaboration folder already exists")
    args = parser.parse_args()

    objective = args.objective.strip()
    participants = []
    for value in args.participant:
        item = value.strip()
        if item and item not in participants:
            participants.append(item)
    objective_gates = [item.strip() for item in args.completion if item.strip()]
    if not objective:
        parser.error("--objective must not be blank")
    if len(participants) < 2:
        parser.error("at least two non-blank --participant values are required")
    if not objective_gates:
        parser.error("at least one non-blank --completion is required")

    primary_type = args.primary_deliverable_type
    try:
        primary_file = args.primary_deliverable_file or default_deliverable_file(primary_type)
    except Exception as exc:
        parser.error(str(exc))
    primary_checks = [item.strip() for item in args.primary_deliverable_check if item.strip()]
    if primary_type == "custom" and not args.primary_deliverable_file:
        parser.error("custom deliverables require --primary-deliverable-file")
    if primary_type == "custom" and not primary_checks:
        parser.error("custom deliverables require at least one --primary-deliverable-check")
    if not primary_file.endswith(".md"):
        parser.error("primary deliverable file must end with .md")
    if path_has_escape(primary_file):
        parser.error("primary deliverable file must be relative and must not contain ..")
    if path_has_escape(args.deliverables_dir):
        parser.error("--deliverables-dir must be relative and must not contain ..")
    if args.deliverables_mode == "external":
        if not args.repo_root:
            parser.error("--repo-root is required when --deliverables-mode external")
        if Path(args.repo_root).is_absolute():
            parser.error("--repo-root must be relative to the collaboration folder")
    elif args.repo_root:
        parser.error("--repo-root is only allowed when --deliverables-mode external")

    folder = Path(args.folder).expanduser().resolve()
    protocol_path = folder / "protocol.json"
    if protocol_path.exists():
        if args.resume:
            print(f"Collaboration folder already exists: {folder}")
            return 0
        parser.error("collaboration folder already contains protocol.json; use --resume to acknowledge it")

    folder.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    primary_ref = f"external:{primary_file}" if args.deliverables_mode == "external" else str(Path(args.deliverables_dir) / primary_file)
    generated_gates = [
        f"Primary deliverable exists: `{primary_ref}`",
        f"Primary deliverable has required `{primary_type}` sections",
        "Every accepted decision has `Reflected in`",
        "Every accepted decision is reflected in the primary deliverable",
        "Primary deliverable status is `Frozen`",
        "Primary deliverable SHA-256 snapshot recorded",
    ]
    protocol = {
        "protocol": "acp",
        "schemaVersion": 2,
        "objective": objective,
        "objectiveGates": objective_gates,
        "participants": [{"id": item} for item in participants],
        "completionGates": [
            *[{"source": "objective", "text": item} for item in objective_gates],
            *[{"source": "generated", "text": item} for item in generated_gates],
        ],
        "deliverables": {
            "mode": args.deliverables_mode,
            "dir": args.deliverables_dir,
            "owner": participants[0],
            "coAuthors": [],
            "primary": {
                "type": primary_type,
                "file": primary_file,
                "checklist": primary_checks,
            },
            "supporting": [],
            "attachments": [],
        },
        "currentPhase": "drafting",
        "proposalOwner": participants[0],
        "waitingFor": [participants[0]],
        "createdAt": now,
        "updatedAt": now,
    }
    if args.deliverables_mode == "external":
        protocol["repoRoot"] = args.repo_root
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.deliverables_mode == "external":
        deliverables_dir = (folder / args.repo_root / args.deliverables_dir).resolve()
    else:
        deliverables_dir = folder / args.deliverables_dir
    write_text(deliverables_dir / primary_file, render_deliverable_template(protocol["deliverables"]["primary"]))

    objective_gate_lines = "\n".join(f"- {item}" for item in objective_gates)
    participant_lines = "\n".join(f"- `{item}`" for item in participants)
    objective_gate_checks = "\n".join(f"- [ ] {item}" for item in objective_gates)
    generated_gate_checks = "\n".join(f"- [ ] {item}" for item in generated_gates)
    write_text(
        folder / "README.md",
        f"""# ACP Collaboration Workspace

Objective:
{objective}

Participants:
{participant_lines}

Objective Gates:
{objective_gate_lines}

Primary Deliverable:
- Type: `{primary_type}`
- Path: `{primary_ref}`

Protocol Files:
- `protocol.json`: ACP schema v2 state and deliverable declaration.
- `events.jsonl`: append-only structured events with continuous `seq` values.
- `proposal.md`: current proposal/change summary only.
- `review.md`: structured participant reviews.
- `decisions.md`: accepted decision index with stable IDs.
- `readiness.md`: question classification, objective gates, generated deliverable gates, and freeze snapshot.
- `conclusion.md`: final receipt that references the frozen deliverable.
- `{args.deliverables_dir}/`: actual deliverable artifacts.
""",
    )
    write_text(
        folder / "proposal.md",
        f"""# Proposal

## Purpose

{objective}

## Current Proposal

Initial proposal pending.

## Deliverable Draft

- Primary: `{primary_ref}`

## Review Focus

- Proposal coherence.
- Primary deliverable completeness.
- Accepted decision traceability.
- Implementation readiness.
""",
    )
    write_text(
        folder / "review.md",
        f"""# Review

Append one structured review per `review_submitted` event.

Heading rule:
`## <ISO-8601 UTC> - <participant_id> - seq <review_submitted event seq>`

Template:

## <timestamp> - <participant_id> - seq <event seq>

Context:
- Read `proposal.md` after event seq `<seq>`.
- Reviewed primary deliverable: `{primary_ref}`
- Reviewed supporting deliverables: none.

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
""",
    )
    write_text(
        folder / "decisions.md",
        f"""# Decisions

Only record accepted decisions here. Use stable IDs and trace each decision to a declared deliverable.

## Accepted Decisions

### D1. Initial deliverable declaration

- Decision: The primary deliverable for this collaboration is `{primary_ref}`.
- Rationale: ACP schema v2 requires a declared primary deliverable.
- Reflected in: `{primary_ref}#proposed-design`
""",
    )
    write_text(
        folder / "readiness.md",
        f"""# Readiness

Classify every open question before readiness can pass.

## Open Question Classification

- [unresolved] Initial deliverable review has not completed.

Allowed statuses:
- `[resolved]`
- `[deferred_nonblocking]` with `Reason: ...`
- `[blocking]`

## Blocking Issues

- None.

## Objective Gates

{objective_gate_checks}

## Generated Deliverable Gates

{generated_gate_checks}

## Deliverable Snapshot

- Primary: `{primary_ref}`
- SHA-256:

## Supporting Deliverables

- None.

## Attachments

- None.

## Deferred Follow-ups

- None.

## Implementation Blockers

- None.

## Ready to Implement

- [ ] Ready to implement
""",
    )
    write_text(
        folder / "conclusion.md",
        f"""# Conclusion

This file is the final receipt of the collaboration, not the primary deliverable.

## Decision Outcome

- [blocked] Collaboration is not complete.

Allowed final outcomes:
- `[proceed]` implement now.
- `[do_not_proceed]` do not implement.
- `[defer]` defer until named follow-ups are resolved.

## Rationale

The collaboration is still in progress.

## Deliverable Receipt

- Primary: `{primary_ref}`
- Type: `{primary_type}`
- SHA-256:
- Supporting: none
- Attachments: none

## Accepted Decisions Summary

- No accepted decisions yet.

## Readiness Result

- Objective gates: not passed
- Generated deliverable gates: not passed
- Readiness file: `readiness.md`

## Assumptions

- No assumptions accepted yet.

## Deferred Follow-ups

- None.

## Implementation Blockers

- None.

## Next Action

Continue the ACP state machine.
""",
    )
    append_jsonl(
        folder / "events.jsonl",
        {
            "seq": 1,
            "from": participants[0],
            "event": "initialized",
            "at": now,
            "summary": "Initialized ACP schema v2 collaboration workspace.",
            "doc": "protocol.json",
        },
    )
    print(f"Initialized ACP schema v2 collaboration folder: {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
