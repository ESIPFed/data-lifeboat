"""
coded_pin/native.py — Publish a Zarr/NetCDF dataset as a native Icechunk store.

Data bytes are written INTO the Icechunk store (no remote references).
Ideal for rechunked or pre-processed datasets you want to fully own on IPFS.

Workflow
--------
1. Open the source (Zarr store or NetCDF file) with xarray.
2. Create a local Icechunk store.
3. Write the dataset to the Icechunk store (actual bytes).
4. Commit with a descriptive message.
5. Upload the Icechunk store directory to Storacha → CID.
6. Optionally publish CID under an IPNS key.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import xarray as xr
import zarr
import icechunk

from rich.console import Console

from .pin import upload_to_storacha, gateway_url
from .ipns import ensure_key, publish, ipns_gateway_url

console = Console()


def publish_native(
    source: str,
    output_dir: Path,
    collection_name: str,
    pin: bool = True,
    ipns_key: str | None = None,
    chunks: dict | None = None,
    encoding: dict | None = None,
) -> dict:
    """
    Publish a Zarr store or NetCDF file as a native Icechunk store.

    Parameters
    ----------
    source : str
        Path to a local Zarr store or NetCDF file.
        Remote S3 Zarr stores (s3://...) are also supported.
    output_dir : Path
        Directory where the Icechunk store will be written.
    collection_name : str
        Human-readable name for the collection.
    pin : bool
        If True, upload the store to Storacha after building.
    ipns_key : str | None
        If provided, publish the CID under this IPNS key name.
    chunks : dict | None
        Optional rechunking spec, e.g. {"time": 1, "lat": 90, "lon": 180}.
        If None, the source chunking is preserved.
    encoding : dict | None
        Optional zarr encoding overrides per variable, e.g.
        {"sst": {"compressor": zarr.codecs.BloscCodec()}}.

    Returns
    -------
    dict with keys: store_path, snapshot_id, cid, ipns, gateway_url
    """
    console.rule(f"[bold]Native Collection: {collection_name}[/bold]")
    console.print(f"  Source : {source}")
    console.print(f"  Output : {output_dir}")
    if chunks:
        console.print(f"  Chunks : {chunks}")
    console.print()

    # --- Step 1: Open source dataset ---
    console.print("[cyan]Opening[/cyan] source dataset…")
    src = Path(source)

    if source.startswith("s3://") or (src.exists() and src.suffix in (".zarr", "") and (src / ".zmetadata").exists()):
        # Zarr store
        ds = xr.open_zarr(source, chunks="auto" if chunks else {})
    elif src.suffix in (".nc", ".nc4", ".h5", ".he5", ".hdf5"):
        ds = xr.open_dataset(source, chunks="auto" if chunks else {})
    else:
        # Try zarr first, then netcdf
        try:
            ds = xr.open_zarr(source, chunks="auto" if chunks else {})
        except Exception:
            ds = xr.open_dataset(source, chunks="auto" if chunks else {})

    console.print(f"  Dimensions : {dict(ds.sizes)}")
    console.print(f"  Variables  : {list(ds.data_vars)}")

    # --- Step 2: Optional rechunking ---
    if chunks:
        console.print(f"[cyan]Rechunking[/cyan] → {chunks}…")
        ds = ds.chunk(chunks)

    # --- Step 3: Create Icechunk store ---
    store_path = output_dir / collection_name
    store_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Creating[/cyan] Icechunk store at {store_path}…")
    storage = icechunk.local_filesystem_storage(str(store_path))
    repo = icechunk.Repository.create(storage)
    session = repo.writable_session("main")
    store = session.store

    # --- Step 4: Write data ---
    console.print("[cyan]Writing[/cyan] data to Icechunk store…")

    write_kwargs: dict = {}
    if encoding:
        write_kwargs["encoding"] = encoding

    # Use zarr-backed to_zarr with the icechunk store
    ds.to_zarr(store, mode="w", safe_chunks=False, **write_kwargs)

    # --- Step 5: Commit ---
    commit_msg = f"coded-pin native: {collection_name}"
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
