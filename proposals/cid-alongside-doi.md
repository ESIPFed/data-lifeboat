# Proposal: CID-alongside-DOI for DataCite Metadata

**Status:** Draft  
**Author:** CODED Working Group, ESIP Federation  
**Date:** 2026-03

---

## Summary

We propose adding content-addressable identifiers (CIDs) as a standard `alternateIdentifier` type in DataCite metadata records. This allows any dataset with a DOI to also carry a cryptographically verifiable, decentralized content fingerprint.

---

## Motivation

DOIs are location-independent persistent identifiers — they tell you *what* something is, but rely on a resolver infrastructure to tell you *where* it is. If the resolver breaks, or the hosting institution disappears, the DOI becomes a dead link.

IPFS CIDs are *content*-addressed: the identifier is derived from the data itself. If you have the CID, you can verify any copy of the data against it — regardless of where it came from.

Pairing these two systems gives datasets:
1. **Discoverability** — via DOI and standard metadata catalogs
2. **Verifiability** — via CID, anyone can confirm they have the right bytes
3. **Resilience** — CID-pinned copies on IPFS/Filecoin survive institutional failure

---

## Proposed DataCite Schema Addition

In the `alternateIdentifiers` field:

```xml
<alternateIdentifiers>
  <alternateIdentifier alternateIdentifierType="CIDv1">
    bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q
  </alternateIdentifier>
</alternateIdentifiers>
```

Or in JSON:

```json
"alternateIdentifiers": [
  {
    "alternateIdentifierType": "CIDv1",
    "alternateIdentifier": "bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q"
  }
]
```

---

## Generating a Stable CID

CIDv1 for a Zarr store can be computed without uploading:

```bash
# Requires: ipfs daemon or kubo CLI
ipfs add --only-hash --recursive --cid-version 1 my-dataset.zarr
```

This produces a deterministic CID based solely on the content. The same dataset on any machine will produce the same CID.

---

## Implementation Path

1. **Short term:** Add CID as `alternateIdentifier` in existing DataCite records (no schema change required — `alternateIdentifierType` is a free-text field)
2. **Medium term:** Propose `CIDv1` as a recognized `alternateIdentifierType` in DataCite vocabulary
3. **Long term:** Automate CID generation in data publication pipelines (e.g., Pangeo Forge, NCAR RDA)

---

## References

- [DataCite Metadata Schema 4.5](https://schema.datacite.org/meta/kernel-4/)
- [IPFS CID specification](https://docs.ipfs.tech/concepts/content-addressing/)
- [Storacha / web3.storage](https://storacha.network)
- CODED benchmark results: see `benchmarks/`
