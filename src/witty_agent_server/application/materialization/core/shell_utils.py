from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass
class CmdResult:
    code: int
    stdout: str
    stderr: str


def run_cmd(
    args: Sequence[str], check: bool = True, env: Mapping[str, str] | None = None
) -> CmdResult:
    merged_env = None
    if env:
        merged_env = os.environ.copy()
        merged_env.update(dict(env))
    cp = subprocess.run(args, capture_output=True, text=True, env=merged_env)
    result = CmdResult(cp.returncode, cp.stdout, cp.stderr)
    if check and cp.returncode != 0:
        cmd = " ".join(args)
        raise RuntimeError(
            f"command failed({cp.returncode}): {cmd}\n{cp.stderr.strip()}"
        )
    return result
