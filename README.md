# 🚢 data-lifeboat

> *Because important scientific datasets shouldn't go down with the ship.*

**data-lifeboat** is a community resource for strategies, tools, and recipes to ensure critical geoscientific datasets remain accessible — even when funding dries up, servers go dark, or institutions restructure.

---

## The Problem

Scientific datasets are disappearing. Agencies lose funding. Cloud bills go unpaid. Hard drives fail. DOIs resolve to 404s. Years of irreplaceable environmental observations — sea surface temperatures, ice extent, atmospheric records — vanish without warning.

We can do better.

---

## The Approach

This repo documents practical approaches to data resilience using:

| Technology | Role |
|---|---|
| **[Zarr](https://zarr.dev)** | Cloud-native array storage — chunked, compressed, parallelizable |
| **[Icechunk](https://icechunk.io)** | Transactional Zarr store with version history |
| **[IPFS](https://ipfs.tech)** | Content-addressed, decentralized distribution |
| **[Filecoin / Storacha](https://storacha.network)** | Long-term decentralized storage with cryptographic receipts |
| **[xarray](https://xarray.dev)** | Analysis-ready access to N-D geoscientific data |
| **[DataCite DOIs](https://datacite.org)** | Persistent identifiers — optionally paired with CIDs |

---

## Contents

```
data-lifeboat/
├── recipes/           # Step-by-step guides for specific datasets/workflows
├── benchmarks/        # Performance comparisons (S3 vs IPFS vs Storacha, etc.)
├── proposals/         # Formal proposals (e.g. CID-alongside-DOI for DataCite)
├── tools/             # Scripts and utilities
└── case-studies/      # Real datasets rescued, with lessons learned
```

---

## Quickstart: Pin a Zarr Dataset to Filecoin

```bash
# Install Storacha CLI
npm install -g @web3-storage/w3cli

# Add a Zarr store (recursive)
w3 up my-dataset.zarr --name "OISST v2.1 2024"

# Get the CID
w3 ls
```

Then embed the CID alongside your DOI metadata. See [`proposals/cid-alongside-doi.md`](proposals/cid-alongside-doi.md) for the formal DataCite proposal.

---

## Key Findings (from CODED research)

- **Geography dominates latency** — a well-placed S3 bucket beats remote IPFS by 6–14×
- **Storacha CDN** (via `w3s.link`) closes most of that gap with ~64ms spatial resolution
- **CIDv1 is reproducible** — `ipfs add --only-hash` on a Zarr store gives a stable, verifiable fingerprint
- **Filecoin-backed CIDs** provide cryptographic proof of storage, independent of any single institution

---

## Case Studies

### OISST v2.1 — 3GB Sea Surface Temperature Archive
- **CID:** `bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q`
- **Format:** Zarr v2, chunked 1×90×180
- **Backed by:** Storacha (Filecoin), w3s.link CDN
- **Access:** `https://bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q.ipfs.w3s.link/`

---

## Contributing

Open an issue or PR! Especially welcome:
- New dataset recipes
- Benchmark results from different regions/protocols
- Failure post-mortems ("we lost this dataset and here's what we learned")
- Integrations with other preservation ecosystems (LOCKSS, DuraCloud, etc.)

---

## Related Work

- [CODED Blog](https://github.com/ESIPFed/coded-blog) — research notes from this project
- [Storacha](https://storacha.network) — web3.storage successor with Filecoin backing
- [Pangeo](https://pangeo.io) — community platform for big geoscience data
- [ESIP Data Stewardship](https://wiki.esipfed.org/Data_Stewardship) — broader preservation context

---

## License

CC0 1.0 — Public Domain. Take it, use it, build on it.

*Built with 🌊 by the [ESIP Federation](https://esipfed.org) CODED working group.*
