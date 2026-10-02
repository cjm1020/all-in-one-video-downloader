"""Verify real Git history and emit an application-ready evidence manifest.

Usage: python scripts/audit_history.py --minimum 51 --base <start-commit>
The report measures committed changes, not years of experience or popularity.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, encoding="utf-8").strip()


def audit(minimum: int, base: str | None) -> dict:
    revision = git("rev-parse", "HEAD")
    if base:
        base = git("rev-parse", "--verify", f"{base}^{{commit}}")
        subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", base, revision], check=True)
    commits, kinds, empty = [], Counter(), []
    for line in git("log", "--reverse", "--format=%H%x09%s", revision).splitlines():
        commit, subject = line.split("\t", 1)
        files = git("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-m", commit).splitlines()
        if not files:
            empty.append(commit)
        for kind in {path.split("/")[0] if "/" in path else "root" for path in files}:
            kinds[kind] += 1
        commits.append({"commit": commit, "subject": subject, "files": sorted(set(files))})
    new_count = int(git("rev-list", "--count", f"{base}..{revision}")) if base else None
    return {
        "head": revision, "branch": git("branch", "--show-current"),
        "total_commits": len(commits), "baseline": base, "commits_after_baseline": new_count,
        "minimum": minimum, "empty_commits": empty,
        "passes": len(commits) >= minimum and not empty,
        "areas": dict(sorted(kinds.items())), "commits": commits,
        "interpretation": "Actual file-changing history; does not establish experience, revenue, or GitHub stars.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimum", type=int, default=51)
    parser.add_argument("--base", help="Existing ancestor commit used to count changes in this delivery")
    parser.add_argument("--output", type=Path, help="Optional JSON report file")
    args = parser.parse_args()
    if args.minimum < 1:
        parser.error("--minimum must be positive")
    try:
        report = audit(args.minimum, args.base)
    except (subprocess.CalledProcessError, ValueError) as exc:
        parser.exit(2, f"Git audit failed: {exc}\n")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "commits"}, ensure_ascii=False, indent=2))
    sys.exit(0 if report["passes"] else 1)


if __name__ == "__main__":
    main()
