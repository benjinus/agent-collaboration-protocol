#!/usr/bin/env python3
import argparse
from pathlib import Path

from _acp import ProtocolError, load_protocol, participant_ids, read_events, readiness_scan, validate_conclusion_for_completion


def last_event(events: list[dict], event_name: str | None = None) -> dict | None:
    for event in reversed(events):
        if event_name is None or event.get("event") == event_name:
            return event
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Show the next portable ACP action for a participant.")
    parser.add_argument("--folder", required=True, help="Collaboration folder")
    parser.add_argument("--participant", required=True, help="Participant id")
    args = parser.parse_args()
    folder = Path(args.folder).expanduser().resolve()

    try:
        protocol = load_protocol(folder)
    except ProtocolError as exc:
        parser.exit(2, f"error: {exc}\n")
    if args.participant not in participant_ids(protocol):
        parser.exit(2, f"error: participant {args.participant!r} is not listed in protocol.json\n")
    events, errors = read_events(folder)
    if errors:
        parser.exit(2, "error: " + "; ".join(errors) + "\n")

    phase = protocol.get("currentPhase")
    waiting_for = protocol.get("waitingFor") if isinstance(protocol.get("waitingFor"), list) else []
    proposal_owner = protocol.get("proposalOwner")
    recent = last_event(events)
    readiness = readiness_scan(folder)
    print(f"phase: {phase}")
    print(f"proposal owner: {proposal_owner}")
    print("waiting for: " + (", ".join(waiting_for) if waiting_for else "none"))
    if recent:
        print(f"last event: seq {recent.get('seq')} {recent.get('event')} from {recent.get('from')}")

    if phase == "drafting":
        if args.participant in waiting_for:
            print("next action: draft the primary deliverable, append deliverable_drafted, update proposal.md, then append proposal_submitted.")
        else:
            print("next action: wait for the proposal owner to submit the proposal.")
    elif phase == "reviewing":
        proposal = last_event(events, "proposal_submitted") or last_event(events, "proposal_revised")
        if args.participant in waiting_for and proposal and proposal.get("from") != args.participant:
            print("next action: review proposal.md and the primary deliverable, update review.md with Review Scope, then append review_submitted.")
        elif args.participant == proposal_owner:
            print("next action: wait for the listed reviewer(s); do not edit proposal.md or deliverables while reviewing unless blocking the collaboration.")
        else:
            print("next action: wait for the listed reviewer(s) to submit review_submitted or blocked.")
    elif phase == "revising":
        review = last_event(events, "review_submitted")
        if args.participant in waiting_for and review and review.get("from") != args.participant:
            print("next action: revise proposal.md and deliverables as needed, append deliverable_revised if the deliverable changed, then append proposal_revised.")
        else:
            print("next action: wait for the proposal owner to revise.")
    elif phase == "decision_review":
        accepted = {event.get("from") for event in events if event.get("event") == "decision_accepted"}
        if args.participant in waiting_for and args.participant not in accepted:
            print("next action: review decisions.md and append decision_accepted only if decisions are explicit.")
        else:
            print("next action: wait for remaining participants to accept decisions.")
    elif phase == "readiness_check":
        if readiness["blocking"] or readiness["unresolved"] or readiness["deferred_missing_reason"]:
            print("next action: classify readiness.md questions and clear blockers before readiness_passed.")
        elif not readiness["ready_to_implement"]:
            print("next action: complete the final design checklist in readiness.md.")
        elif not any(event.get("event") == "readiness_passed" for event in events):
            print("next action: run validate_collaboration.py, then append readiness_passed.")
        elif not any(event.get("event") == "deliverable_frozen" and event.get("role") == "primary" for event in events):
            print("next action: freeze the primary deliverable with deliverable_frozen, run validate_collaboration.py, then append readiness_passed.")
        elif validate_conclusion_for_completion(folder, protocol):
            print("next action: write conclusion.md with the final outcome, deliverable receipt, readiness result, and next action.")
        else:
            print("next action: run validate_collaboration.py, then append completed with doc=conclusion.md.")
    elif phase == "completed":
        print("next action: stop; collaboration is complete.")
    elif phase == "blocked":
        print("next action: resolve the blocker or start a new collaboration round.")
    else:
        print("next action: run validate_collaboration.py; current phase is invalid.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
