# Recipe: Pin a Zarr Dataset to Storacha (Filecoin-backed IPFS)

**Time:** ~10 minutes  
**Prerequisites:** Node.js, a Storacha account  

---

## 1. Install the Storacha CLI

```bash
npm install -g @web3-storage/w3cli
```

## 2. Authenticate

```bash
w3 login your@email.com
# Follow the email link to verify
```

## 3. Create a Space (one-time)

```bash
w3 space create my-datasets
w3 space use my-datasets
```

## 4. Upload Your Zarr Store

```bash
w3 up /path/to/my-dataset.zarr --name "Dataset Name vX.Y"
```

This recursively uploads all chunks and metadata. Output will include a CID.

## 5. Verify

```bash
w3 ls
# Lists all uploads with CIDs

# Test access via HTTP gateway
curl -I "https://<YOUR_CID>.ipfs.w3s.link/.zattrs"
```

## 6. Record Your CID

Add it to your dataset's DataCite metadata as an `alternateIdentifier`:

```json
{
  "alternateIdentifierType": "CIDv1",
  "alternateIdentifier": "<YOUR_CID>"
}
```

---

## Notes

- Storacha stores data on Filecoin with cryptographic storage receipts
- The `w3s.link` gateway provides CDN-accelerated access (~64ms globally)
- CIDs are immutable — any change to the data produces a new CID
- For mutable datasets, consider [Icechunk](https://icechunk.io) for versioned snapshots, each with their own CID

---

## Tested With

- OISST v2.1 SST (3GB Zarr) — CID: `bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q`
- EC2 us-east-1, Storacha free tier
