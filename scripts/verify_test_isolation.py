"""Run pytest twice and verify it leaves checkout artifacts and status unchanged."""

import hashlib
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def snapshot():
    files = {}
    for folder in ("models", "reports", "data"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file():
                files[str(path.relative_to(ROOT))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT
    )
    return files, status


def main():
    before = snapshot()
    for run in (1, 2):
        print(f"Full test run {run}/2", flush=True)
        result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT)
        if result.returncode:
            return result.returncode
        if snapshot() != before:
            print("FAIL: tests changed checkout artifacts or Git status.")
            return 1
    print("PASS: both full runs passed; artifact hashes and Git status unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
