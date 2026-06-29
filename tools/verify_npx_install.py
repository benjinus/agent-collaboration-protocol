#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_FILES = [
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
    "tests/test_collaboration_scripts.py",
]


def run(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def find_installed_skill(env: dict[str, str]) -> Path | None:
    result = run(["npx", "skills", "list", "-g", "--json"], env=env)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return None
    try:
        skills = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Unable to parse skills list JSON: {exc}\n")
        sys.stderr.write(result.stdout)
        return None

    for skill in skills:
        if skill.get("name") == "agent-collaboration-protocol":
            return Path(skill["path"])
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify npx skills add installs the full ACP package.")
    parser.add_argument("--source", default="agi-connect/agent-collaboration-protocol")
    parser.add_argument("--agent", default="codex")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    temp_root = Path(tempfile.mkdtemp(prefix="acp-npx-install-"))
    home = temp_root / "home"
    skills_home = temp_root / "skills-home"
    codex_home = temp_root / "codex-home"
    home.mkdir()
    skills_home.mkdir()
    codex_home.mkdir()

    env = dict(os.environ)
    env["HOME"] = str(home)
    env["SKILLS_HOME"] = str(skills_home)
    env["CODEX_HOME"] = str(codex_home)

    try:
        result = run(
            [
                "npx",
                "skills",
                "add",
                str(Path(args.source).resolve()) if args.source.startswith((".", "/")) else args.source,
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

        installed = find_installed_skill(env)
        if installed is None:
            sys.stderr.write("agent-collaboration-protocol was not listed after installation\n")
            return 2

        missing = [name for name in REQUIRED_FILES if not (installed / name).is_file()]
        if missing:
            sys.stderr.write("Missing installed files:\n")
            for name in missing:
                sys.stderr.write(f"- {name}\n")
            sys.stderr.write(f"\nInstall directory: {installed}\n")
            return 3

        stale_owner = "ben" + "jinus"
        stale_hits = run(["rg", "-n", stale_owner, str(installed)], env=env)
        if stale_hits.returncode == 0:
            sys.stderr.write(stale_hits.stdout)
            return 4

        print(f"npx skills add installed full package at {installed}")
        return 0
    finally:
        if args.keep:
            print(f"Kept temporary directory: {temp_root}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
