"""
coded_pin/virtual.py — Build an Icechunk virtual collection from NetCDF/HDF5 files.

Data bytes stay at their original location (NOAA, NCAR, etc.).
The Icechunk store holds only chunk references (manifests).

Workflow
--------
1. For each input file, open as a VirtualiZarr dataset (chunk refs, no data read).
2. Combine all datasets along the concat_dim (default: "time").
3. Write the combined virtual dataset to a local Icechunk store.
4. Commit with a descriptive message.
5. Upload the Icechunk store directory to Storacha → CID.
6. Optionally publish CID under an IPNS key.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable

import xarray as xr
import virtualizarr  # noqa: F401 — registers .vz accessor
from obspec_utils.registry import ObjectStoreRegistry
from obstore.store import LocalStore, HTTPStore
from virtualizarr.parsers import HDFParser, NetCDF3Parser
import icechunk

from rich.console import Console
from rich.progress import track

from .pin import upload_to_storacha, gateway_url
from .ipns import ensure_key, publish, ipns_gateway_url

console = Console()


def _make_registry(urls: list[str]) -> ObjectStoreRegistry:
    """
    Build an ObjectStoreRegistry covering all the URL schemes in *urls*.
    Supports: file://, http://, https://, s3://.
    """
    stores: dict[str, object] = {}

    for url in urls:
        if url.startswith("file://") or url.startswith("/"):
            # Local filesystem — register root
            if "file://" not in stores:
                stores["file://"] = LocalStore("/")
        elif url.startswith("https://") or url.startswith("http://"):
            # HTTP — register by origin
            from urllib.parse import urlparse
            parsed = urlparse(url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin not in stores:
                stores[origin] = HTTPStore(origin)
        elif url.startswith("s3://"):
            from urllib.parse import urlparse
            from obstore.store import S3Store
            parsed = urlparse(url)
            bucket = parsed.netloc
            key = f"s3://{bucket}"
            if key not in stores:
                stores[key] = S3Store(bucket=bucket, config={"aws_region": "us-east-1"})
        else:
            raise ValueError(f"Unsupported URL scheme: {url!r}")

    return ObjectStoreRegistry(stores)


def _resolve_url(path_or_url: str) -> str:
    """Normalise a local path or URL to a string URL."""
    if path_or_url.startswith(("file://", "http://", "https://", "s3://")):
        return path_or_url
    p = Path(path_or_url).resolve()
    return f"file://{p}"


def _pick_parser(url: str):
    """Choose a VirtualiZarr parser based on file extension."""
    lower = url.lower().split("?")[0]  # strip query params
    if lower.endswith((".nc4", ".h5", ".he5", ".hdf5")):
        return HDFParser()
    if lower.endswith(".nc") or lower.endswith(".nc3"):
        # Try HDF first (most modern NetCDF4 is HDF5 under the hood)
        return HDFParser()
    return HDFParser()  # safe default for most geoscience files


def build_virtual_collection(
    inputs: list[str],
    output_dir: Path,
    collection_name: str,
    concat_dim: str = "time",
    pin: bool = True,
    ipns_key: str | None = None,
) -> dict:
    """
    Build a virtual Icechunk collection from a list of NetCDF/HDF5 files.

    Parameters
    ----------
    inputs : list[str]
        Paths or URLs to input files. Globs should be expanded before calling.
    output_dir : Path
        Directory where the Icechunk store will be written.
    collection_name : str
        Human-readable name for the collection (used in commit message + Storacha label).
    concat_dim : str
        Dimension to concatenate files along (default: "time").
    pin : bool
        If True, upload the store to Storacha after building.
    ipns_key : str | None
        If provided, publish the CID under this IPNS key name.

    Returns
    -------
    dict with keys: store_path, cid, ipns, gateway_url
    """
    urls = [_resolve_url(i) for i in inputs]

    console.rule(f"[bold]Virtual Collection: {collection_name}[/bold]")
    console.print(f"  Files   : {len(urls)}")
    console.print(f"  Concat  : {concat_dim}")
    console.print(f"  Output  : {output_dir}")
    console.print()

    # --- Step 1: Open each file as a virtual dataset ---
    registry = _make_registry(urls)
    vdatasets = []

    for url in track(urls, description="Virtualising files…"):
        parser = _pick_parser(url)
        try:
            vds = xr.open_dataset(
                url,
                engine="virtualizarr",
                virtualizarr_registry=registry,
                virtualizarr_parser=parser,
            )
            vdatasets.append(vds)
        except Exception as exc:
            console.print(f"[yellow]⚠ Skipping {url}: {exc}[/yellow]")

    if not vdatasets:
        raise RuntimeError("No files could be virtualised — aborting.")

    # --- Step 2: Combine ---
    console.print(f"\n[cyan]Combining[/cyan] {len(vdatasets)} virtual datasets along '{concat_dim}'…")
    if len(vdatasets) == 1:
        combined = vdatasets[0]
    else:
        combined = xr.concat(vdatasets, dim=concat_dim)

    console.print(f"  Shape: {dict(combined.dims)}")

    # --- Step 3: Create Icechunk store ---
    store_path = output_dir / collection_name
    store_path.mkdir(parents=True, exist_ok=True)

    # Determine virtual chunk containers for authorization
    # (needed by Icechunk to allow reading from remote origins)
    origins = set()
    for url in urls:
        if url.startswith("file://"):
            origins.add("file://")
        elif url.startswith("https://") or url.startswith("http://"):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            origins.add(f"{parsed.scheme}://{parsed.netloc}")
        elif url.startswith("s3://"):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            origins.add(f"s3://{parsed.netloc}")

    authorize_virtual = {origin: None for origin in origins}

    console.print(f"\n[cyan]Creating[/cyan] Icechunk store at {store_path} …")
    storage = icechunk.local_filesystem_storage(str(store_path))
    repo = icechunk.Repository.create(
        storage,
        authorize_virtual_chunk_access=authorize_virtual,
    )
    session = repo.writable_session("main")
    store = session.store

    # --- Step 4: Write virtual references ---
    console.print("[cyan]Writing[/cyan] virtual chunk references…")
    combined.vz.to_icechunk(store, validate_containers=False)

    # --- Step 5: Commit ---
    commit_msg = f"coded-pin virtual: {collection_name} ({len(urls)} files)"
    snapshot_id = session.commit(commit_msg)
    console.print(f"[bold green]✓ Committed[/bold green] snapshot {snapshot_id}")

    result = {
        "store_path": str(store_path),
        "snapshot_id": str(snapshot_id),
        "cid": None,
        "ipns": None,
        "gateway_url": None,
    }

    # --- Step 6: Pin to Storacha ---
    if pin:
        cid = upload_to_storacha(store_path, name=collection_name)
        result["cid"] = cid
        result["gateway_url"] = gateway_url(cid)

        # --- Step 7: IPNS ---
        if ipns_key:
            peer_id = ensure_key(ipns_key)
            if peer_id:
                ipns_name = publish(cid, ipns_key)
                result["ipns"] = ipns_name or f"/ipns/{peer_id}"
                result["ipns_gateway_url"] = ipns_gateway_url(peer_id)

    return result
