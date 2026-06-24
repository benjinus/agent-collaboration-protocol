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
            self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 4).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 4).returncode, 0)
            blocked = self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 6)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("unresolved readiness", blocked.stderr)

            self.write_valid_readiness(folder)
            ready = self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 6)
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
            self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 4).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 4).returncode, 0)
            self.assertEqual(self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 6).returncode, 0)
            completed = self.append(folder, "server", "completed", "done", "decisions.md", 7)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("completion gates", completed.stderr)

if __name__ == "__main__":
    unittest.main()
