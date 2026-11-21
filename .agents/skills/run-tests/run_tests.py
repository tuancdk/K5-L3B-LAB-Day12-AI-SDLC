"""Chạy toàn bộ test và lưu log làm bằng chứng. Chỉ dùng thư viện chuẩn.

    python3 .agents/skills/run-tests/run_tests.py [--phase phase-1] [--who handle]
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def git_head():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        return out.stdout.strip() or "?"
    except OSError:
        return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="phase-1")
    ap.add_argument("--who", default="team")
    a = ap.parse_args()

    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "tests"), str(ROOT)))
    cmd = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    res = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    out_dir = ROOT / "docs" / "proof" / a.phase / a.who
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / "unittest.log"
    header = (f"# commit {git_head()} · Python {platform.python_version()} · {platform.system()}\n"
              f"# PYTHONPATH=tests:. python3 -m unittest discover -s tests -v\n").encode("utf-8")
    log.write_bytes(header + res.stdout)

    text = res.stdout.decode("utf-8", "replace").splitlines()
    summary = [ln for ln in text if ln.startswith("Ran ") or ln.startswith("OK") or ln.startswith("FAILED")]
    print("\n".join(summary))
    print(f"log: {log.relative_to(ROOT).as_posix()} - exit {res.returncode}")
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
