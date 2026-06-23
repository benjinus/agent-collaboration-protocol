#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from pathlib import Path


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def next_seq(state_path: Path) -> int:
    if not state_path.exists():
        return 1
    seq = 0
    for line in state_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        value = payload.get("seq")
        if isinstance(value, int) and value > seq:
            seq = value
    return seq + 1


def append_state(state_path: Path, participant: str, event: str, summary: str, doc: str | None = None) -> int:
    seq = next_seq(state_path)
    payload = {
        "seq": seq,
        "from": participant,
        "event": event,
        "at": utc_now(),
        "summary": summary,
    }
    if doc:
        payload["doc"] = doc
    with state_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return seq


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a vendor-neutral file collaboration folder.")
    parser.add_argument("--folder", required=True, help="Shared collaboration folder")
    parser.add_argument("--participant", required=True, help="Current participant id")
    parser.add_argument("--objective", required=True, help="Collaboration objective")
    parser.add_argument(
        "--completion",
        action="append",
        required=True,
        help="Completion condition; repeat for multiple conditions",
    )
    args = parser.parse_args()

    completions = [item.strip() for item in args.completion if item.strip()]
    if not args.objective.strip():
        parser.error("--objective must not be blank")
    if not completions:
        parser.error("at least one non-blank --completion is required")

    folder = Path(args.folder).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)

    readme = folder / "README.md"
    state = folder / "state.log"
    discussion = folder / "discussion.md"
    opinions = folder / "opinions.md"

    completion_lines = "\n".join(f"- {item}" for item in completions)
    write_if_missing(
        readme,
        f"""# File Collaboration Workspace

Objective:
{args.objective.strip()}

Completion Conditions:
{completion_lines}

Files:
- `state.log`: append-only JSONL events.
- `discussion.md`: shared proposal/design document.
- `opinions.md`: append-only participant opinions.

Rules:
- Append state events; do not edit previous state lines.
- Process only events from other participants.
- Write opinions in the agreed structured format.
- Stop when a completion condition is met and a `completed` event is written.

Compatibility:
- This workspace is vendor-neutral and can be used by Codex, Claude Code,
  OpenCode, Kiro, shell scripts, IDE tasks, or any agent that can read/write
  these files.
- Participant identity is the `from` field in `state.log`, not a vendor account.
""",
    )

    write_if_missing(
        discussion,
        f"""# Discussion

## Purpose

{args.objective.strip()}

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

    write_if_missing(
        opinions,
        """# Opinions

Append one structured entry per response. Do not rewrite older entries.
""",
    )

    seq = append_state(
        state,
        args.participant,
        "collaboration-started",
        "Collaboration workspace initialized",
        "discussion.md",
    )
    print(f"Initialized collaboration folder: {folder}")
    print(f"state seq: {seq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
