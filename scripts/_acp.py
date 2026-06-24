import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


PHASES = {
    "drafting",
    "reviewing",
    "revising",
    "decision_review",
    "readiness_check",
    "completed",
    "blocked",
}

EVENTS = {
    "initialized",
    "proposal_submitted",
    "review_submitted",
    "proposal_revised",
    "question_classified",
    "decision_proposed",
    "decision_accepted",
    "readiness_passed",
    "completed",
    "blocked",
}

REQUIRED_FILES = [
    "protocol.json",
    "events.jsonl",
    "proposal.md",
    "review.md",
    "decisions.md",
    "readiness.md",
]


class ProtocolError(Exception):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_protocol(folder: Path) -> dict[str, Any]:
    path = folder / "protocol.json"
    if not path.exists():
        raise ProtocolError(f"missing protocol.json in {folder}")
    try:
        protocol = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid protocol.json: {exc}") from exc
    return protocol


def write_protocol(folder: Path, protocol: dict[str, Any]) -> None:
    protocol["updatedAt"] = utc_now()
    (folder / "protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_events(folder: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = folder / "events.jsonl"
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return events, ["missing events.jsonl"]

    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"events.jsonl line {index}: invalid JSON: {exc}")
            continue
        if not isinstance(event, dict):
            errors.append(f"events.jsonl line {index}: event must be an object")
            continue
        events.append(event)
    return events, errors


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def next_seq(events: list[dict[str, Any]]) -> int:
    if not events:
        return 1
    values = [event.get("seq") for event in events if isinstance(event.get("seq"), int)]
    return (max(values) if values else 0) + 1


def existing_seqs(events: list[dict[str, Any]]) -> set[int]:
    return {event["seq"] for event in events if isinstance(event.get("seq"), int)}


def participant_ids(protocol: dict[str, Any]) -> list[str]:
    participants = protocol.get("participants", [])
    if not isinstance(participants, list):
        return []
    result: list[str] = []
    for item in participants:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            result.append(item["id"])
    return result


def readiness_scan(folder: Path) -> dict[str, Any]:
    text = (folder / "readiness.md").read_text(encoding="utf-8") if (folder / "readiness.md").exists() else ""
    statuses = re.findall(r"^\s*-\s*\[([A-Za-z_]+)\]\s*(.*)$", text, flags=re.MULTILINE)
    blocking = [body for status, body in statuses if status == "blocking"]
    unresolved = [
        body
        for status, body in statuses
        if status in {"unresolved", "resolved", "deferred_nonblocking", "blocking"}
        and (status == "unresolved" or "TBD" in body)
    ]
    deferred_missing_reason = [
        body for status, body in statuses if status == "deferred_nonblocking" and "reason:" not in body.lower()
    ]
    ready_to_implement = bool(re.search(r"^\s*-\s*\[[xX]\]\s*Ready to implement", text, flags=re.MULTILINE))
    return {
        "blocking": blocking,
        "unresolved": unresolved,
        "deferred_missing_reason": deferred_missing_reason,
        "ready_to_implement": ready_to_implement,
        "text": text,
    }


def missing_completion_gates(protocol: dict[str, Any], readiness_text: str) -> list[str]:
    gates = protocol.get("completionGates", [])
    if not isinstance(gates, list):
        return []
    missing: list[str] = []
    for gate in gates:
        if not isinstance(gate, str):
            continue
        pattern = r"^\s*-\s*\[[xX]\]\s*" + re.escape(gate) + r"\s*$"
        if not re.search(pattern, readiness_text, flags=re.MULTILINE):
            missing.append(gate)
    return missing


def decision_acceptance_complete(protocol: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    participants = set(participant_ids(protocol))
    if not participants:
        return False
    marker = 0
    for event in events:
        if event.get("event") in {"proposal_revised", "decision_proposed"} and isinstance(event.get("seq"), int):
            marker = event["seq"]
    accepted = {
        event.get("from")
        for event in events
        if event.get("event") == "decision_accepted"
        and isinstance(event.get("seq"), int)
        and event["seq"] > marker
    }
    return participants.issubset(accepted)


def derive_phase(protocol: dict[str, Any], events: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    phase: str | None = None
    errors: list[str] = []
    readiness_passed = False

    for event in events:
        name = event.get("event")
        seq = event.get("seq")
        if name == "initialized":
            if seq != 1:
                errors.append("initialized must be seq 1")
            phase = "drafting"
        elif name == "blocked":
            phase = "blocked"
        elif name == "proposal_submitted":
            if phase not in {"drafting", "revising"}:
                errors.append(f"seq {seq}: proposal_submitted is not allowed from phase {phase}")
            phase = "reviewing"
        elif name == "review_submitted":
            if phase != "reviewing":
                errors.append(f"seq {seq}: review_submitted is not allowed from phase {phase}")
            phase = "revising"
        elif name == "proposal_revised":
            if phase != "revising":
                errors.append(f"seq {seq}: proposal_revised is not allowed from phase {phase}")
            phase = "decision_review"
        elif name == "decision_proposed":
            if phase not in {"revising", "decision_review"}:
                errors.append(f"seq {seq}: decision_proposed is not allowed from phase {phase}")
            phase = "decision_review"
        elif name == "decision_accepted":
            if phase != "decision_review":
                errors.append(f"seq {seq}: decision_accepted is not allowed from phase {phase}")
            prefix = [item for item in events if isinstance(item.get("seq"), int) and item["seq"] <= seq]
            phase = "readiness_check" if decision_acceptance_complete(protocol, prefix) else "decision_review"
        elif name == "question_classified":
            if phase != "readiness_check":
                errors.append(f"seq {seq}: question_classified is not allowed from phase {phase}")
            phase = "readiness_check"
        elif name == "readiness_passed":
            if phase != "readiness_check":
                errors.append(f"seq {seq}: readiness_passed is not allowed from phase {phase}")
            readiness_passed = True
            phase = "readiness_check"
        elif name == "completed":
            if phase != "readiness_check" or not readiness_passed:
                errors.append(f"seq {seq}: completed requires a prior readiness_passed event")
            phase = "completed"
    return phase, errors


def validate_event_shape(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[int] = set()
    for expected, event in enumerate(events, start=1):
        seq = event.get("seq")
        if seq != expected:
            errors.append(f"events.jsonl: expected seq {expected}, found {seq}")
        if isinstance(seq, int):
            seen.add(seq)
        for field in ("seq", "from", "event", "at", "summary"):
            if field not in event:
                errors.append(f"seq {seq}: missing required field {field}")
        if event.get("event") not in EVENTS:
            errors.append(f"seq {seq}: unknown event {event.get('event')!r}")
        reply_to = event.get("reply_to")
        if reply_to is not None:
            if not isinstance(reply_to, int) or reply_to not in seen:
                errors.append(f"seq {seq}: reply_to must point to an earlier event")
    return errors


def review_heading_map(folder: Path) -> dict[int, str]:
    path = folder / "review.md"
    if not path.exists():
        return {}
    headings: dict[int, str] = {}
    pattern = re.compile(r"^##\s+.+?\s+-\s+(.+?)\s+-\s+seq\s+(\d+)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            headings[int(match.group(2))] = match.group(1).strip()
    return headings


def validate_review_links(folder: Path, events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    headings = review_heading_map(folder)
    events_by_seq = {event.get("seq"): event for event in events}
    review_event_seqs = {event.get("seq") for event in events if event.get("event") == "review_submitted"}
    for seq in review_event_seqs:
        if seq not in headings:
            errors.append(f"seq {seq}: review_submitted requires matching review.md heading")
    for seq in headings:
        event = events_by_seq.get(seq)
        if not event:
            errors.append(f"review.md heading seq {seq}: no matching event")
        elif event.get("event") != "review_submitted":
            errors.append(f"review.md heading seq {seq}: matching event is {event.get('event')}, not review_submitted")
    return errors


def validate_folder(folder: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for name in REQUIRED_FILES:
        if not (folder / name).exists():
            errors.append(f"missing {name}")

    try:
        protocol = load_protocol(folder)
    except ProtocolError as exc:
        return [str(exc), *errors], warnings

    if protocol.get("currentPhase") not in PHASES:
        errors.append(f"currentPhase must be one of {sorted(PHASES)}")
    if not protocol.get("objective"):
        errors.append("protocol.json objective must not be blank")
    if not participant_ids(protocol):
        errors.append("protocol.json participants must not be empty")
    if not protocol.get("completionGates"):
        errors.append("protocol.json completionGates must not be empty")

    events, event_errors = read_events(folder)
    errors.extend(event_errors)
    errors.extend(validate_event_shape(events))
    errors.extend(validate_review_links(folder, events))
    derived_phase, phase_errors = derive_phase(protocol, events)
    errors.extend(phase_errors)
    if derived_phase and protocol.get("currentPhase") != derived_phase:
        errors.append(f"protocol.json currentPhase is {protocol.get('currentPhase')}, expected {derived_phase}")

    readiness = readiness_scan(folder)
    has_decision_acceptance = any(event.get("event") == "decision_accepted" for event in events)
    has_readiness_passed = any(event.get("event") == "readiness_passed" for event in events)
    has_completed = any(event.get("event") == "completed" for event in events)
    if readiness["blocking"] and has_decision_acceptance:
        errors.append("blocking readiness items must be cleared before decision_accepted")
    if has_readiness_passed or has_completed:
        if readiness["blocking"]:
            errors.append("blocking readiness items must be cleared before readiness_passed or completed")
        if readiness["unresolved"]:
            errors.append("unresolved readiness questions must be classified before readiness_passed or completed")
        if readiness["deferred_missing_reason"]:
            errors.append("deferred_nonblocking readiness items require a reason")
        if not readiness["ready_to_implement"]:
            errors.append("readiness.md must check 'Ready to implement' before readiness_passed or completed")
    if has_completed:
        missing_gates = missing_completion_gates(protocol, readiness["text"])
        if missing_gates:
            errors.append("completion gates must be checked before completed: " + ", ".join(missing_gates))
    elif readiness["deferred_missing_reason"]:
        warnings.append("deferred_nonblocking readiness items should include a reason")
    return errors, warnings


def append_event(
    folder: Path,
    participant: str,
    event_name: str,
    summary: str,
    doc: str | None = None,
    reply_to: int | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(folder)
    if event_name not in EVENTS:
        raise ProtocolError(f"unknown event {event_name!r}")
    if participant not in participant_ids(protocol):
        raise ProtocolError(f"participant {participant!r} is not listed in protocol.json")
    events, errors = read_events(folder)
    if errors:
        raise ProtocolError("; ".join(errors))
    if reply_to is not None and reply_to not in existing_seqs(events):
        raise ProtocolError("reply_to must point to an existing event")

    seq = next_seq(events)
    payload: dict[str, Any] = {
        "seq": seq,
        "from": participant,
        "event": event_name,
        "at": utc_now(),
        "summary": summary,
    }
    if doc:
        payload["doc"] = doc
    if reply_to is not None:
        payload["reply_to"] = reply_to

    candidate_events = [*events, payload]
    derived_phase, phase_errors = derive_phase(protocol, candidate_events)
    if phase_errors:
        raise ProtocolError("; ".join(phase_errors))
    readiness = readiness_scan(folder)
    if event_name in {"decision_accepted", "readiness_passed", "completed"} and readiness["blocking"]:
        raise ProtocolError("blocking readiness items must be cleared first")
    if event_name in {"readiness_passed", "completed"}:
        if readiness["unresolved"]:
            raise ProtocolError("unresolved readiness questions must be classified first")
        if readiness["deferred_missing_reason"]:
            raise ProtocolError("deferred_nonblocking readiness items require a reason")
        if not readiness["ready_to_implement"]:
            raise ProtocolError("readiness.md must check 'Ready to implement' first")
    if event_name == "completed":
        missing_gates = missing_completion_gates(protocol, readiness["text"])
        if missing_gates:
            raise ProtocolError("completion gates must be checked first: " + ", ".join(missing_gates))
    append_jsonl(folder / "events.jsonl", payload)
    if derived_phase:
        protocol["currentPhase"] = derived_phase
        write_protocol(folder, protocol)
    return payload
