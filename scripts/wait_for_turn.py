#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from pathlib import Path

from _acp import ProtocolError, load_protocol, participant_ids, read_events


TERMINAL_PHASES = {"completed", "blocked"}
DEFAULT_TIMEOUT_SECONDS = 30 * 60


def state_signature(folder: Path) -> tuple[float, float, int]:
    protocol = folder / "protocol.json"
    events = folder / "events.jsonl"
    event_count = 0
    if events.exists():
        event_count = len([line for line in events.read_text(encoding="utf-8").splitlines() if line.strip()])
    return (
        protocol.stat().st_mtime if protocol.exists() else 0,
        events.stat().st_mtime if events.exists() else 0,
        event_count,
    )


def is_ready(folder: Path, participant: str) -> tuple[bool, str]:
    protocol = load_protocol(folder)
    if participant not in participant_ids(protocol):
        raise ProtocolError(f"participant {participant!r} is not listed in protocol.json")

    events, errors = read_events(folder)
    if errors:
        raise ProtocolError("; ".join(errors))

    phase = protocol.get("currentPhase")
    waiting_for = protocol.get("waitingFor") if isinstance(protocol.get("waitingFor"), list) else []
    if phase in TERMINAL_PHASES:
        return True, f"phase is {phase}"
    if participant in waiting_for:
        return True, f"{participant} is listed in waitingFor"
    recent = events[-1] if events else None
    if recent:
        return False, f"waiting for {', '.join(waiting_for) if waiting_for else 'none'} after seq {recent.get('seq')}"
    return False, f"waiting for {', '.join(waiting_for) if waiting_for else 'none'}"


def print_next_action(folder: Path, participant: str) -> None:
    script = Path(__file__).resolve().parent / "next_action.py"
    subprocess.run(
        [sys.executable, str(script), "--folder", str(folder), "--participant", participant],
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Block until an ACP participant has the turn or the collaboration is terminal.")
    parser.add_argument("--folder", required=True, help="Collaboration folder")
    parser.add_argument("--participant", required=True, help="Participant id")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Maximum seconds to wait; defaults to 1800 seconds. Use 0 for no timeout.",
    )
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    start = time.monotonic()
    last_signature: tuple[float, float, int] | None = None
    while True:
        try:
            ready, reason = is_ready(folder, args.participant)
        except ProtocolError as exc:
            parser.exit(2, f"error: {exc}\n")
        if ready:
            print(f"ready: {reason}")
            print_next_action(folder, args.participant)
            return 0

        signature = state_signature(folder)
        if signature != last_signature:
            print(f"waiting: {reason}", flush=True)
            last_signature = signature

        if args.timeout and time.monotonic() - start >= args.timeout:
            print(f"timeout: {reason}", file=sys.stderr)
            return 1
        time.sleep(max(args.interval, 0.1))


if __name__ == "__main__":
    raise SystemExit(main())
