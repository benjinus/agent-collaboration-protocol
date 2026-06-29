# Npx Skills Full Package Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `agent-collaboration-protocol` so `npx skills add agi-connect/agent-collaboration-protocol` installs the complete skill package, including scripts and references, instead of only root `SKILL.md`.

**Architecture:** The installable skill package will live under `skills/agent-collaboration-protocol/`, which is the layout the `skills` CLI treats as a folder-backed skill package. The repository root remains the project documentation and test harness; root-level wrapper scripts and docs can remain as compatibility shims, but installation-critical files are validated from the nested package. Regression tests will assert the package layout and include an optional live `npx skills add` smoke test script for end-to-end verification.

**Tech Stack:** Python `unittest`, Python standard library scripts, Markdown documentation, GitHub-hosted `npx skills` CLI.

---

## File Structure

Create or modify these files:

- Create: `skills/agent-collaboration-protocol/SKILL.md`
  - The installable skill entrypoint copied from the current root `SKILL.md`.
- Create: `skills/agent-collaboration-protocol/scripts/_acp.py`
  - Package copy of the ACP protocol engine.
- Create: `skills/agent-collaboration-protocol/scripts/init_collaboration.py`
  - Package copy of the initializer.
- Create: `skills/agent-collaboration-protocol/scripts/append_event.py`
  - Package copy of the event appender.
- Create: `skills/agent-collaboration-protocol/scripts/next_action.py`
  - Package copy of the action helper.
- Create: `skills/agent-collaboration-protocol/scripts/wait_for_turn.py`
  - Package copy of the wait helper.
- Create: `skills/agent-collaboration-protocol/scripts/validate_collaboration.py`
  - Package copy of the validator.
- Create: `skills/agent-collaboration-protocol/references/open-agent-installation.md`
  - Package copy of the portable installation reference.
- Create: `skills/agent-collaboration-protocol/README.md`
  - Package-local English usage summary.
- Create: `skills/agent-collaboration-protocol/README.zh-CN.md`
  - Package-local Chinese usage summary.
- Create: `skills/agent-collaboration-protocol/LICENSE`
  - Package-local MIT license copy.
- Create: `scripts/verify_npx_install.py`
  - Live smoke test that installs from GitHub with `npx skills add`, then verifies files exist and stale owner strings are absent.
- Modify: `tests/test_collaboration_scripts.py`
  - Resolve script paths through `skills/agent-collaboration-protocol/`, assert the nested package contains required files, and keep stale owner checks scoped to docs.
- Modify: `README.md`
  - Explain the nested package layout and retain the current install command.
- Modify: `README.zh-CN.md`
  - Mirror the English README packaging guidance.
- Modify: `references/open-agent-installation.md`
  - Mention that the installable package lives at `skills/agent-collaboration-protocol/`.
- Modify: `.gitignore`
  - Ignore local smoke-test install directories produced by `scripts/verify_npx_install.py`.

Do not delete root scripts in this plan. Keeping them avoids breaking existing direct-repo workflows while the install package becomes authoritative for `npx skills add`.

---

### Task 1: Add Package Layout Regression Tests

**Files:**
- Modify: `tests/test_collaboration_scripts.py`
- Test: `tests/test_collaboration_scripts.py`

- [ ] **Step 1: Write the failing package layout test**

Insert these constants after `DOC_SUFFIXES = {".md", ".yaml", ".yml"}` in `tests/test_collaboration_scripts.py`:

```python
PACKAGE = ROOT / "skills" / "agent-collaboration-protocol"
PACKAGE_INIT = PACKAGE / "scripts" / "init_collaboration.py"
PACKAGE_APPEND = PACKAGE / "scripts" / "append_event.py"
PACKAGE_VALIDATE = PACKAGE / "scripts" / "validate_collaboration.py"
PACKAGE_WAIT = PACKAGE / "scripts" / "wait_for_turn.py"
PACKAGE_NEXT_ACTION = PACKAGE / "scripts" / "next_action.py"
REQUIRED_PACKAGE_FILES = [
    "SKILL.md",
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "references/open-agent-installation.md",
    "scripts/_acp.py",
    "scripts/init_collaboration.py",
    "scripts/append_event.py",
    "scripts/next_action.py",
    "scripts/wait_for_turn.py",
    "scripts/validate_collaboration.py",
]
```

Insert this test method immediately after `class CollaborationScriptsTest(unittest.TestCase):`:

```python
    def test_installable_package_contains_runtime_files(self) -> None:
        missing = [name for name in REQUIRED_PACKAGE_FILES if not (PACKAGE / name).is_file()]
        self.assertEqual(missing, [])

        skill_text = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: agent-collaboration-protocol", skill_text)
        self.assertIn("scripts/init_collaboration.py", skill_text)
        self.assertIn("references/open-agent-installation.md", "\n".join(REQUIRED_PACKAGE_FILES))
```

- [ ] **Step 2: Run the new test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts.CollaborationScriptsTest.test_installable_package_contains_runtime_files
```

Expected: `FAIL` with `AssertionError` listing missing files under `skills/agent-collaboration-protocol/`.

- [ ] **Step 3: Point script constants at the package paths**

Replace the existing path constants in `tests/test_collaboration_scripts.py`:

```python
INIT = ROOT / "scripts" / "init_collaboration.py"
APPEND = ROOT / "scripts" / "append_event.py"
VALIDATE = ROOT / "scripts" / "validate_collaboration.py"
WAIT = ROOT / "scripts" / "wait_for_turn.py"
NEXT_ACTION = ROOT / "scripts" / "next_action.py"
```

with:

```python
INIT = PACKAGE_INIT
APPEND = PACKAGE_APPEND
VALIDATE = PACKAGE_VALIDATE
WAIT = PACKAGE_WAIT
NEXT_ACTION = PACKAGE_NEXT_ACTION
```

Place this replacement after the `PACKAGE_*` constants so the names are defined before use.

- [ ] **Step 4: Run the full test suite to verify the package paths fail before files exist**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts
```

Expected: failures from missing package script files, confirming the test suite will exercise the installable package once files are added.

- [ ] **Step 5: Commit the failing tests**

```bash
git add tests/test_collaboration_scripts.py
git commit -m "test: require installable skill package layout"
```

---

### Task 2: Create The Installable Skill Package

**Files:**
- Create: `skills/agent-collaboration-protocol/SKILL.md`
- Create: `skills/agent-collaboration-protocol/scripts/_acp.py`
- Create: `skills/agent-collaboration-protocol/scripts/init_collaboration.py`
- Create: `skills/agent-collaboration-protocol/scripts/append_event.py`
- Create: `skills/agent-collaboration-protocol/scripts/next_action.py`
- Create: `skills/agent-collaboration-protocol/scripts/wait_for_turn.py`
- Create: `skills/agent-collaboration-protocol/scripts/validate_collaboration.py`
- Create: `skills/agent-collaboration-protocol/references/open-agent-installation.md`
- Create: `skills/agent-collaboration-protocol/README.md`
- Create: `skills/agent-collaboration-protocol/README.zh-CN.md`
- Create: `skills/agent-collaboration-protocol/LICENSE`
- Test: `tests/test_collaboration_scripts.py`

- [ ] **Step 1: Copy the package files into the nested skill directory**

Run:

```bash
mkdir -p skills/agent-collaboration-protocol/scripts skills/agent-collaboration-protocol/references
cp SKILL.md skills/agent-collaboration-protocol/SKILL.md
cp README.md skills/agent-collaboration-protocol/README.md
cp README.zh-CN.md skills/agent-collaboration-protocol/README.zh-CN.md
cp LICENSE skills/agent-collaboration-protocol/LICENSE
cp references/open-agent-installation.md skills/agent-collaboration-protocol/references/open-agent-installation.md
cp scripts/_acp.py skills/agent-collaboration-protocol/scripts/_acp.py
cp scripts/init_collaboration.py skills/agent-collaboration-protocol/scripts/init_collaboration.py
cp scripts/append_event.py skills/agent-collaboration-protocol/scripts/append_event.py
cp scripts/next_action.py skills/agent-collaboration-protocol/scripts/next_action.py
cp scripts/wait_for_turn.py skills/agent-collaboration-protocol/scripts/wait_for_turn.py
cp scripts/validate_collaboration.py skills/agent-collaboration-protocol/scripts/validate_collaboration.py
```

- [ ] **Step 2: Run the package layout test**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts.CollaborationScriptsTest.test_installable_package_contains_runtime_files
```

Expected: `OK`.

- [ ] **Step 3: Run the full Python test suite against package scripts**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts
```

Expected: `OK`, with the same number of tests as before plus the new package layout test.

- [ ] **Step 4: Verify package and root script copies match**

Run:

```bash
diff -qr --exclude='__pycache__' scripts skills/agent-collaboration-protocol/scripts
diff -q SKILL.md skills/agent-collaboration-protocol/SKILL.md
diff -q references/open-agent-installation.md skills/agent-collaboration-protocol/references/open-agent-installation.md
```

Expected: no output from all three commands.

- [ ] **Step 5: Commit the package files**

```bash
git add skills/agent-collaboration-protocol tests/test_collaboration_scripts.py
git commit -m "feat: add nested installable skill package"
```

---

### Task 3: Keep Package And Root Copies In Sync

**Files:**
- Modify: `tests/test_collaboration_scripts.py`
- Test: `tests/test_collaboration_scripts.py`

- [ ] **Step 1: Write a failing sync regression test**

Insert this helper method inside `CollaborationScriptsTest` after `test_installable_package_contains_runtime_files`:

```python
    def assert_same_text_file(self, root_relative: str) -> None:
        root_file = ROOT / root_relative
        package_file = PACKAGE / root_relative
        self.assertEqual(
            package_file.read_text(encoding="utf-8"),
            root_file.read_text(encoding="utf-8"),
            root_relative,
        )
```

Insert this test immediately after the helper:

```python
    def test_installable_package_stays_in_sync_with_root_runtime_files(self) -> None:
        for path in [
            "SKILL.md",
            "LICENSE",
            "references/open-agent-installation.md",
            "scripts/_acp.py",
            "scripts/init_collaboration.py",
            "scripts/append_event.py",
            "scripts/next_action.py",
            "scripts/wait_for_turn.py",
            "scripts/validate_collaboration.py",
        ]:
            self.assert_same_text_file(path)
```

- [ ] **Step 2: Run the sync test**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts.CollaborationScriptsTest.test_installable_package_stays_in_sync_with_root_runtime_files
```

Expected: `OK` if Task 2 copied files exactly. If it fails, use the failure path to copy the root file to the package path, then rerun this exact command.

- [ ] **Step 3: Update stale owner regression to scan package docs too**

Replace the body of `test_packaged_docs_use_current_repo_owner` with:

```python
    def test_packaged_docs_use_current_repo_owner(self) -> None:
        docs = {
            path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
            for base in [ROOT, PACKAGE]
            for path in base.rglob("*")
            if path.is_file() and path.suffix in DOC_SUFFIXES and ".git" not in path.parts
        }
        stale_owner = "ben" + "jinus"
        stale_paths = [name for name, text in docs.items() if stale_owner in text]
        self.assertEqual(stale_paths, [])

        for install_reference in [
            docs["references/open-agent-installation.md"],
            docs["skills/agent-collaboration-protocol/references/open-agent-installation.md"],
        ]:
            self.assertIn("npx skills add agi-connect/agent-collaboration-protocol", install_reference)
            self.assertIn("https://github.com/agi-connect/agent-collaboration-protocol.git", install_reference)
```

- [ ] **Step 4: Run the full Python test suite**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts
```

Expected: `OK`.

- [ ] **Step 5: Commit the sync tests**

```bash
git add tests/test_collaboration_scripts.py
git commit -m "test: keep installable package in sync"
```

---

### Task 4: Update Install Documentation For The Nested Package

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `references/open-agent-installation.md`
- Modify: `skills/agent-collaboration-protocol/README.md`
- Modify: `skills/agent-collaboration-protocol/README.zh-CN.md`
- Modify: `skills/agent-collaboration-protocol/references/open-agent-installation.md`
- Test: `tests/test_collaboration_scripts.py`

- [ ] **Step 1: Update English README packaging text**

In `README.md`, replace the paragraph after the install command:

```markdown
This installs the skill into the local skills directory used by compatible
agents.
```

with:

```markdown
This installs the complete skill package from
`skills/agent-collaboration-protocol/`, including `SKILL.md`, the Python helper
scripts, and the portable installation reference.
```

- [ ] **Step 2: Update Chinese README packaging text**

In `README.zh-CN.md`, find the paragraph immediately after:

```markdown
npx skills add agi-connect/agent-collaboration-protocol
```

Replace that paragraph with:

```markdown
这会从 `skills/agent-collaboration-protocol/` 安装完整技能包，包括
`SKILL.md`、Python 辅助脚本和可移植安装参考。
```

- [ ] **Step 3: Update the English installation reference**

In `references/open-agent-installation.md`, replace:

```markdown
The `skills` CLI detects supported agents and installs the skill into the
selected agent locations.
```

with:

```markdown
The `skills` CLI detects supported agents and installs the package from
`skills/agent-collaboration-protocol/` into the selected agent locations. A
valid install must include `SKILL.md`, `scripts/`, and `references/`.
```

- [ ] **Step 4: Copy updated docs into the package**

Run:

```bash
cp README.md skills/agent-collaboration-protocol/README.md
cp README.zh-CN.md skills/agent-collaboration-protocol/README.zh-CN.md
cp references/open-agent-installation.md skills/agent-collaboration-protocol/references/open-agent-installation.md
```

- [ ] **Step 5: Run documentation and sync tests**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts.CollaborationScriptsTest.test_packaged_docs_use_current_repo_owner
python3 -m unittest tests.test_collaboration_scripts.CollaborationScriptsTest.test_installable_package_stays_in_sync_with_root_runtime_files
```

Expected: both commands return `OK`.

- [ ] **Step 6: Run the full Python test suite**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts
```

Expected: `OK`.

- [ ] **Step 7: Commit documentation updates**

```bash
git add README.md README.zh-CN.md references/open-agent-installation.md skills/agent-collaboration-protocol/README.md skills/agent-collaboration-protocol/README.zh-CN.md skills/agent-collaboration-protocol/references/open-agent-installation.md
git commit -m "docs: document nested skill package install"
```

---

### Task 5: Add Live Npx Install Smoke Verification

**Files:**
- Create: `scripts/verify_npx_install.py`
- Modify: `.gitignore`
- Test: `scripts/verify_npx_install.py`

- [ ] **Step 1: Add the smoke verification script**

Create `scripts/verify_npx_install.py` with this content:

```python
#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_FILES = [
    "SKILL.md",
    "references/open-agent-installation.md",
    "scripts/_acp.py",
    "scripts/init_collaboration.py",
    "scripts/append_event.py",
    "scripts/next_action.py",
    "scripts/wait_for_turn.py",
    "scripts/validate_collaboration.py",
]


def run(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify npx skills add installs the full ACP package.")
    parser.add_argument("--source", default="agi-connect/agent-collaboration-protocol")
    parser.add_argument("--agent", default="codex")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    temp_root = Path(tempfile.mkdtemp(prefix="acp-npx-install-"))
    codex_home = temp_root / "codex-home"
    agents_home = temp_root / "agents-home"
    codex_home.mkdir()
    agents_home.mkdir()

    env = dict(**__import__("os").environ)
    env["CODEX_HOME"] = str(codex_home)
    env["AGENTS_HOME"] = str(agents_home)
    env["HOME"] = str(temp_root)

    try:
        result = run(
            [
                "npx",
                "skills",
                "add",
                args.source,
                "-g",
                "-a",
                args.agent,
                "-y",
                "--copy",
            ],
            env=env,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode

        installed = agents_home / "skills" / "agent-collaboration-protocol"
        missing = [name for name in REQUIRED_FILES if not (installed / name).is_file()]
        if missing:
            sys.stderr.write("Missing installed files:\n")
            for name in missing:
                sys.stderr.write(f"- {name}\n")
            sys.stderr.write(f"\nInstall directory: {installed}\n")
            return 2

        stale_owner = "ben" + "jinus"
        stale_hits = run(["rg", "-n", stale_owner, str(installed)], env=env)
        if stale_hits.returncode == 0:
            sys.stderr.write(stale_hits.stdout)
            return 3

        print(f"npx skills add installed full package at {installed}")
        return 0
    finally:
        if args.keep:
            print(f"Kept temporary directory: {temp_root}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Make the script executable**

Run:

```bash
chmod +x scripts/verify_npx_install.py
```

- [ ] **Step 3: Ignore local smoke-test directories if a run is kept**

Append this block to `.gitignore`:

```gitignore

# Local npx skills install smoke-test output
acp-npx-install-*/
```

- [ ] **Step 4: Run the smoke script against the current remote**

Run:

```bash
python3 scripts/verify_npx_install.py
```

Expected before pushing the nested package to GitHub: fail with `Missing installed files` because `origin/main` still exposes the old root-only package. This proves the smoke test catches the current broken install behavior.

- [ ] **Step 5: Run the full Python test suite**

Run:

```bash
python3 -m unittest tests.test_collaboration_scripts
```

Expected: `OK`.

- [ ] **Step 6: Commit smoke verification**

```bash
git add .gitignore scripts/verify_npx_install.py
git commit -m "test: add npx skills install smoke check"
```

---

### Task 6: Validate The Published Install Path

**Files:**
- No code changes expected after the remote branch contains Tasks 1-5.
- Test: `scripts/verify_npx_install.py`

- [ ] **Step 1: Push the branch after local tests pass**

Run:

```bash
git status --short
git push origin main
```

Expected: push succeeds, and GitHub `main` contains `skills/agent-collaboration-protocol/SKILL.md`.

- [ ] **Step 2: Run the live install smoke test**

Run:

```bash
python3 scripts/verify_npx_install.py
```

Expected:

```text
npx skills add installed full package at <temporary-path>/agents-home/skills/agent-collaboration-protocol
```

- [ ] **Step 3: Install the fixed package into the real global Codex target**

Run:

```bash
npx skills add agi-connect/agent-collaboration-protocol -g -a codex -y --copy
```

Expected: installation completes and reports `agent-collaboration-protocol`.

- [ ] **Step 4: Verify the real global install contains runtime files**

Run:

```bash
test -f /Users/xiasenhai/.agents/skills/agent-collaboration-protocol/scripts/init_collaboration.py
test -f /Users/xiasenhai/.agents/skills/agent-collaboration-protocol/references/open-agent-installation.md
stale_owner='ben''jinus'
rg -n "$stale_owner" /Users/xiasenhai/.agents/skills/agent-collaboration-protocol && exit 1 || true
```

Expected: both `test -f` commands exit 0; `rg` prints no stale owner hits.

- [ ] **Step 5: Verify installed package matches repository package**

Run:

```bash
diff -qr --exclude='__pycache__' --exclude='.DS_Store' \
  skills/agent-collaboration-protocol \
  /Users/xiasenhai/.agents/skills/agent-collaboration-protocol
```

Expected: no output.

- [ ] **Step 6: Record final validation status**

Run:

```bash
git log -1 --oneline
npx skills list -g --json | python3 -c 'import json,sys; data=json.load(sys.stdin); print(json.dumps([x for x in data if x.get("name")=="agent-collaboration-protocol"], ensure_ascii=False, indent=2))'
```

Expected: latest commit is the published fix, and the JSON entry path is `/Users/xiasenhai/.agents/skills/agent-collaboration-protocol` with `Codex` in `agents`.

---

## Self-Review

Spec coverage:
- The plan changes the repository layout so `npx skills add` can install a folder-backed package instead of a root single-file skill.
- The plan preserves current install command text: `npx skills add agi-connect/agent-collaboration-protocol`.
- The plan adds regression tests for package layout, stale owner strings, root/package sync, and a live `npx skills add` smoke check.
- The plan includes real global Codex installation validation after publishing.

Placeholder scan:
- No placeholder markers or unspecified implementation steps remain.
- Every code-changing step includes exact code or exact commands.
- Every test step includes expected output.

Type consistency:
- Path constants consistently use `PACKAGE`, `PACKAGE_INIT`, `PACKAGE_APPEND`, `PACKAGE_VALIDATE`, `PACKAGE_WAIT`, and `PACKAGE_NEXT_ACTION`.
- The smoke script and tests use the same required runtime file names.
