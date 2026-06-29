import hashlib
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
NEXT_ACTION = ROOT / "scripts" / "next_action.py"
DOC_SUFFIXES = {".md", ".yaml", ".yml"}


def run_script(*args: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class CollaborationScriptsTest(unittest.TestCase):
    def test_packaged_docs_use_current_repo_owner(self) -> None:
        docs = {
            path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
            for path in ROOT.rglob("*")
            if path.is_file() and path.suffix in DOC_SUFFIXES and ".git" not in path.parts
        }
        stale_paths = [name for name, text in docs.items() if "benjinus" in text]
        self.assertEqual(stale_paths, [])

        install_reference = docs["references/open-agent-installation.md"]
        self.assertIn("npx skills add agi-connect/agent-collaboration-protocol", install_reference)
        self.assertIn("https://github.com/agi-connect/agent-collaboration-protocol.git", install_reference)

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
            "Decide ACP deliverable protocol",
            "--primary-deliverable-type",
            "design-spec",
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
        role: str | None = None,
        sha256: str | None = None,
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
        if role:
            args.extend(["--role", role])
        if sha256:
            args.extend(["--sha256", sha256])
        return run_script(*args)

    def write_valid_review(self, folder: Path, seq: int) -> None:
        (folder / "review.md").write_text(
            f"""# Review

## 2026-01-01T00:00:00Z - reader - seq {seq}

Context:
- Read `proposal.md` after event seq `{seq - 1}`.
- Reviewed primary deliverable: `deliverables/design-spec.md`
- Reviewed supporting deliverables: none.

Review Scope:
- Proposal coherence
- Primary deliverable completeness
- Accepted decision traceability
- Implementation readiness

Position:
- Accept with required revisions.

Concerns:
- None.

Required Changes:
- None.

Questions:
- None.
""",
            encoding="utf-8",
        )

    def write_valid_decisions(self, folder: Path) -> None:
        (folder / "decisions.md").write_text(
            """# Decisions

## Accepted Decisions

### D1. Use deliverable-aware ACP

- Decision: ACP requires a declared primary deliverable.
- Rationale: The final output must be separable from protocol receipt files.
- Reflected in: `deliverables/design-spec.md#proposed-design`
""",
            encoding="utf-8",
        )

    def freeze_primary(self, folder: Path, reply_to: int) -> tuple[str, subprocess.CompletedProcess[str]]:
        deliverable = folder / "deliverables" / "design-spec.md"
        text = deliverable.read_text(encoding="utf-8").replace("Status: Draft", "Status: Frozen")
        for section in [
            "Problem",
            "Goals",
            "Non-goals",
            "Proposed Design",
            "Interfaces / Contracts",
            "Failure Modes",
            "Validation Plan",
            "Open Questions",
        ]:
            text = text.replace(f"## {section}\n\n", f"## {section}\n\nContent for {section}.\n\n")
        deliverable.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(deliverable.read_bytes()).hexdigest()
        result = self.append(
            folder,
            "server",
            "deliverable_frozen",
            "primary deliverable frozen",
            "deliverables/design-spec.md",
            reply_to,
            role="primary",
            sha256=digest,
        )
        return digest, result

    def write_valid_readiness(self, folder: Path, sha256: str) -> None:
        (folder / "readiness.md").write_text(
            f"""# Readiness

## Open Question Classification

- [resolved] All questions are handled.
- [deferred_nonblocking] Tune thresholds later. Reason: implementation can start with defaults.

## Blocking Issues

- None.

## Objective Gates

- [x] Accepted decisions are explicit
- [x] Readiness passes

## Generated Deliverable Gates

- [x] Primary deliverable exists: `deliverables/design-spec.md`
- [x] Primary deliverable has required `design-spec` sections
- [x] Every accepted decision has `Reflected in`
- [x] Every accepted decision is reflected in the primary deliverable
- [x] Primary deliverable status is `Frozen`
- [x] Primary deliverable SHA-256 snapshot recorded

## Deliverable Snapshot

- Primary: `deliverables/design-spec.md`
- SHA-256: {sha256}

## Supporting Deliverables

- None.

## Attachments

- None.

## Deferred Follow-ups

- Tune thresholds later.

## Implementation Blockers

- None.

## Ready to Implement

- [x] Ready to implement
""",
            encoding="utf-8",
        )

    def write_valid_conclusion(self, folder: Path, sha256: str, outcome: str = "proceed") -> None:
        (folder / "conclusion.md").write_text(
            f"""# Conclusion

## Decision Outcome

- [{outcome}] Implement the accepted design now.

## Rationale

The accepted decisions answer the collaboration objective and readiness has no blockers.

## Deliverable Receipt

- Primary: `deliverables/design-spec.md`
- Type: `design-spec`
- SHA-256: {sha256}
- Supporting: none
- Attachments: none

## Accepted Decisions Summary

- D1. Use deliverable-aware ACP.

## Readiness Result

- Objective gates: passed
- Generated deliverable gates: passed
- Readiness file: `readiness.md`

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

    def complete_happy_path(self, folder: Path) -> str:
        self.assertEqual(self.append(folder, "server", "deliverable_drafted", "draft ready", "deliverables/design-spec.md", 1, role="primary").returncode, 0)
        self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 2).returncode, 0)
        self.write_valid_review(folder, seq=4)
        self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 3).returncode, 0)
        self.assertEqual(self.append(folder, "server", "proposal_revised", "proposal revised", "proposal.md", 4).returncode, 0)
        self.write_valid_decisions(folder)
        self.write_valid_readiness(folder, "0" * 64)
        self.assertEqual(self.append(folder, "server", "question_classified", "questions classified", "readiness.md", 5).returncode, 0)
        self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 6).returncode, 0)
        self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 7).returncode, 0)
        sha256, frozen = self.freeze_primary(folder, 8)
        self.assertEqual(frozen.returncode, 0, frozen.stderr)
        self.write_valid_readiness(folder, sha256)
        self.assertEqual(self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 9).returncode, 0)
        self.write_valid_conclusion(folder, sha256)
        self.assertEqual(self.append(folder, "server", "completed", "done", "conclusion.md", 10).returncode, 0)
        return sha256

    def test_init_creates_v2_protocol_and_deliverable_templates(self) -> None:
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
                "deliverables/design-spec.md",
            ]:
                self.assertTrue((folder / name).exists(), name)
            protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
            self.assertEqual(protocol["protocol"], "acp")
            self.assertEqual(protocol["schemaVersion"], 2)
            self.assertEqual(protocol["currentPhase"], "drafting")
            self.assertEqual(protocol["deliverables"]["mode"], "internal")
            self.assertEqual(protocol["deliverables"]["dir"], "deliverables")
            self.assertEqual(protocol["deliverables"]["primary"]["type"], "design-spec")
            self.assertEqual(protocol["deliverables"]["primary"]["file"], "design-spec.md")
            self.assertEqual(protocol["deliverables"]["owner"], "server")
            self.assertEqual(protocol["completionGates"][0]["source"], "objective")
            self.assertTrue(any(gate["source"] == "generated" for gate in protocol["completionGates"]))
            events = [json.loads(line) for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["event"], "initialized")
            self.assertIn("Status: Draft", (folder / "deliverables" / "design-spec.md").read_text(encoding="utf-8"))

            repeat = self.init_folder(folder)
            self.assertNotEqual(repeat.returncode, 0)
            resume = run_script(
                INIT,
                "--folder",
                folder,
                "--participant",
                "server",
                "--participant",
                "reader",
                "--objective",
                "x",
                "--primary-deliverable-type",
                "design-spec",
                "--completion",
                "y",
                "--resume",
            )
            self.assertEqual(resume.returncode, 0, resume.stderr)

    def test_init_requires_custom_deliverable_file_and_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_file = run_script(
                INIT,
                "--folder",
                Path(tmp) / "custom-a",
                "--participant",
                "agent-a",
                "--participant",
                "agent-b",
                "--objective",
                "Decide custom output",
                "--primary-deliverable-type",
                "custom",
                "--completion",
                "Custom output is ready",
            )
            self.assertNotEqual(missing_file.returncode, 0)
            self.assertIn("custom deliverables require --primary-deliverable-file", missing_file.stderr)

            missing_checklist = run_script(
                INIT,
                "--folder",
                Path(tmp) / "custom-b",
                "--participant",
                "agent-a",
                "--participant",
                "agent-b",
                "--objective",
                "Decide custom output",
                "--primary-deliverable-type",
                "custom",
                "--primary-deliverable-file",
                "custom-output.md",
                "--completion",
                "Custom output is ready",
            )
            self.assertNotEqual(missing_checklist.returncode, 0)
            self.assertIn("custom deliverables require at least one --primary-deliverable-check", missing_checklist.stderr)

    def test_deliverable_events_require_role_and_valid_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)

            missing_role = self.append(folder, "server", "deliverable_drafted", "draft ready", "deliverables/design-spec.md", 1)
            self.assertEqual(missing_role.returncode, 2)
            self.assertIn("deliverable events require role", missing_role.stderr)

            wrong_doc = self.append(folder, "server", "deliverable_drafted", "draft ready", "proposal.md", 1, role="primary")
            self.assertEqual(wrong_doc.returncode, 2)
            self.assertIn("doc must reference the primary deliverable", wrong_doc.stderr)

            ok = self.append(folder, "server", "deliverable_drafted", "draft ready", "deliverables/design-spec.md", 1, role="primary")
            self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_deliverable_frozen_requires_sha256_and_matching_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(
                self.append(folder, "server", "deliverable_drafted", "draft ready", "deliverables/design-spec.md", 1, role="primary").returncode,
                0,
            )

            missing_hash = self.append(folder, "server", "deliverable_frozen", "frozen", "deliverables/design-spec.md", 2, role="primary")
            self.assertEqual(missing_hash.returncode, 2)
            self.assertIn("deliverable_frozen requires sha256", missing_hash.stderr)

            wrong_hash = "0" * 64
            bad = self.append(folder, "server", "deliverable_frozen", "frozen", "deliverables/design-spec.md", 2, role="primary", sha256=wrong_hash)
            self.assertEqual(bad.returncode, 2)
            self.assertIn("sha256 does not match", bad.stderr)

    def test_proposal_submitted_requires_primary_deliverable_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            blocked = self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 1)
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("proposal_submitted requires prior primary deliverable_drafted", blocked.stderr)

            self.assertEqual(
                self.append(folder, "server", "deliverable_drafted", "draft ready", "deliverables/design-spec.md", 1, role="primary").returncode,
                0,
            )
            ok = self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 2)
            self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_readiness_passed_requires_primary_deliverable_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(self.append(folder, "server", "deliverable_drafted", "draft ready", "deliverables/design-spec.md", 1, role="primary").returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 2).returncode, 0)
            self.write_valid_review(folder, seq=4)
            self.assertEqual(self.append(folder, "reader", "review_submitted", "review ready", "review.md", 3).returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_revised", "proposal revised", "proposal.md", 4).returncode, 0)
            self.write_valid_decisions(folder)
            self.write_valid_readiness(folder, "0" * 64)
            self.assertEqual(self.append(folder, "server", "question_classified", "questions classified", "readiness.md", 5).returncode, 0)
            self.assertEqual(self.append(folder, "server", "decision_accepted", "server accepts", "decisions.md", 6).returncode, 0)
            self.assertEqual(self.append(folder, "reader", "decision_accepted", "reader accepts", "decisions.md", 7).returncode, 0)
            blocked = self.append(folder, "server", "readiness_passed", "ready", "readiness.md", 8)
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("readiness_passed requires primary deliverable_frozen", blocked.stderr)

    def test_validator_rejects_protocol_without_v2_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            folder.mkdir()
            (folder / "protocol.json").write_text(
                json.dumps(
                    {
                        "objective": "legacy",
                        "participants": [{"id": "server"}, {"id": "reader"}],
                        "completionGates": ["done"],
                        "currentPhase": "drafting",
                        "proposalOwner": "server",
                        "waitingFor": ["server"],
                    }
                ),
                encoding="utf-8",
            )
            for name in ["events.jsonl", "proposal.md", "review.md", "decisions.md", "readiness.md", "conclusion.md"]:
                (folder / name).write_text("\n", encoding="utf-8")
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("protocol.json protocol must be 'acp'", result.stdout)
            self.assertIn("protocol.json schemaVersion must be 2", result.stdout)
            self.assertIn("protocol.json deliverables.primary is required", result.stdout)

    def test_validator_rejects_decisions_without_stable_ids_and_reflected_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            (folder / "decisions.md").write_text(
                """# Decisions

## Accepted Decisions

### 1. Bad heading

- Decision: Bad format.
""",
                encoding="utf-8",
            )
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("accepted decision headings must use D<number>", result.stdout)
            self.assertIn("accepted decision D1 requires Reflected in", result.stdout)

    def test_completed_happy_path_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.complete_happy_path(folder)
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
            self.assertEqual(protocol["currentPhase"], "completed")
            self.assertEqual(protocol["waitingFor"], [])

    def test_validator_rejects_hash_change_after_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.complete_happy_path(folder)
            deliverable = folder / "deliverables" / "design-spec.md"
            deliverable.write_text(deliverable.read_text(encoding="utf-8") + "\nChanged after freeze.\n", encoding="utf-8")
            result = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(result.returncode, 2)
            self.assertIn("deliverable_frozen sha256 does not match current file", result.stdout)

    def test_wait_for_turn_returns_when_participant_is_waiting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            result = run_script(WAIT, "--folder", folder, "--participant", "server", "--timeout", "1", "--interval", "0.1")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ready: server is listed in waitingFor", result.stdout)
            self.assertIn("next action: draft the primary deliverable", result.stdout)

    def test_next_action_owner_waits_during_reviewing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.assertEqual(self.append(folder, "server", "deliverable_drafted", "draft ready", "deliverables/design-spec.md", 1, role="primary").returncode, 0)
            self.assertEqual(self.append(folder, "server", "proposal_submitted", "proposal ready", "proposal.md", 2).returncode, 0)
            result = run_script(NEXT_ACTION, "--folder", folder, "--participant", "server")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("wait for the listed reviewer", result.stdout)
            self.assertIn("do not edit proposal.md or deliverables", result.stdout)

    def test_wait_for_turn_returns_on_completed_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "collab"
            self.assertEqual(self.init_folder(folder).returncode, 0)
            self.complete_happy_path(folder)
            result = run_script(WAIT, "--folder", folder, "--participant", "reader", "--timeout", "1", "--interval", "0.1")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ready: phase is completed", result.stdout)
            self.assertIn("next action: stop; collaboration is complete", result.stdout)

    def test_external_mode_uses_repo_relative_dir_and_external_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            folder = repo / ".acp" / "run"
            repo.mkdir()
            result = run_script(
                INIT,
                "--folder",
                folder,
                "--participant",
                "server",
                "--participant",
                "reader",
                "--objective",
                "External deliverable",
                "--primary-deliverable-type",
                "decision-memo",
                "--deliverables-mode",
                "external",
                "--repo-root",
                "../..",
                "--deliverables-dir",
                "docs/acp-output",
                "--completion",
                "External deliverable is ready",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((repo / "docs" / "acp-output" / "decision-memo.md").exists())
            protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
            self.assertEqual(protocol["repoRoot"], "../..")
            self.assertEqual(protocol["deliverables"]["mode"], "external")
            self.assertIn("external:decision-memo.md", (folder / "readiness.md").read_text(encoding="utf-8"))
            validate = run_script(VALIDATE, "--folder", folder)
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)


if __name__ == "__main__":
    unittest.main()
