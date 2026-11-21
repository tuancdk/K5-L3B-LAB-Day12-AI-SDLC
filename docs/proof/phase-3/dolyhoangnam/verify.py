"""Ghi log kiểm chứng thật cho Phase 3 (gather #19 + extension current #23), giữ exit code và UTF-8."""

import os
from pathlib import Path
import subprocess
import sys


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = os.pathsep.join((str(root / "tests"), str(root)))
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    result = subprocess.run(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = Path(__file__).with_name("unittest.log")
    log.write_bytes(result.stdout)
    sys.stdout.buffer.write(result.stdout)
    sys.exit(result.returncode)
