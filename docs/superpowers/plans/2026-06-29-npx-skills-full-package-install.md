# Npx Skills Full Package Install Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Keep the package layout below as the source of truth.

**Goal:** Make `npx skills add agi-connect/agent-collaboration-protocol` install the complete Agent Collaboration Protocol package, not a stale root entrypoint or partial file set.

**Final Architecture:** The installable skill package is self-contained under `skills/agent-collaboration-protocol/`. The repository root is only for repository-level documentation, agent metadata, implementation plans, and verification tooling. The root must not contain `SKILL.md`, `scripts/`, `references/`, or `tests/` runtime copies, because a root `SKILL.md` causes the `skills` CLI to install only that entrypoint.

**Required Package Layout:**

```text
skills/agent-collaboration-protocol/
  SKILL.md
  scripts/
  references/
  README.md
  README.zh-CN.md
  LICENSE
  tests/
```

**Tech Stack:** Python `unittest`, Python standard-library helper scripts, Markdown documentation, GitHub-hosted `npx skills` CLI.

---

## File Structure

Create or modify these files:

- Keep: `skills/agent-collaboration-protocol/SKILL.md`
  - The only skill entrypoint in the repository.
- Keep: `skills/agent-collaboration-protocol/scripts/`
  - Package-local ACP helper scripts.
- Keep: `skills/agent-collaboration-protocol/references/open-agent-installation.md`
  - Package-local portable installation reference.
- Keep: `skills/agent-collaboration-protocol/README.md`
  - Package-local English usage summary.
- Keep: `skills/agent-collaboration-protocol/README.zh-CN.md`
  - Package-local Chinese usage summary.
- Keep: `skills/agent-collaboration-protocol/LICENSE`
  - Package-local MIT license copy.
- Keep: `skills/agent-collaboration-protocol/tests/test_collaboration_scripts.py`
  - Package-local regression suite.
- Keep: `tools/verify_npx_install.py`
  - Live smoke test for `npx skills add`.
- Modify: `README.md`
  - Explain that the installable package lives only at `skills/agent-collaboration-protocol/`.
- Modify: `README.zh-CN.md`
  - Mirror the English packaging guidance.
- Modify: `.gitignore`
  - Ignore kept local smoke-test directories.
- Delete: root `SKILL.md`, root `scripts/`, root `references/`, root `tests/`
  - These are not compatibility shims; they are install-path hazards.

---

### Task 1: Make The Package Self-Contained

**Files:**
- Keep: `skills/agent-collaboration-protocol/SKILL.md`
- Keep: `skills/agent-collaboration-protocol/scripts/_acp.py`
- Keep: `skills/agent-collaboration-protocol/scripts/init_collaboration.py`
- Keep: `skills/agent-collaboration-protocol/scripts/append_event.py`
- Keep: `skills/agent-collaboration-protocol/scripts/next_action.py`
- Keep: `skills/agent-collaboration-protocol/scripts/wait_for_turn.py`
- Keep: `skills/agent-collaboration-protocol/scripts/validate_collaboration.py`
- Keep: `skills/agent-collaboration-protocol/references/open-agent-installation.md`
- Keep: `skills/agent-collaboration-protocol/README.md`
- Keep: `skills/agent-collaboration-protocol/README.zh-CN.md`
- Keep: `skills/agent-collaboration-protocol/LICENSE`
- Keep: `skills/agent-collaboration-protocol/tests/test_collaboration_scripts.py`

- [x] Ensure `skills/agent-collaboration-protocol/` contains the required package layout.
- [x] Ensure the package-local `SKILL.md` references helper scripts and installation references by package-relative paths.
- [x] Ensure package-local tests execute helper scripts from package-local paths.
- [x] Include `tests/test_collaboration_scripts.py` in the required package file list so the installed package carries its regression suite.

Validation:

```bash
cd skills/agent-collaboration-protocol && python3 -m unittest tests.test_collaboration_scripts
```

Expected: all tests pass.

---

### Task 2: Remove Root Runtime Copies

**Files:**
- Delete: root `SKILL.md`
- Delete: root `scripts/`
- Delete: root `references/`
- Delete: root `tests/`
- Keep: `tools/verify_npx_install.py`

- [x] Remove root runtime directories and files so the `skills` CLI cannot select a stale root skill.
- [x] Keep smoke-test tooling under `tools/`, because it is repository tooling, not part of the runtime protocol package.
- [x] Remove transient root reference files; renaming the root entrypoint is not the fix.

Validation:

```bash
find . -path './.git' -prune -o -iname '*skill.md' -print | sort
find . -path './.git' -prune -o -maxdepth 2 -type d -print | sort
```

Expected:

```text
./skills/agent-collaboration-protocol/SKILL.md
```

No root `scripts/`, `references/`, or `tests/` directory should be present.

---

### Task 3: Keep Documentation Aligned

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `skills/agent-collaboration-protocol/README.md`
- Modify: `skills/agent-collaboration-protocol/README.zh-CN.md`
- Modify: `skills/agent-collaboration-protocol/references/open-agent-installation.md`

- [x] Keep the install command as:

```bash
npx skills add agi-connect/agent-collaboration-protocol
```

- [x] State that the complete package is installed from `skills/agent-collaboration-protocol/`.
- [x] State that a valid install includes `SKILL.md`, `scripts/`, `references/`, and `tests/`.
- [x] State that the repository root intentionally does not contain runtime copies.
- [x] Keep English and Chinese README guidance in lockstep.

Validation:

```bash
stale_owner='ben''jinus'
rg -n "$stale_owner" . --glob '!/.git/**'
cd skills/agent-collaboration-protocol && python3 -m unittest tests.test_collaboration_scripts.CollaborationScriptsTest.test_packaged_docs_use_current_repo_owner
```

Expected: no stale owner hits and the documentation test passes.

---

### Task 4: Add Regression Checks

**Files:**
- Modify: `skills/agent-collaboration-protocol/tests/test_collaboration_scripts.py`
- Keep: `tools/verify_npx_install.py`

- [x] Add a package-layout regression test that fails if required package files are missing.
- [x] Add a stale-owner regression check that constructs the old owner string as `"ben" + "jinus"` so the test itself does not reintroduce the stale literal.
- [x] Add a live `npx skills add` smoke check that installs into isolated temporary homes and asserts the installed package contains:

```text
SKILL.md
README.md
README.zh-CN.md
LICENSE
references/open-agent-installation.md
scripts/_acp.py
scripts/init_collaboration.py
scripts/append_event.py
scripts/next_action.py
scripts/wait_for_turn.py
scripts/validate_collaboration.py
tests/test_collaboration_scripts.py
```

Validation:

```bash
cd skills/agent-collaboration-protocol && python3 -m unittest tests.test_collaboration_scripts
python3 tools/verify_npx_install.py --source .
```

Expected: both commands pass locally.

---

### Task 5: Publish And Verify The Real Install Path

**Files:**
- No further code changes expected after local validation.

- [ ] Commit the cleanup.
- [ ] Push `main`.
- [ ] Run the live smoke test against the published default source.
- [ ] Update the real Codex global install with `npx skills add`.
- [ ] Verify the installed package matches `skills/agent-collaboration-protocol/`.

Commands:

```bash
git status --short
git push origin main
python3 tools/verify_npx_install.py
npx skills add agi-connect/agent-collaboration-protocol -g -a codex -y --copy
test -f /Users/xiasenhai/.agents/skills/agent-collaboration-protocol/tests/test_collaboration_scripts.py
diff -qr --exclude='__pycache__' --exclude='.DS_Store' \
  skills/agent-collaboration-protocol \
  /Users/xiasenhai/.agents/skills/agent-collaboration-protocol
```

Expected: the published and real Codex installs contain the complete package and no stale owner string.

---

## Self-Review

- The repository root contains no runtime skill entrypoint or runtime directory that can shadow the nested package.
- The install command remains `npx skills add agi-connect/agent-collaboration-protocol`.
- The installed package includes `SKILL.md`, `scripts/`, `references/`, `README.md`, `README.zh-CN.md`, `LICENSE`, and `tests/`.
- Regression checks cover package completeness and the old owner string.
- The real global Codex install is refreshed through `npx skills add`, not by manual copying.
