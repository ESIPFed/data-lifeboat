"""
coded_pin/cli.py — Click CLI entry point for coded-pin.

Usage
-----
# Virtual collection (data stays at original URL, IPFS hosts manifests only)
coded-pin virtual "oisst-avhrr-v02r01.2024*.nc" \\
    --name oisst-virtual-2024 \\
    --concat-dim time \\
    --pin storacha \\
    --ipns oisst-current

# Native data (actual bytes written into Icechunk store, then uploaded)
coded-pin native oisst_rechunked.zarr \\
    --name oisst-native-2024 \\
    --chunks '{"time": 1, "lat": 720, "lon": 1440}' \\
    --pin storacha \\
    --ipns oisst-native-current
"""

from __future__ import annotations

import glob
import json
import sys
import tempfile
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_result(result: dict, mode: str) -> None:
    table = Table(title=f"coded-pin {mode} — result", show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="bold cyan", no_wrap=True)
    table.add_column("value", style="white")

    table.add_row("Store", result.get("store_path", "—"))
    table.add_row("Snapshot", result.get("snapshot_id", "—"))
    if result.get("cid"):
        table.add_row("CID", result["cid"])
    if result.get("gateway_url"):
        table.add_row("HTTP Gateway", result["gateway_url"])
    if result.get("ipns"):
        table.add_row("IPNS", result["ipns"])
    if result.get("ipns_gateway_url"):
        table.add_row("IPNS Gateway", result["ipns_gateway_url"])

    console.print()
    console.print(table)
    console.print()

    if result.get("cid"):
        console.print(
            Panel(
                f"[bold green]{result['cid']}[/bold green]",
                title="📦 CID",
                border_style="green",
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLI Group
# ─────────────────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(package_name="coded-pin")
def main():
    """
    coded-pin: Publish scientific datasets as Icechunk stores on IPFS/Filecoin.

    Two modes:

    \b
    virtual  Data stays at its original URL (NOAA, NCAR, S3…).
             Icechunk holds only chunk manifests (references).
             Tiny footprint, big datasets — perfect for archival pointers.

    \b
    native   Data bytes are written into the Icechunk store.
             Full self-contained snapshot, pinned to Filecoin via Storacha.
    """


# ─────────────────────────────────────────────────────────────────────────────
# virtual subcommand
# ─────────────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("inputs", nargs=-1, required=True)
@click.option(
    "--name", "-n",
    default=None,
    metavar="NAME",
    help="Collection name (used in commit message and Storacha label). "
         "Defaults to the first input file's stem.",
)
@click.option(
    "--concat-dim", "-d",
    default="time",
    show_default=True,
    metavar="DIM",
    help="Dimension to concatenate files along.",
)
@click.option(
    "--output-dir", "-o",
    default=None,
    type=click.Path(file_okay=False, writable=True),
    metavar="DIR",
    help="Directory to write the Icechunk store. Defaults to a temp directory.",
)
@click.option(
    "--pin",
    type=click.Choice(["storacha", "none"], case_sensitive=False),
    default="storacha",
    show_default=True,
    help="Where to pin the Icechunk store.",
)
@click.option(
    "--ipns",
    default=None,
    metavar="KEY_NAME",
    help="IPNS key name for a mutable pointer to the latest CID. "
         "Requires a running IPFS daemon.",
)
def virtual(inputs, name, concat_dim, output_dir, pin, ipns):
    """
    Build a VIRTUAL Icechunk collection from NetCDF/HDF5 files.

    INPUTS can be paths, URLs (https://, s3://, file://), or glob patterns.

    \b
    Examples:
      coded-pin virtual "oisst*.nc" --name oisst-virtual-2024
      coded-pin virtual https://thredds.ucar.edu/file1.nc https://.../file2.nc
      coded-pin virtual s3://noaa-oisst/*.nc --pin storacha --ipns oisst-current
    """
    from .virtual import build_virtual_collection

    # Expand globs
    resolved: list[str] = []
    for inp in inputs:
        # Check if it looks like a URL
        if inp.startswith(("http://", "https://", "s3://", "file://")):
            resolved.append(inp)
        else:
            expanded = glob.glob(inp, recursive=True)
            if expanded:
                resolved.extend(sorted(expanded))
            else:
                # Might be a literal path
                resolved.append(inp)

    if not resolved:
        console.print("[red]No input files found.[/red]")
        sys.exit(1)

    console.print(f"[dim]Resolved {len(resolved)} file(s)[/dim]")

    collection_name = name or Path(resolved[0]).stem

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        result = build_virtual_collection(
            resolved, out, collection_name,
            concat_dim=concat_dim,
            pin=(pin != "none"),
            ipns_key=ipns,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="coded-pin-virtual-") as tmpdir:
            result = build_virtual_collection(
                resolved, Path(tmpdir), collection_name,
                concat_dim=concat_dim,
                pin=(pin != "none"),
                ipns_key=ipns,
            )

    _print_result(result, "virtual")


# ─────────────────────────────────────────────────────────────────────────────
# native subcommand
# ─────────────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("source")
@click.option(
    "--name", "-n",
    default=None,
    metavar="NAME",
    help="Collection name. Defaults to the source directory/file name.",
)
@click.option(
    "--output-dir", "-o",
    default=None,
    type=click.Path(file_okay=False, writable=True),
    metavar="DIR",
    help="Directory to write the Icechunk store. Defaults to a temp directory.",
)
@click.option(
    "--pin",
    type=click.Choice(["storacha", "none"], case_sensitive=False),
    default="storacha",
    show_default=True,
    help="Where to pin the Icechunk store.",
)
@click.option(
    "--ipns",
    default=None,
    metavar="KEY_NAME",
    help="IPNS key name for a mutable pointer to the latest CID.",
)
@click.option(
    "--chunks",
    default=None,
    metavar="JSON",
    help='Rechunking spec as JSON, e.g. \'{"time": 1, "lat": 720, "lon": 1440}\'.',
)
@click.option(
    "--encoding",
    default=None,
    metavar="JSON",
    help='Zarr encoding overrides as JSON, e.g. \'{"sst": {"dtype": "float32"}}\'.',
)
def native(source, name, output_dir, pin, ipns, chunks, encoding):
    """
    Publish a NATIVE Icechunk store from a Zarr store or NetCDF file.

    SOURCE is a path to a local Zarr store directory, NetCDF file, or s3:// URL.

    \b
    Examples:
      coded-pin native oisst_rechunked.zarr --name oisst-native-2024
      coded-pin native s3://my-bucket/data.zarr --pin storacha --ipns my-dataset
      coded-pin native data.nc --chunks '{"time": 1, "lat": 90, "lon": 180}'
    """
    from .native import publish_native

    collection_name = name or Path(source).stem

    chunks_dict = json.loads(chunks) if chunks else None
    encoding_dict = json.loads(encoding) if encoding else None

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        result = publish_native(
            source, out, collection_name,
            pin=(pin != "none"),
            ipns_key=ipns,
            chunks=chunks_dict,
            encoding=encoding_dict,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="coded-pin-native-") as tmpdir:
            result = publish_native(
                source, Path(tmpdir), collection_name,
                pin=(pin != "none"),
                ipns_key=ipns,
                chunks=chunks_dict,
                encoding=encoding_dict,
            )

    _print_result(result, "native")
