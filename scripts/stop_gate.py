"""Stop hook: keep a turn from ending on a red build.

Wired in `.claude/settings.json`. Reads the hook's JSON on stdin and exits:
- 0 when the hook already blocked once (`stop_hook_active`), when nothing differs
  from HEAD, or when the working tree is the one the last green run checked;
- 0 after pytest and pre-commit pass, saving the tree's fingerprint;
- 2 with the failing output's tail on stderr, which blocks the stop.

The fingerprint stamp (`.claude/stop-gate.stamp`, gitignored) lets a turn that
changed nothing end at once while a large uncommitted diff sits on the branch.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAMP = ROOT / ".claude" / "stop-gate.stamp"
CHECKS = [
    ["uv", "run", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
    ["uv", "run", "python", "-m", "pre_commit", "run", "--all-files"],
]
TAIL = 40


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=True
    ).stdout


def fingerprint() -> str | None:
    """Hash of HEAD, the diff against it and the untracked files; None when clean."""
    diff = git("diff", "HEAD", "--binary")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    untracked = [p for p in untracked if p]
    if not diff and not untracked:
        return None
    h = hashlib.sha256(git("rev-parse", "HEAD"))
    h.update(diff)
    for p in sorted(untracked):
        h.update(p)
        path = ROOT / p.decode()
        if path.is_file():
            h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        event = {}
    if event.get("stop_hook_active"):
        return 0
    before = fingerprint()
    if before is None:
        return 0
    if STAMP.is_file() and STAMP.read_text().strip() == before:
        return 0
    for cmd in CHECKS:
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True)
        if run.returncode != 0:
            out = (run.stdout + run.stderr).decode("utf-8", errors="replace")
            tail = "\n".join(out.splitlines()[-TAIL:])
            print(f"Stop gate: `{' '.join(cmd)}` failed.\n{tail}", file=sys.stderr)
            return 2
    STAMP.write_text(fingerprint() or "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
