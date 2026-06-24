import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_collaboration.py"
APPEND = ROOT / "scripts" / "append_event.py"
VALIDATE = ROOT / "scripts" / "validate_collaboration.py"
WAIT = ROOT / "scripts" / "wait_for_turn.py"


def run_script(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class CollaborationScriptsTest(unittest.TestCase):
    def init_folder(self, folder: Path) -> subprocess.CompletedProcess[str]:
        return run_script(
            INIT,
            "--folder",
            folder,
            "--participant",
            "server",
            "--participant",
            "reader",
            "--objective",
            "Decide protocol",
            "--completion",
            "Accepted decisions are explicit",
            "--completion",
            "Readiness passes",
        )

    def append(
        self,
        folder: Path,
        participant: str,
        event: str,
        summary: str,
        doc: str | None = None,
        reply_to: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args: list[str | Path] = [
            APPEND,
            "--folder",
            folder,
            "--participant",
            participant,
            "--event",
            event,
            "--summary",
            summary,
        ]
        if doc:
            args.extend(["--doc", doc])
        if reply_to is not None:
            args.extend(["--reply-to", str(reply_to)])
        return run_script(*args)

    def write_valid_readiness(self, folder: Path) -> None:
        (folder / "readiness.md").write_text(
            """# Readiness

## Open Question Classification

- [resolved] All questions are handled.
- [deferred_nonblocking] Tune thresholds later. Reason: implementation can start with defaults.

## Blocking Issues

- None.

## Deferred Follow-ups

- Tune thresholds later.

## Completion Gates

- [x] Accepted decisions are explicit
- [x] Readiness passes

## Final Design Document Checklist

- [x] Accepted Decisions
- [x] Assumptions
- [x] Deferred Follow-ups
- [x] Implementation Blockers
- [x] Ready to implement
""",
            encoding="utf-8",
        )

    def write_valid_conclusion(self, folder: Path, outcome: str = "proceed") -> None:
        (folder / "conclusion.md").write_text(
            f"""# Conclusion

## Decision Outcome

- [{outcome}] Implement the accepted design now.

## Rationale

The accepted decisions answer the collaboration objective and readiness has no blockers.

## Accepted Decisions

- Use the accepted decisions in decisions.md.

## Implementation Approach

Implement according to the accepted decisions.

## Assumptions

- No additional assumptions.

## Deferred Follow-ups

- None.

## Implementation Blockers

- None.

## Next Action

Start implementation.
""",
            encoding="utf-8",
        )

    def test_init_creates_protocol_structure_and_rejects_repeat_without_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            result = self.init_folder(folder)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in [
                "protocol.json",
                "events.jsonl",
                "proposal.md",
                "review.md",
                "decisions.md",
                "readiness.md",
                "conclusion.md",
            ]:
                self.assertTrue((folder / name).exists(), name)
            protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
            self.assertEqual(protocol["currentPhase"], "drafting")
            self.assertEqual(json.loads((folder / "events.jsonl").read_text(encoding="utf-8"))["event"], "initialized")

            repeat = self.init_folder(folder)
            self.assertNotEqual(repeat.returncode, 0)
            resume = run_script(INIT, "--folder", folder, "--participant", "server", "--objective", "x", "--completion", "y", "--resume")
            self.assertEqual(resume.returncode, 0, resume.stderr)

    def test_init_requires_objective_and_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_objective = run_script(
                INIT,
                "--folder",
                Path(tmp) / "a",
                "--participant",
                "server",
                "--objective",
                "",
                "--completion",
                "done",
            )
            self.assertNotEqual(missing_objective.returncode, 0)
            missing_completion = run_script(
                INIT,
                "--folder",
                Path(tmp) / "b",
                "--participant",
                "server",
                "--objective",
                "x",
            )
            self.assertNotEqual(missing_completion.returncode, 0)

    def test_append_event_assigns_seq_and_rejects_invalid_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            result = self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1)
            self.assertEqual(result.returncode, 0, result.stderr)
            events = [json.loads(line) for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[-1]["seq"], 2)
            self.assertEqual(json.loads((folder / "protocol.json").read_text(encoding="utf-8"))["currentPhase"], "reviewing")

            invalid = self.append(folder, "server", "completed", "done", "decisions.md", 2)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("completed requires", invalid.stderr)

    def test_validator_rejects_missing_reply_to_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            with (folder / "events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "seq": 2,
                            "from": "server",
                            "event": "proposal_submitted",
                            "at": "2026-01-01T00:00:00Z",
                            "summary": "bad reply",
                            "reply_to": 99,
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("reply_to", result.stdout)

    def test_append_requires_reply_to_after_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            result = self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("reply_to is required after initialized", result.stderr)

    def test_validator_rejects_review_seq_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 2).returncode, 0)
            (folder / "review.md").write_text(
                """# Review

## 2026-01-01T00:00:00Z - reader - seq 2

Context:
- wrong seq.
""",
                encoding="utf-8",
            )
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("review.md heading seq 2", result.stdout)

    def test_validator_rejects_review_participant_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 2).returncode, 0)
            (folder / "review.md").write_text(
                """# Review

## 2026-01-01T00:00:00Z - server - seq 3

Context:
- wrong participant.
""",
                encoding="utf-8",
            )
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("participant 'server' does not match event from 'reader'", result.stdout)

    def test_quality_gate_blocks_readiness_until_questions_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 2).returncode, 0)
            (folder / "review.md").write_text(
                """# Review

## 2026-01-01T00:00:00Z - reader - seq 3

Context:
- Read proposal.
""",
                encoding="utf-8",
            )
            self.assertEqual(self.append(folder, "server", "proposal_revised", "proposal revised", "proposal.md", 3).returncode, 0)
            decision = self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 4)
            self.assertNotEqual(decision.returncode, 0)
            self.assertIn("unresolved readiness", decision.stderr)

            blocked = self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 4)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("readiness_passed is not allowed from phase decision_review", blocked.stderr)

            self.write_valid_readiness(folder)
            self.assertEqual(self.append(folder, "server", "question_classified", "questions classified", "readiness.md", 4).returncode, 0)
            self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 5).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 6).returncode, 0)
            ready = self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 7)
            self.assertEqual(ready.returncode, 0, ready.stderr)

    def test_completed_requires_readiness_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.write_valid_readiness(folder)
            with (folder / "events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "seq": 2,
                            "from": "server",
                            "event": "completed",
                            "at": "2026-01-01T00:00:00Z",
                            "summary": "done",
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("completed requires", result.stdout)

    def test_completed_requires_checked_completion_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.write_valid_readiness(folder)
            text = (folder / "readiness.md").read_text(encoding="utf-8")
            text = text.replace("- [x] Readiness passes", "- [ ] Readiness passes")
            (folder / "readiness.md").write_text(text, encoding="utf-8")
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 2).returncode, 0)
            (folder / "review.md").write_text(
                """# Review

## 2026-01-01T00:00:00Z - reader - seq 3

Context:
- Read proposal.
""",
                encoding="utf-8",
            )
            self.assertEqual(self.append(folder, "server", "proposal_revised", "proposal revised", "proposal.md", 3).returncode, 0)
            self.assertEqual(self.append(folder, "server", "question_classified", "questions classified", "readiness.md", 4).returncode, 0)
            self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 5).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 6).returncode, 0)
            self.assertEqual(self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 7).returncode, 0)
            self.write_valid_conclusion(folder)
            completed = self.append(folder, "server", "completed", "done", "conclusion.md", 8)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("completion gates", completed.stderr)

    def test_completed_requires_complete_conclusion_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.write_valid_readiness(folder)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 2).returncode, 0)
            (folder / "review.md").write_text(
                """# Review

## 2026-01-01T00:00:00Z - reader - seq 3

Context:
- Read proposal.
""",
                encoding="utf-8",
            )
            self.assertEqual(self.append(folder, "server", "proposal_revised", "proposal revised", "proposal.md", 3).returncode, 0)
            self.assertEqual(self.append(folder, "server", "question_classified", "questions classified", "readiness.md", 4).returncode, 0)
            self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 5).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 6).returncode, 0)
            self.assertEqual(self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 7).returncode, 0)

            wrong_doc = self.append(folder, "server", "completed", "done", "decisions.md", 8)
            self.assertEqual(wrong_doc.returncode, 2)
            self.assertIn("completed must reference conclusion.md", wrong_doc.stderr)

            incomplete = self.append(folder, "server", "completed", "done", "conclusion.md", 8)
            self.assertEqual(incomplete.returncode, 2)
            self.assertIn("conclusion.md", incomplete.stderr)

            self.write_valid_conclusion(folder)
            completed = self.append(folder, "server", "completed", "done", "conclusion.md", 8)
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_validator_rejects_completed_with_incomplete_conclusion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.write_valid_readiness(folder)
            manual_events = [
                {"seq": 2, "from": "server", "event": "proposal_submitted", "at": "2026-01-01T00:00:01Z", "summary": "proposal", "reply_to": 1},
                {"seq": 3, "from": "reader", "event": "review_submitted", "at": "2026-01-01T00:00:02Z", "summary": "review", "reply_to": 2},
                {"seq": 4, "from": "server", "event": "proposal_revised", "at": "2026-01-01T00:00:03Z", "summary": "revised", "reply_to": 3},
                {"seq": 5, "from": "server", "event": "question_classified", "at": "2026-01-01T00:00:04Z", "summary": "classified", "reply_to": 4},
                {"seq": 6, "from": "server", "event": "decision_accepted", "at": "2026-01-01T00:00:05Z", "summary": "server accepts", "reply_to": 5},
                {"seq": 7, "from": "reader", "event": "decision_accepted", "at": "2026-01-01T00:00:06Z", "summary": "reader accepts", "reply_to": 6},
                {"seq": 8, "from": "server", "event": "readiness_passed", "at": "2026-01-01T00:00:07Z", "summary": "ready", "reply_to": 7},
                {"seq": 9, "from": "server", "event": "completed", "at": "2026-01-01T00:00:08Z", "summary": "done", "doc": "conclusion.md", "reply_to": 8},
            ]
            with (folder / "events.jsonl").open("a", encoding="utf-8") as handle:
                for event in manual_events:
                    handle.write(json.dumps(event, separators=(",", ":")) + "\n")
            (folder / "review.md").write_text(
                """# Review

## 2026-01-01T00:00:02Z - reader - seq 3

Context:
- Read proposal.
""",
                encoding="utf-8",
            )
            protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
            protocol["currentPhase"] = "completed"
            protocol["waitingFor"] = []
            (folder / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False), encoding="utf-8")

            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("conclusion.md", result.stdout)

    def test_proposal_owner_must_wait_during_reviewing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)

            premature = self.append(folder, "server", "proposal_revised", "proposal revised", "proposal.md", 2)
            self.assertNotEqual(premature.returncode, 0)
            self.assertIn("proposal_revised is not allowed from phase reviewing", premature.stderr)

            action = run_script(ROOT / "scripts" / "next_action.py", "--folder", folder, "--participant", "server")
            self.assertEqual(action.returncode, 0, action.stderr)
            self.assertIn("wait for the listed reviewer", action.stdout)
            self.assertIn("do not edit proposal.md", action.stdout)

    def test_wait_for_turn_returns_when_participant_is_waiting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)

            result = run_script(
                WAIT,
                "--folder",
                folder,
                "--participant",
                "server",
                "--timeout",
                "1",
                "--interval",
                "0.1",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ready: server is listed in waitingFor", result.stdout)
            self.assertIn("next action: update proposal.md", result.stdout)

    def test_wait_for_turn_documents_default_timeout(self) -> None:
        result = run_script(WAIT, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("defaults to 1800 seconds", result.stdout)
        self.assertIn("0 for no timeout", result.stdout)

    def test_wait_for_turn_times_out_when_participant_is_not_waiting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)

            result = run_script(
                WAIT,
                "--folder",
                folder,
                "--participant",
                "server",
                "--timeout",
                "0.2",
                "--interval",
                "0.1",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("waiting for reader", result.stdout)
            self.assertIn("timeout: waiting for reader", result.stderr)

    def test_wait_for_turn_returns_on_completed_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.write_valid_readiness(folder)
            self.write_valid_conclusion(folder)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 2).returncode, 0)
            (folder / "review.md").write_text(
                """# Review

## 2026-01-01T00:00:00Z - reader - seq 3

Context:
- Read proposal.
""",
                encoding="utf-8",
            )
            self.assertEqual(self.append(folder, "server", "proposal_revised", "proposal revised", "proposal.md", 3).returncode, 0)
            self.assertEqual(self.append(folder, "server", "question_classified", "questions classified", "readiness.md", 4).returncode, 0)
            self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 5).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 6).returncode, 0)
            self.assertEqual(self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 7).returncode, 0)
            self.assertEqual(self.append(folder, "server", "completed", "done", "conclusion.md", 8).returncode, 0)

            result = run_script(
                WAIT,
                "--folder",
                folder,
                "--participant",
                "reader",
                "--timeout",
                "1",
                "--interval",
                "0.1",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ready: phase is completed", result.stdout)
            self.assertIn("next action: stop; collaboration is complete", result.stdout)

    def test_validator_rejects_obsolete_files_and_completion_gate_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            (folder / "state.log").write_text("old state\n", encoding="utf-8")
            protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
            protocol["completionGates"].append("state.log has completion")
            (folder / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False), encoding="utf-8")

            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("state.log is not part of the protocol", result.stdout)
            self.assertIn("completion gate must not reference obsolete file state.log", result.stdout)

    def test_validator_rejects_event_time_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            with (folder / "events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "seq": 2,
                            "from": "server",
                            "event": "proposal_submitted",
                            "at": "2026-01-01T00:00:00Z",
                            "summary": "proposal",
                            "reply_to": 1,
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "seq": 3,
                            "from": "reader",
                            "event": "review_submitted",
                            "at": "2025-12-31T23:59:59Z",
                            "summary": "review",
                            "reply_to": 2,
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            (folder / "review.md").write_text(
                """# Review

## 2025-12-31T23:59:59Z - reader - seq 3

Context:
- Read proposal.
""",
                encoding="utf-8",
            )

            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("at must not be earlier than the previous event", result.stdout)

if __name__ == "__main__":
    unittest.main()
