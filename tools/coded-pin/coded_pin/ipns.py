"""
coded_pin/ipns.py — IPNS key management for mutable "current branch" pointers.

Wraps the IPFS CLI (kubo). Requires a running IPFS daemon.
Falls back gracefully if IPFS is not available.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from rich.console import Console

console = Console()

_IPFS_UNAVAILABLE_MSG = (
    "IPFS daemon not available — skipping IPNS publish.\n"
    "To enable mutable pointers, install Kubo and run `ipfs daemon`.\n"
    "See: https://docs.ipfs.tech/install/command-line/"
)


def _ipfs_available() -> bool:
    return shutil.which("ipfs") is not None


def _ipfs(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ipfs", *args],
        capture_output=True,
        text=True,
        check=check,
    )


def ensure_key(name: str) -> str:
    """
    Return the peer ID for an IPNS key, creating it if it doesn't exist.

    Parameters
    ----------
    name : str
        Key name (e.g. "oisst-virtual-collection").

    Returns
    -------
    str
        The peer ID (IPNS address) for this key.
    """
    if not _ipfs_available():
        console.print(f"[yellow]⚠[/yellow] {_IPFS_UNAVAILABLE_MSG}")
        return ""

    # List existing keys
    result = _ipfs("key", "list", "--enc=json", check=False)
    if result.returncode == 0:
        try:
            keys = json.loads(result.stdout)
            # Format: {"Keys": [{"Name": "...", "Id": "..."}, ...]}
            for k in keys.get("Keys", []):
                if k.get("Name") == name:
                    peer_id = k["Id"]
                    console.print(f"[dim]IPNS key '{name}' exists → {peer_id}[/dim]")
                    return peer_id
        except (json.JSONDecodeError, KeyError):
            pass

    # Generate new key
    result = _ipfs("key", "gen", "--type=ed25519", name, check=False)
    if result.returncode != 0:
        console.print(f"[yellow]⚠ Could not create IPNS key '{name}': {result.stderr.strip()}[/yellow]")
        return ""

    peer_id = result.stdout.strip()
    console.print(f"[bold green]✓ Created IPNS key[/bold green] '{name}' → {peer_id}")
    return peer_id


def publish(cid: str, key_name: str) -> str:
    """
    Publish a CID under an IPNS key.

    Parameters
    ----------
    cid : str
        The CIDv1 to publish.
    key_name : str
        IPNS key name to publish under.

    Returns
    -------
    str
        The IPNS name (e.g. /ipns/k51q...) or empty string if unavailable.
    """
    if not _ipfs_available():
        console.print(f"[yellow]⚠[/yellow] {_IPFS_UNAVAILABLE_MSG}")
        return ""

    console.print(f"[cyan]Publishing[/cyan] /ipfs/{cid} → IPNS key '{key_name}' …")
    result = _ipfs("name", "publish", f"--key={key_name}", f"/ipfs/{cid}", check=False)

    if result.returncode != 0:
        console.print(f"[yellow]⚠ IPNS publish failed: {result.stderr.strip()}[/yellow]")
        return ""

    # Output: Published to <name>: /ipfs/<cid>
    line = result.stdout.strip()
    console.print(f"[bold green]✓ IPNS[/bold green] {line}")

    # Extract the /ipns/... part
    if "Published to" in line:
        parts = line.split("Published to", 1)
        if len(parts) > 1:
            return "/ipns/" + parts[1].split(":")[0].strip()

    return line


def ipns_gateway_url(peer_id: str) -> str:
    """Return an HTTP gateway URL for an IPNS peer ID."""
    return f"https://{peer_id}.ipns.dweb.link"
