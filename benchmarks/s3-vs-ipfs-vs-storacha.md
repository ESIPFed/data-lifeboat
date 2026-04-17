# Benchmark: S3 vs IPFS vs Storacha CDN — Access Latency

**Dataset:** OISST v2.1 SST (3GB Zarr, chunked 1×90×180)  
**Conducted:** 2026-03, CODED Working Group  

---

## Setup

- **S3:** `s3://oisst-zarr/` (us-east-1)
- **IPFS (remote node):** Public gateway, eu-west-1 pin
- **Storacha CDN:** `w3s.link`, Filecoin-backed

Tests run from EC2 instances in 3 regions: `us-east-1`, `eu-west-1`, `ap-southeast-1`

---

## Results: Time-to-First-Byte (ms)

| Client Region | S3 (same region) | S3 (cross-region) | Remote IPFS | Storacha CDN |
|---|---|---|---|---|
| us-east-1 | 42ms | 380ms | 520ms | 67ms |
| eu-west-1 | 410ms | 55ms | 88ms | 61ms |
| ap-southeast-1 | 620ms | 590ms | 740ms | 64ms |

---

## Key Takeaways

1. **Geography dominates** — same-region S3 is unbeatable at ~42ms
2. **Cross-region S3** degrades to 380–620ms, comparable to or worse than Storacha CDN
3. **Remote IPFS** (single pin, no CDN) is consistently slowest due to routing overhead
4. **Storacha CDN** delivers ~64ms globally — competitive with regional S3 for most users
5. **Under load**, Storacha CDN showed rate limiting on the free tier; paid tier resolves this

---

## Recommendation

For resilience-first workflows:
- **Primary access:** Regional S3 (best performance for co-located compute)
- **Archival + verification:** Storacha/Filecoin (CID-pinned, institution-independent)
- **Public distribution:** Storacha CDN (`w3s.link`) — good enough for most users globally

Don't rely on a single remote IPFS node without CDN acceleration.

---

## Raw Data

See `benchmarks/raw/oisst-latency-2026-03.csv` (forthcoming).
