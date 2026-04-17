# coded-pin 🚢📦

Publish scientific datasets as **Icechunk stores on IPFS/Filecoin**.

Two modes, one CID, version history included.

---

## Install

```bash
pip install -e .
# Also requires the Storacha CLI for pinning:
npm install -g @web3-storage/w3cli
w3 login your@email.com
w3 space use my-space
```

---

## Usage

### `virtual` — data stays at its original URL

The Icechunk store holds only chunk manifests (tiny). The actual bytes stay at NOAA, NCAR, or wherever they live. Perfect for making existing archives content-addressed and versioned without moving any data.

```bash
# Single glob pattern
coded-pin virtual "oisst-avhrr-v02r01.2024*.nc" \
    --name oisst-virtual-2024 \
    --pin storacha \
    --ipns oisst-current

# Multiple URLs
coded-pin virtual \
    https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/202401/oisst-avhrr-v02r01.20240101.nc \
    https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/202401/oisst-avhrr-v02r01.20240102.nc \
    --name oisst-jan2024 \
    --pin storacha

# S3 source
coded-pin virtual "s3://noaa-cdr-sea-surface-temp-optimum-interpolation-pds/data/v2.1/avhrr/2024/*.nc" \
    --name oisst-2024-full \
    --pin storacha \
    --ipns oisst-2024
```

### `native` — data bytes go into the Icechunk store

Full self-contained snapshot. Entire dataset uploaded to Filecoin via Storacha.

```bash
# From a local Zarr store
coded-pin native oisst_rechunked.zarr \
    --name oisst-native-2024 \
    --pin storacha \
    --ipns oisst-native-current

# With rechunking
coded-pin native raw_data.zarr \
    --name my-dataset \
    --chunks '{"time": 1, "lat": 720, "lon": 1440}' \
    --pin storacha

# From a NetCDF file
coded-pin native data.nc \
    --name my-dataset-v1 \
    --chunks '{"time": 1, "lat": 90, "lon": 180}'

# Dry run (no upload)
coded-pin native my.zarr --pin none --output-dir ./icechunk-output
```

---

## Output

Both commands print a result table:

```
  Store      /tmp/coded-pin-virtual-abc123/oisst-virtual-2024
  Snapshot   c3a8f2d1...
  CID        bafybeig3x7...
  HTTP       https://bafybeig3x7....ipfs.w3s.link/
  IPNS       /ipns/k51qzi5uqu5...
  IPNS GW    https://k51qzi5uqu5....ipns.dweb.link
```

The **CID** uniquely identifies this exact version of your dataset. Anyone with the CID can verify and retrieve the data, independent of your institution.

The **IPNS** name is a mutable pointer — when you publish a new version, update the IPNS key and consumers following the IPNS name get the latest automatically.

---

## Reading Back

```python
import icechunk
import xarray as xr

# Open from local store
storage = icechunk.local_filesystem_storage("/path/to/store")
repo = icechunk.Repository.open(storage)
store = repo.readonly_session("main").store()
ds = xr.open_zarr(store)
print(ds)

# Or open from IPFS gateway (virtual collections only — data fetched from origin)
# Coming soon: icechunk IPFS storage backend
```

---

## How It Works

```
virtual mode:
  NetCDF files (NOAA/S3/HTTPS)
        │
        ▼ virtualizarr.open_virtual_dataset()
  VirtualiZarr Datasets (chunk references only)
        │
        ▼ xr.concat() + .vz.to_icechunk()
  Icechunk store (manifests only, ~MB)
        │
        ▼ w3 up → Storacha/Filecoin
  CID + IPNS

native mode:
  Zarr/NetCDF source (local or S3)
        │
        ▼ xr.open_zarr() / xr.open_dataset()
  xarray Dataset (actual data)
        │
        ▼ ds.to_zarr(icechunk_store)
  Icechunk store (full data, ~GB)
        │
        ▼ w3 up → Storacha/Filecoin
  CID + IPNS
```

---

## Why Icechunk?

- **Version history** — every commit is a snapshot, full audit trail
- **Transactional** — atomic writes, no partial corruption
- **Zarr-compatible** — any xarray/zarr reader works directly
- **Manifest separation** — virtual mode stores only references (not data)

---

## Why IPFS/Filecoin?

- **Content-addressed** — CID is a hash of the data, tamper-evident
- **Decentralized** — not tied to any institution's infrastructure
- **Persistent** — Filecoin deals survive funding gaps and server failures
- **Verifiable** — anyone can confirm they have the right bytes

---

## CI / Non-interactive Auth

Set environment variables to avoid interactive login:

```bash
export STORACHA_PRINCIPAL="did:key:..."
export STORACHA_PROOF="..."
coded-pin virtual ...
```

See [w3cli CI docs](https://github.com/web3-storage/w3cli#ci) for generating these.

---

## License

CC0 1.0 — Public Domain. Part of the [CODED Working Group](https://github.com/ESIPFed/data-lifeboat), ESIP Federation.
