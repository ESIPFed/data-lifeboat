"""
coded_pin/pin.py — Upload a local directory to Storacha and return a CID.

Uses the w3cli (Node.js) under the hood. Requires:
  npm install -g @web3-storage/w3cli
  w3 login <email>
  w3 space use <space-name>

Alternatively, set STORACHA_PRINCIPAL and STORACHA_PROOF env vars for
non-interactive / CI use (see: https://github.com/web3-storage/w3cli#ci).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


def _require_w3cli() -> str:
    """Return path to w3 CLI binary, or raise if not found."""
    w3 = shutil.which("w3")
    if not w3:
        raise RuntimeError(
            "w3 CLI not found. Install with:\n"
            "  npm install -g @web3-storage/w3cli\n"
            "Then authenticate:\n"
            "  w3 login your@email.com\n"
            "  w3 space use <space-name>"
        )
    return w3


def upload_to_storacha(path: Path, name: str | None = None) -> str:
    """
    Upload *path* (file or directory) to Storacha and return the root CID.

    Parameters
    ----------
    path : Path
        Local path to upload.
    name : str, optional
        Human-readable label stored in Storacha (defaults to directory name).

    Returns
    -------
    str
        CIDv1 of the uploaded content.
    """
    w3 = _require_w3cli()
    label = name or path.name

    cmd = [w3, "up", str(path), "--name", label, "--json"]

    # Inject CI credentials if provided via env
    env = os.environ.copy()
    principal = env.get("STORACHA_PRINCIPAL")
    proof = env.get("STORACHA_PROOF")
    if principal and proof:
        cmd += ["--principal", principal, "--proof", proof]

    console.print(f"[bold cyan]↑ Uploading[/bold cyan] {path} → Storacha as [italic]{label}[/italic]")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(
            f"w3 up failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # Parse CID from JSON output: {"root": {"/":<cid>}, ...}
    # w3 up --json outputs a line like: {"root":{"/":"bafy..."},...}
    cid = _extract_cid(result.stdout.strip())
    console.print(f"[bold green]✓ Pinned[/bold green] CID: [bold]{cid}[/bold]")
    return cid


def _extract_cid(output: str) -> str:
    """Extract CID from w3 up --json output."""
    # Try JSON parse first
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            # w3 up --json: {"root": {"/": "bafy..."}, "shards": [...]}
            if "root" in data:
                root = data["root"]
                if isinstance(root, dict) and "/" in root:
                    return root["/"]
                if isinstance(root, str):
                    return root
            # Fallback: look for any bafy... string in the dict values
            for v in data.values():
                if isinstance(v, str) and v.startswith("bafy"):
                    return v
        except json.JSONDecodeError:
            pass

    # Last resort: regex for a CIDv1
    match = re.search(r"(baf[a-zA-Z2-7]{50,})", output)
    if match:
        return match.group(1)

    raise ValueError(f"Could not parse CID from w3 output:\n{output}")


def gateway_url(cid: str, path: str = "") -> str:
    """Return the w3s.link HTTP gateway URL for a CID."""
    base = f"https://{cid}.ipfs.w3s.link"
    return f"{base}/{path}" if path else base
