import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROTOCOL_NAME = "acp"
SCHEMA_VERSION = 2

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
    "deliverable_drafted",
    "deliverable_revised",
    "deliverable_frozen",
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
    "conclusion.md",
]

FORBIDDEN_FILES = [
    "state.log",
    "discussion.md",
    "opinions.md",
]

FORBIDDEN_PROTOCOL_REFERENCES = set(FORBIDDEN_FILES)

CONCLUSION_REQUIRED_HEADINGS = [
    "Decision Outcome",
    "Rationale",
    "Deliverable Receipt",
    "Accepted Decisions Summary",
    "Readiness Result",
    "Assumptions",
    "Deferred Follow-ups",
    "Implementation Blockers",
    "Next Action",
]

CONCLUSION_COMPLETABLE_OUTCOMES = {"proceed", "do_not_proceed", "defer"}

DELIVERABLE_TYPES = {
    "adr": {
        "title": "Architecture Decision Record",
        "default_file": "adr.md",
        "sections": ["Status", "Context", "Decision", "Alternatives Considered", "Consequences", "Follow-ups"],
    },
    "design-spec": {
        "title": "Design Spec",
        "default_file": "design-spec.md",
        "sections": [
            "Problem",
            "Goals",
            "Non-goals",
            "Proposed Design",
            "Interfaces / Contracts",
            "Failure Modes",
            "Validation Plan",
            "Open Questions",
        ],
    },
    "implementation-plan": {
        "title": "Implementation Plan",
        "default_file": "implementation-plan.md",
        "sections": ["Scope", "Phases", "Tasks", "Dependencies", "Rollout / Migration", "Tests", "Risks", "Exit Criteria"],
    },
    "decision-memo": {
        "title": "Decision Memo",
        "default_file": "decision-memo.md",
        "sections": ["Question", "Recommendation", "Options", "Tradeoffs", "Decision", "Next Action"],
    },
    "review-report": {
        "title": "Review Report",
        "default_file": "review-report.md",
        "sections": ["Scope", "Findings", "Risks", "Required Changes", "Open Questions", "Recommendation"],
    },
    "test-plan": {
        "title": "Test Plan",
        "default_file": "test-plan.md",
        "sections": ["Scope", "Test Matrix", "Fixtures", "Automation", "Manual Tests", "Exit Criteria"],
    },
}

DELIVERABLE_TYPE_NAMES = {*DELIVERABLE_TYPES, "custom"}
DELIVERABLE_STATUSES = {"Draft", "In Review", "Frozen"}


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


def parse_event_time(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.UTC)


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


def default_deliverable_file(deliverable_type: str) -> str:
    if deliverable_type not in DELIVERABLE_TYPES:
        raise ProtocolError("custom deliverables require --primary-deliverable-file")
    return str(DELIVERABLE_TYPES[deliverable_type]["default_file"])


def deliverable_sections(deliverable: dict[str, Any]) -> list[str]:
    deliverable_type = deliverable.get("type")
    if deliverable_type == "custom":
        checklist = deliverable.get("checklist", [])
        return [item.strip() for item in checklist if isinstance(item, str) and item.strip()]
    spec = DELIVERABLE_TYPES.get(deliverable_type)
    return list(spec["sections"]) if spec else []


def deliverable_title(deliverable: dict[str, Any]) -> str:
    deliverable_type = deliverable.get("type")
    if deliverable_type == "custom":
        return "Custom Deliverable"
    spec = DELIVERABLE_TYPES.get(deliverable_type)
    return str(spec["title"]) if spec else "Deliverable"


def render_deliverable_template(deliverable: dict[str, Any]) -> str:
    sections = deliverable_sections(deliverable)
    title = deliverable_title(deliverable)
    section_text = "\n\n".join(f"## {section}\n\n" for section in sections)
    return f"# {title}\n\nDeliverable type: `{deliverable['type']}`\nStatus: Draft\n\n{section_text}\n"


def path_has_escape(value: str) -> bool:
    path = Path(value)
    return path.is_absolute() or ".." in path.parts


def is_lower_hex_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deliverables_config(protocol: dict[str, Any]) -> dict[str, Any]:
    value = protocol.get("deliverables")
    return value if isinstance(value, dict) else {}


def resolved_deliverable_ref(protocol: dict[str, Any], file: str) -> str:
    deliverables = deliverables_config(protocol)
    mode = deliverables.get("mode", "internal")
    if mode == "external":
        return f"external:{file}"
    return str(Path(str(deliverables.get("dir", "deliverables"))) / file)


def primary_deliverable(protocol: dict[str, Any]) -> dict[str, Any]:
    primary = deliverables_config(protocol).get("primary")
    return primary if isinstance(primary, dict) else {}


def supporting_deliverables(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    supporting = deliverables_config(protocol).get("supporting", [])
    return [item for item in supporting if isinstance(item, dict)] if isinstance(supporting, list) else []


def primary_deliverable_ref(protocol: dict[str, Any]) -> str:
    return resolved_deliverable_ref(protocol, str(primary_deliverable(protocol).get("file", "")))


def actual_deliverables_base(folder: Path, protocol: dict[str, Any]) -> Path:
    deliverables = deliverables_config(protocol)
    mode = deliverables.get("mode", "internal")
    if mode == "external":
        repo_root = protocol.get("repoRoot")
        if not isinstance(repo_root, str):
            raise ProtocolError("repoRoot is required for external deliverables")
        return (folder / repo_root / str(deliverables.get("dir", ""))).resolve()
    return folder / str(deliverables.get("dir", "deliverables"))


def deliverable_file_path(folder: Path, protocol: dict[str, Any], file: str) -> Path:
    return actual_deliverables_base(folder, protocol) / file


def event_deliverable_file(protocol: dict[str, Any], doc: str, role: str) -> str:
    if role == "primary":
        expected_file = str(primary_deliverable(protocol).get("file", ""))
        expected_ref = resolved_deliverable_ref(protocol, expected_file)
        if doc != expected_ref:
            raise ProtocolError("doc must reference the primary deliverable")
        return expected_file

    for item in supporting_deliverables(protocol):
        file = str(item.get("file", ""))
        if doc == resolved_deliverable_ref(protocol, file):
            return file
    raise ProtocolError("doc must reference a declared supporting deliverable")


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


def conclusion_scan(folder: Path) -> dict[str, Any]:
    text = (folder / "conclusion.md").read_text(encoding="utf-8") if (folder / "conclusion.md").exists() else ""
    missing_headings = [
        heading
        for heading in CONCLUSION_REQUIRED_HEADINGS
        if not re.search(r"^##\s+" + re.escape(heading) + r"\s*$", text, flags=re.MULTILINE)
    ]
    outcomes = re.findall(r"^\s*-\s*\[([A-Za-z_]+)\]\s+(.+)$", text, flags=re.MULTILINE)
    final_outcomes = [
        (status, body)
        for status, body in outcomes
        if status in {*CONCLUSION_COMPLETABLE_OUTCOMES, "blocked"}
    ]
    placeholders = re.findall(r"\b(?:TBD|TODO|unresolved|待定)\b", text, flags=re.IGNORECASE)
    return {
        "missing_headings": missing_headings,
        "final_outcomes": final_outcomes,
        "placeholders": placeholders,
        "text": text,
    }


def validate_conclusion_for_completion(folder: Path, protocol: dict[str, Any] | None = None) -> list[str]:
    conclusion = conclusion_scan(folder)
    errors: list[str] = []
    if conclusion["missing_headings"]:
        errors.append("conclusion.md is missing required sections: " + ", ".join(conclusion["missing_headings"]))
    final_outcomes = conclusion["final_outcomes"]
    if len(final_outcomes) != 1:
        errors.append("conclusion.md must declare exactly one final outcome")
    elif final_outcomes[0][0] not in CONCLUSION_COMPLETABLE_OUTCOMES:
        errors.append("conclusion.md outcome cannot be completed while blocked")
    if conclusion["placeholders"]:
        errors.append("conclusion.md must not contain unresolved placeholders before completed")
    if protocol is not None:
        primary_ref = primary_deliverable_ref(protocol)
        if primary_ref and primary_ref not in conclusion["text"]:
            errors.append("conclusion.md must reference the primary deliverable")
    return errors


def missing_completion_gates(protocol: dict[str, Any], readiness_text: str) -> list[str]:
    gates = protocol.get("completionGates", [])
    if not isinstance(gates, list):
        return []
    missing: list[str] = []
    for gate in gates:
        text = gate.get("text") if isinstance(gate, dict) else gate
        if not isinstance(text, str):
            continue
        pattern = r"^\s*-\s*\[[xX]\]\s*" + re.escape(text) + r"\s*$"
        if not re.search(pattern, readiness_text, flags=re.MULTILINE):
            missing.append(text)
    return missing


def ready_for_decision(folder: Path) -> tuple[bool, list[str]]:
    readiness = readiness_scan(folder)
    errors: list[str] = []
    if readiness["blocking"]:
        errors.append("blocking readiness items must be cleared before decision_accepted")
    if readiness["unresolved"]:
        errors.append("unresolved readiness questions must be classified before decision_accepted")
    if readiness["deferred_missing_reason"]:
        errors.append("deferred_nonblocking readiness items require a reason before decision_accepted")
    return not errors, errors


def derive_state(
    protocol: dict[str, Any],
    events: list[dict[str, Any]],
    folder: Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    participants = participant_ids(protocol)
    phase: str | None = None
    proposal_owner: str | None = None
    waiting_for: list[str] = []
    review_waiting: set[str] = set()
    accepted_waiting: set[str] = set()
    classification_seq = 0
    latest_decision_input_seq = 0
    errors: list[str] = []
    readiness_passed = False
    primary_drafted = False
    primary_frozen = False

    def expect_waiting(event: dict[str, Any], allowed: set[str], action: str) -> bool:
        actor = event.get("from")
        seq = event.get("seq")
        if actor not in allowed:
            expected = ", ".join(sorted(allowed)) or "no participant"
            errors.append(f"seq {seq}: {action} is reserved for {expected}; got {actor}")
            return False
        return True

    for event in events:
        name = event.get("event")
        seq = event.get("seq")
        actor = event.get("from")
        if name == "initialized":
            if seq != 1:
                errors.append("initialized must be seq 1")
            if actor not in participants:
                errors.append(f"seq {seq}: initialized participant is not listed in protocol.json")
            proposal_owner = actor if isinstance(actor, str) else None
            phase = "drafting"
            waiting_for = [proposal_owner] if proposal_owner else []
        elif name == "blocked":
            phase = "blocked"
            waiting_for = []
        elif name == "deliverable_drafted":
            if event.get("role") == "primary":
                if phase not in {"drafting", "revising", "decision_review"}:
                    errors.append(f"seq {seq}: deliverable_drafted is not allowed from phase {phase}")
                if proposal_owner:
                    expect_waiting(event, {proposal_owner}, "deliverable draft")
                primary_drafted = True
        elif name == "deliverable_revised":
            if event.get("role") == "primary":
                if primary_frozen:
                    errors.append(f"seq {seq}: deliverable_revised is not allowed after deliverable_frozen")
                if phase not in {"revising", "decision_review"}:
                    errors.append(f"seq {seq}: deliverable_revised is not allowed from phase {phase}")
                if proposal_owner:
                    expect_waiting(event, {proposal_owner}, "deliverable revision")
                primary_drafted = True
        elif name == "deliverable_frozen":
            if event.get("role") == "primary":
                if primary_frozen:
                    errors.append(f"seq {seq}: primary deliverable can be frozen only once")
                if phase != "readiness_check":
                    errors.append(f"seq {seq}: deliverable_frozen is not allowed from phase {phase}")
                if proposal_owner:
                    expect_waiting(event, {proposal_owner}, "deliverable freeze")
                primary_frozen = True
        elif name == "proposal_submitted":
            if phase not in {"drafting", "revising"}:
                errors.append(f"seq {seq}: proposal_submitted is not allowed from phase {phase}")
            if not primary_drafted:
                errors.append(f"seq {seq}: proposal_submitted requires prior primary deliverable_drafted")
            expected_owner = {proposal_owner} if proposal_owner else {actor}
            expect_waiting(event, {item for item in expected_owner if isinstance(item, str)}, "proposal submission")
            proposal_owner = actor if isinstance(actor, str) else proposal_owner
            review_waiting = {item for item in participants if item != proposal_owner}
            if not review_waiting:
                errors.append(f"seq {seq}: proposal_submitted requires at least one reviewer")
            phase = "reviewing"
            waiting_for = sorted(review_waiting)
        elif name == "review_submitted":
            if phase != "reviewing":
                errors.append(f"seq {seq}: review_submitted is not allowed from phase {phase}")
            expect_waiting(event, review_waiting, "review submission")
            if actor in review_waiting:
                review_waiting.remove(actor)
            if review_waiting:
                phase = "reviewing"
                waiting_for = sorted(review_waiting)
            else:
                phase = "revising"
                waiting_for = [proposal_owner] if proposal_owner else []
        elif name == "proposal_revised":
            if phase != "revising":
                errors.append(f"seq {seq}: proposal_revised is not allowed from phase {phase}")
            if proposal_owner:
                expect_waiting(event, {proposal_owner}, "proposal revision")
            latest_decision_input_seq = seq if isinstance(seq, int) else latest_decision_input_seq
            classification_seq = 0
            phase = "decision_review"
            waiting_for = [proposal_owner] if proposal_owner else []
        elif name == "decision_proposed":
            if phase not in {"revising", "decision_review"}:
                errors.append(f"seq {seq}: decision_proposed is not allowed from phase {phase}")
            if proposal_owner:
                expect_waiting(event, {proposal_owner}, "decision proposal")
            latest_decision_input_seq = seq if isinstance(seq, int) else latest_decision_input_seq
            classification_seq = 0
            phase = "decision_review"
            waiting_for = [proposal_owner] if proposal_owner else []
        elif name == "question_classified":
            if phase != "decision_review":
                errors.append(f"seq {seq}: question_classified is not allowed from phase {phase}")
            if proposal_owner:
                expect_waiting(event, {proposal_owner}, "question classification")
            classification_seq = seq if isinstance(seq, int) else classification_seq
            accepted_waiting = set(participants)
            phase = "decision_review"
            waiting_for = sorted(accepted_waiting)
        elif name == "decision_accepted":
            if phase != "decision_review":
                errors.append(f"seq {seq}: decision_accepted is not allowed from phase {phase}")
            if latest_decision_input_seq and classification_seq <= latest_decision_input_seq:
                errors.append(f"seq {seq}: decision_accepted requires question_classified after the latest proposal or decision")
            expect_waiting(event, accepted_waiting, "decision acceptance")
            if folder is not None:
                _, readiness_errors = ready_for_decision(folder)
                errors.extend(f"seq {seq}: {item}" for item in readiness_errors)
            if actor in accepted_waiting:
                accepted_waiting.remove(actor)
            if accepted_waiting:
                phase = "decision_review"
                waiting_for = sorted(accepted_waiting)
            else:
                phase = "readiness_check"
                waiting_for = [proposal_owner] if proposal_owner else []
        elif name == "readiness_passed":
            if phase != "readiness_check":
                errors.append(f"seq {seq}: readiness_passed is not allowed from phase {phase}")
            if not primary_frozen:
                errors.append(f"seq {seq}: readiness_passed requires primary deliverable_frozen")
            if proposal_owner:
                expect_waiting(event, {proposal_owner}, "readiness pass")
            readiness_passed = True
            phase = "readiness_check"
            waiting_for = [proposal_owner] if proposal_owner else []
        elif name == "completed":
            if phase != "readiness_check" or not readiness_passed:
                errors.append(f"seq {seq}: completed requires a prior readiness_passed event")
            if event.get("doc") != "conclusion.md":
                errors.append(f"seq {seq}: completed must reference conclusion.md")
            if proposal_owner:
                expect_waiting(event, {proposal_owner}, "completion")
            phase = "completed"
            waiting_for = []
    return {
        "currentPhase": phase,
        "proposalOwner": proposal_owner,
        "waitingFor": waiting_for,
    }, errors


def validate_event_shape(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[int] = set()
    previous_at: dt.datetime | None = None
    for expected, event in enumerate(events, start=1):
        seq = event.get("seq")
        if seq != expected:
            errors.append(f"events.jsonl: expected seq {expected}, found {seq}")
        for field in ("seq", "from", "event", "at", "summary"):
            if field not in event:
                errors.append(f"seq {seq}: missing required field {field}")
        if event.get("event") not in EVENTS:
            errors.append(f"seq {seq}: unknown event {event.get('event')!r}")
        if isinstance(event.get("event"), str) and event["event"].startswith("deliverable_"):
            if event.get("role") not in {"primary", "supporting"}:
                errors.append(f"seq {seq}: deliverable events require role")
            if not isinstance(event.get("doc"), str):
                errors.append(f"seq {seq}: deliverable events require doc")
            if event["event"] == "deliverable_frozen" and not is_lower_hex_sha256(event.get("sha256")):
                errors.append(f"seq {seq}: deliverable_frozen requires sha256")
        reply_to = event.get("reply_to")
        if event.get("event") != "initialized" and reply_to is None:
            errors.append(f"seq {seq}: reply_to is required after initialized")
        if reply_to is not None:
            if not isinstance(reply_to, int) or reply_to not in seen:
                errors.append(f"seq {seq}: reply_to must point to an earlier event")
        parsed_at = parse_event_time(event.get("at"))
        if parsed_at is None:
            errors.append(f"seq {seq}: at must be an ISO-8601 timestamp")
        elif previous_at is not None and parsed_at < previous_at:
            errors.append(f"seq {seq}: at must not be earlier than the previous event")
        if parsed_at is not None:
            previous_at = parsed_at
        if isinstance(seq, int):
            seen.add(seq)
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


def validate_review_links(folder: Path, events: list[dict[str, Any]], protocol: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    headings = review_heading_map(folder)
    events_by_seq = {event.get("seq"): event for event in events}
    review_event_seqs = {event.get("seq") for event in events if event.get("event") == "review_submitted"}
    text = (folder / "review.md").read_text(encoding="utf-8") if (folder / "review.md").exists() else ""
    for seq in review_event_seqs:
        if seq not in headings:
            errors.append(f"seq {seq}: review_submitted requires matching review.md heading")
    for seq in headings:
        event = events_by_seq.get(seq)
        if not event:
            errors.append(f"review.md heading seq {seq}: no matching event")
        elif event.get("event") != "review_submitted":
            errors.append(f"review.md heading seq {seq}: matching event is {event.get('event')}, not review_submitted")
        elif headings[seq] != event.get("from"):
            errors.append(f"review.md heading seq {seq}: participant {headings[seq]!r} does not match event from {event.get('from')!r}")
    if review_event_seqs:
        if "Reviewed primary deliverable:" not in text:
            errors.append("review.md must declare Reviewed primary deliverable")
        if "Review Scope:" not in text:
            errors.append("review.md must declare Review Scope")
        if "Primary deliverable completeness" not in text:
            errors.append("review.md Review Scope must include Primary deliverable completeness")
        primary_ref = primary_deliverable_ref(protocol)
        if primary_ref and primary_ref not in text:
            errors.append("review.md must reference the primary deliverable")
    return errors


def markdown_heading_present(text: str, heading: str) -> bool:
    return bool(re.search(r"^##\s+" + re.escape(heading) + r"\s*$", text, flags=re.MULTILINE))


def markdown_section_has_content(text: str, heading: str) -> bool:
    pattern = re.compile(r"^##\s+" + re.escape(heading) + r"\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE)
    match = pattern.search(text)
    return bool(match and match.group(1).strip())


def deliverable_status(text: str) -> str | None:
    match = re.search(r"^Status:\s*(Draft|In Review|Frozen)\s*$", text, flags=re.MULTILINE)
    return match.group(1) if match else None


def validate_deliverables_schema(protocol: dict[str, Any], folder: Path) -> list[str]:
    errors: list[str] = []
    deliverables = deliverables_config(protocol)
    if not deliverables:
        return ["protocol.json deliverables.primary is required"]
    mode = deliverables.get("mode")
    if mode not in {"internal", "external"}:
        errors.append("deliverables.mode must be internal or external")
    if mode == "internal" and "repoRoot" in protocol:
        errors.append("repoRoot is not allowed for internal deliverables")
    if mode == "external":
        repo_root = protocol.get("repoRoot")
        if not isinstance(repo_root, str) or not repo_root.strip():
            errors.append("repoRoot is required for external deliverables")
        elif Path(repo_root).is_absolute():
            errors.append("repoRoot must be relative")
        else:
            resolved = (folder / repo_root).resolve()
            if not resolved.exists() or not resolved.is_dir():
                errors.append("repoRoot must resolve to an existing directory")
            elif resolved == resolved.anchor:
                errors.append("repoRoot must not resolve to filesystem root")
            elif resolved not in [folder.resolve(), *folder.resolve().parents]:
                errors.append("collaboration folder must be inside repoRoot")
    directory = deliverables.get("dir")
    if not isinstance(directory, str) or not directory.strip():
        errors.append("deliverables.dir is required")
    elif path_has_escape(directory):
        errors.append("deliverables.dir must be relative and must not contain ..")
    primary = deliverables.get("primary")
    if not isinstance(primary, dict):
        errors.append("protocol.json deliverables.primary is required")
        return errors
    dtype = primary.get("type")
    if dtype not in DELIVERABLE_TYPE_NAMES:
        errors.append("primary deliverable type is invalid")
    file = primary.get("file")
    if not isinstance(file, str) or not file.endswith(".md"):
        errors.append("primary deliverable file must be Markdown")
    elif path_has_escape(file):
        errors.append("primary deliverable file must be relative and must not contain ..")
    if dtype == "custom" and not deliverable_sections(primary):
        errors.append("custom primary deliverable requires checklist")
    seen_supporting: set[str] = set()
    for item in supporting_deliverables(protocol):
        file = item.get("file")
        dtype = item.get("type")
        if dtype not in DELIVERABLE_TYPE_NAMES:
            errors.append("supporting deliverable type is invalid")
        if not isinstance(file, str) or not file.endswith(".md"):
            errors.append("supporting deliverable file must be Markdown")
        elif path_has_escape(file):
            errors.append("supporting deliverable file must be relative and must not contain ..")
        elif file in seen_supporting:
            errors.append("supporting deliverable files must be unique")
        elif file == primary.get("file"):
            errors.append("supporting deliverable must not reuse the primary deliverable file")
        else:
            seen_supporting.add(file)
    attachments = deliverables.get("attachments", [])
    if isinstance(attachments, list):
        for item in attachments:
            if not isinstance(item, dict):
                errors.append("attachments must be objects")
                continue
            file = item.get("file")
            if not isinstance(file, str) or not file:
                errors.append("attachment file is required")
            elif path_has_escape(file):
                errors.append("attachment file must be relative and must not contain ..")
    return errors


def validate_primary_deliverable_content(protocol: dict[str, Any], folder: Path, require_frozen: bool) -> list[str]:
    errors: list[str] = []
    primary = primary_deliverable(protocol)
    ref = primary_deliverable_ref(protocol)
    try:
        path = deliverable_file_path(folder, protocol, str(primary.get("file", "")))
    except ProtocolError as exc:
        return [str(exc)]
    if not path.exists():
        return [f"primary deliverable missing: {ref}"]
    text = path.read_text(encoding="utf-8")
    status = deliverable_status(text)
    if status not in DELIVERABLE_STATUSES:
        errors.append("primary deliverable must include Status: Draft, In Review, or Frozen")
    if require_frozen and status != "Frozen":
        errors.append("primary deliverable status must be Frozen")
    for section in deliverable_sections(primary):
        if not markdown_heading_present(text, section):
            errors.append(f"primary deliverable missing required section: {section}")
        elif require_frozen and not markdown_section_has_content(text, section):
            errors.append(f"primary deliverable section must not be empty when frozen: {section}")
    return errors


def validate_supporting_deliverables_content(protocol: dict[str, Any], folder: Path, frozen_docs: set[str]) -> list[str]:
    errors: list[str] = []
    for item in supporting_deliverables(protocol):
        file = str(item.get("file", ""))
        ref = resolved_deliverable_ref(protocol, file)
        path = deliverable_file_path(folder, protocol, file)
        if not path.exists():
            errors.append(f"supporting deliverable missing: {ref}")
            continue
        text = path.read_text(encoding="utf-8")
        status = deliverable_status(text)
        if status not in DELIVERABLE_STATUSES:
            errors.append(f"supporting deliverable {ref} must include Status")
        require_frozen = bool(item.get("frozen")) or ref in frozen_docs
        if require_frozen and status != "Frozen":
            errors.append(f"supporting deliverable {ref} status must be Frozen")
        for section in deliverable_sections(item):
            if not markdown_heading_present(text, section):
                errors.append(f"supporting deliverable {ref} missing required section: {section}")
            elif require_frozen and not markdown_section_has_content(text, section):
                errors.append(f"supporting deliverable {ref} section must not be empty when frozen: {section}")
    return errors


def validate_decisions_document(folder: Path, protocol: dict[str, Any]) -> list[str]:
    path = folder / "decisions.md"
    if not path.exists():
        return ["missing decisions.md"]
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r"^###\s+(.+)$", text, flags=re.MULTILINE)
    errors: list[str] = []
    seen: set[str] = set()
    primary_ref = primary_deliverable_ref(protocol)
    for index, heading in enumerate(headings, start=1):
        match = re.match(r"(D\d+)\.\s+.+", heading)
        decision_id = f"D{index}"
        if not match:
            errors.append("accepted decision headings must use D<number>")
        else:
            decision_id = match.group(1)
            if decision_id in seen:
                errors.append(f"duplicate accepted decision id {decision_id}")
            seen.add(decision_id)
            if decision_id != f"D{index}":
                errors.append("accepted decision ids must be sequential")
        block_pattern = re.compile(r"^###\s+" + re.escape(heading) + r"\s*$([\s\S]*?)(?=^###\s+|\Z)", re.MULTILINE)
        block = block_pattern.search(text)
        body = block.group(1) if block else ""
        if "- Decision:" not in body:
            errors.append(f"accepted decision {decision_id} requires Decision")
        if "- Reflected in:" not in body:
            errors.append(f"accepted decision {decision_id} requires Reflected in")
        elif primary_ref not in body and not any(resolved_deliverable_ref(protocol, str(item.get("file", ""))) in body for item in supporting_deliverables(protocol)):
            errors.append(f"accepted decision {decision_id} Reflected in must point to declared deliverable")
    return errors


def validate_deliverable_events(folder: Path, protocol: dict[str, Any], events: list[dict[str, Any]]) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    frozen_docs: set[str] = set()
    primary_freezes = 0
    for event in events:
        name = event.get("event")
        if not isinstance(name, str) or not name.startswith("deliverable_"):
            continue
        seq = event.get("seq")
        role = event.get("role")
        doc = event.get("doc")
        if role not in {"primary", "supporting"} or not isinstance(doc, str):
            continue
        try:
            file = event_deliverable_file(protocol, doc, role)
            path = deliverable_file_path(folder, protocol, file)
        except ProtocolError as exc:
            errors.append(f"seq {seq}: {exc}")
            continue
        if name == "deliverable_frozen":
            sha = event.get("sha256")
            if not is_lower_hex_sha256(sha):
                errors.append(f"seq {seq}: deliverable_frozen requires sha256")
                continue
            if not path.exists():
                errors.append(f"seq {seq}: deliverable_frozen doc does not exist")
                continue
            actual = file_sha256(path)
            if actual != sha:
                errors.append(f"seq {seq}: deliverable_frozen sha256 does not match current file")
            frozen_docs.add(doc)
            if role == "primary":
                primary_freezes += 1
    if primary_freezes > 1:
        errors.append("primary deliverable can be frozen only once")
    for item in supporting_deliverables(protocol):
        ref = resolved_deliverable_ref(protocol, str(item.get("file", "")))
        if item.get("frozen") and ref not in frozen_docs:
            errors.append(f"supporting deliverable requires deliverable_frozen: {ref}")
        if not item.get("frozen") and ref in frozen_docs:
            errors.append(f"supporting deliverable has freeze event but is not marked frozen: {ref}")
    return errors, frozen_docs


def validate_attachments(protocol: dict[str, Any], folder: Path) -> list[str]:
    errors: list[str] = []
    attachments = deliverables_config(protocol).get("attachments", [])
    if not isinstance(attachments, list):
        return errors
    for item in attachments:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str):
            continue
        path = deliverable_file_path(folder, protocol, item["file"])
        if not path.exists():
            errors.append(f"attachment missing: {item['file']}")
    return errors


def validate_folder(folder: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for name in REQUIRED_FILES:
        if not (folder / name).exists():
            errors.append(f"missing {name}")
    for name in FORBIDDEN_FILES:
        if (folder / name).exists():
            errors.append(f"{name} is not part of the protocol; remove it and use events.jsonl/readiness.md instead")

    try:
        protocol = load_protocol(folder)
    except ProtocolError as exc:
        return [str(exc), *errors], warnings

    if protocol.get("protocol") != PROTOCOL_NAME:
        errors.append("protocol.json protocol must be 'acp'")
    if protocol.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("protocol.json schemaVersion must be 2")
    if protocol.get("currentPhase") not in PHASES:
        errors.append(f"currentPhase must be one of {sorted(PHASES)}")
    if not protocol.get("objective"):
        errors.append("protocol.json objective must not be blank")
    if not participant_ids(protocol):
        errors.append("protocol.json participants must not be empty")
    gates = protocol.get("completionGates")
    if not isinstance(gates, list) or not gates:
        errors.append("protocol.json completionGates must not be empty")
    else:
        for index, gate in enumerate(gates, start=1):
            if (
                not isinstance(gate, dict)
                or gate.get("source") not in {"objective", "generated"}
                or not isinstance(gate.get("text"), str)
                or not gate["text"].strip()
            ):
                errors.append(f"completionGates[{index}] must include source and text")
            elif isinstance(gate.get("text"), str):
                for forbidden in FORBIDDEN_PROTOCOL_REFERENCES:
                    if forbidden in gate["text"]:
                        errors.append(f"completion gate must not reference obsolete file {forbidden}")
    if "waitingFor" not in protocol:
        errors.append("protocol.json waitingFor must be present")
    if "proposalOwner" not in protocol:
        errors.append("protocol.json proposalOwner must be present")
    deliverable_schema_errors = validate_deliverables_schema(protocol, folder)
    errors.extend(deliverable_schema_errors)

    events, event_errors = read_events(folder)
    errors.extend(event_errors)
    errors.extend(validate_event_shape(events))
    errors.extend(validate_review_links(folder, events, protocol))
    deliverable_event_errors, frozen_docs = validate_deliverable_events(folder, protocol, events)
    errors.extend(deliverable_event_errors)
    has_deliverable_frozen = any(event.get("event") == "deliverable_frozen" and event.get("role") == "primary" for event in events)
    derived_state, phase_errors = derive_state(protocol, events, folder)
    errors.extend(phase_errors)
    derived_phase = derived_state["currentPhase"]
    if derived_phase and protocol.get("currentPhase") != derived_phase:
        errors.append(f"protocol.json currentPhase is {protocol.get('currentPhase')}, expected {derived_phase}")
    for field in ("proposalOwner", "waitingFor"):
        expected = derived_state[field]
        if field in protocol and expected is not None and protocol.get(field) != expected:
            errors.append(f"protocol.json {field} is {protocol.get(field)!r}, expected {expected!r}")

    readiness = readiness_scan(folder)
    has_decision_acceptance = any(event.get("event") == "decision_accepted" for event in events)
    has_readiness_passed = any(event.get("event") == "readiness_passed" for event in events)
    has_completed = any(event.get("event") == "completed" for event in events)
    require_frozen_content = has_deliverable_frozen or has_readiness_passed or has_completed
    if not deliverable_schema_errors:
        errors.extend(validate_primary_deliverable_content(protocol, folder, require_frozen_content))
        errors.extend(validate_supporting_deliverables_content(protocol, folder, frozen_docs))
        errors.extend(validate_decisions_document(folder, protocol))
        errors.extend(validate_attachments(protocol, folder))
    if readiness["blocking"] and has_decision_acceptance:
        errors.append("blocking readiness items must be cleared before decision_accepted")
    if has_decision_acceptance:
        if readiness["unresolved"]:
            errors.append("unresolved readiness questions must be classified before decision_accepted")
        if readiness["deferred_missing_reason"]:
            errors.append("deferred_nonblocking readiness items require a reason before decision_accepted")
    if has_readiness_passed or has_completed:
        if readiness["blocking"]:
            errors.append("blocking readiness items must be cleared before readiness_passed or completed")
        if readiness["unresolved"]:
            errors.append("unresolved readiness questions must be classified before readiness_passed or completed")
        if readiness["deferred_missing_reason"]:
            errors.append("deferred_nonblocking readiness items require a reason")
        if not readiness["ready_to_implement"]:
            errors.append("readiness.md must check 'Ready to implement' before readiness_passed or completed")
        if not has_deliverable_frozen:
            errors.append("readiness_passed requires primary deliverable_frozen")
    if has_completed:
        missing_gates = missing_completion_gates(protocol, readiness["text"])
        if missing_gates:
            errors.append("completion gates must be checked before completed: " + ", ".join(missing_gates))
        errors.extend(validate_conclusion_for_completion(folder, protocol))
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
    role: str | None = None,
    sha256: str | None = None,
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
    if events and reply_to is None:
        raise ProtocolError("reply_to is required after initialized")

    if event_name.startswith("deliverable_"):
        if role not in {"primary", "supporting"}:
            raise ProtocolError("deliverable events require role")
        if not doc:
            raise ProtocolError("deliverable events require doc")
        file = event_deliverable_file(protocol, doc, role)
        deliverable_path = deliverable_file_path(folder, protocol, file)
        if event_name == "deliverable_frozen":
            if not is_lower_hex_sha256(sha256):
                raise ProtocolError("deliverable_frozen requires sha256")
            if not deliverable_path.exists():
                raise ProtocolError("deliverable_frozen doc does not exist")
            actual = file_sha256(deliverable_path)
            if actual != sha256:
                raise ProtocolError("deliverable_frozen sha256 does not match current file")

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
    if role:
        payload["role"] = role
    if sha256:
        payload["sha256"] = sha256

    candidate_events = [*events, payload]
    derived_state, phase_errors = derive_state(protocol, candidate_events, folder)
    if phase_errors:
        raise ProtocolError("; ".join(phase_errors))
    readiness = readiness_scan(folder)
    if event_name in {"decision_accepted", "readiness_passed", "completed"} and readiness["blocking"]:
        raise ProtocolError("blocking readiness items must be cleared first")
    if event_name == "decision_accepted":
        if readiness["unresolved"]:
            raise ProtocolError("unresolved readiness questions must be classified first")
        if readiness["deferred_missing_reason"]:
            raise ProtocolError("deferred_nonblocking readiness items require a reason")
    if event_name in {"readiness_passed", "completed"}:
        if readiness["unresolved"]:
            raise ProtocolError("unresolved readiness questions must be classified first")
        if readiness["deferred_missing_reason"]:
            raise ProtocolError("deferred_nonblocking readiness items require a reason")
        if not readiness["ready_to_implement"]:
            raise ProtocolError("readiness.md must check 'Ready to implement' first")
    if event_name == "completed":
        if doc != "conclusion.md":
            raise ProtocolError("completed must reference conclusion.md")
        missing_gates = missing_completion_gates(protocol, readiness["text"])
        if missing_gates:
            raise ProtocolError("completion gates must be checked first: " + ", ".join(missing_gates))
        conclusion_errors = validate_conclusion_for_completion(folder, protocol)
        if conclusion_errors:
            raise ProtocolError("; ".join(conclusion_errors))
    append_jsonl(folder / "events.jsonl", payload)
    if derived_state["currentPhase"]:
        protocol["currentPhase"] = derived_state["currentPhase"]
        protocol["proposalOwner"] = derived_state["proposalOwner"]
        protocol["waitingFor"] = derived_state["waitingFor"]
        write_protocol(folder, protocol)
    return payload
