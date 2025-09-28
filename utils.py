# utils.py - small helper functions
import subprocess
from typing import Tuple, List

def run_cmd(cmd: list, cwd: str | None = None, check: bool = True) -> Tuple[str, str]:
    """Run subprocess command, return (stdout, stderr). Raise RuntimeError on non-zero if check True."""
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Cmd failed: {' '.join(cmd)}\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}")
    return proc.stdout, proc.stderr

def find_downloaded_file(out_dir: str, prefix: str = "input.") -> str | None:
    import os
    for f in sorted(os.listdir(out_dir)):
        if f.startswith(prefix) and any(f.endswith(ext) for ext in [".mp4", ".mkv", ".webm", ".mov"]):
            return os.path.join(out_dir, f)
    return None
