#!/usr/bin/env python3
import argparse
from pathlib import Path

from _acp import EVENTS, ProtocolError, append_event


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a validated ACP event.")
    parser.add_argument("--folder", required=True, help="Collaboration folder")
    parser.add_argument("--participant", required=True, help="Participant id writing the event")
    parser.add_argument("--event", required=True, choices=sorted(EVENTS), help="Event name")
    parser.add_argument("--summary", required=True, help="Short event summary")
    parser.add_argument("--doc", help="Document path relative to the collaboration folder")
    parser.add_argument("--reply-to", type=int, help="Earlier event seq this event responds to")
    parser.add_argument("--role", choices=["primary", "supporting"], help="Deliverable role for deliverable_* events")
    parser.add_argument("--sha256", help="64-character lowercase hex SHA-256 for deliverable_frozen")
    args = parser.parse_args()

    try:
        payload = append_event(
            Path(args.folder).expanduser().resolve(),
            args.participant,
            args.event,
            args.summary,
            args.doc,
            args.reply_to,
            args.role,
            args.sha256,
        )
    except ProtocolError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(f"appended seq {payload['seq']}: {payload['event']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
