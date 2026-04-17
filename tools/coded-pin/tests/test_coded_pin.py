"""
Smoke tests for coded-pin.

Run with:
    pip install -e ".[dev]"
    pytest tests/ -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import xarray as xr
import zarr
import icechunk


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_zarr(tmp_path):
    """Create a tiny test Zarr store."""
    store_path = tmp_path / "test.zarr"
    ds = xr.Dataset(
        {
            "sst": (["time", "lat", "lon"], np.random.rand(3, 4, 8).astype("float32")),
        },
        coords={
            "time": np.arange(3),
            "lat": np.linspace(-90, 90, 4),
            "lon": np.linspace(-180, 180, 8),
        },
    )
    ds.to_zarr(str(store_path), mode="w")
    return store_path


@pytest.fixture
def sample_netcdf(tmp_path):
    """Create a tiny test NetCDF4 file."""
    nc_path = tmp_path / "test.nc"
    ds = xr.Dataset(
        {
            "sst": (["time", "lat", "lon"], np.random.rand(2, 4, 8).astype("float32")),
        },
        coords={
            "time": np.arange(2),
            "lat": np.linspace(-90, 90, 4),
            "lon": np.linspace(-180, 180, 8),
        },
    )
    ds.to_netcdf(str(nc_path))
    return nc_path


# ─────────────────────────────────────────────────────────────────────────────
# pin.py tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractCid:
    def test_json_root_dict(self):
        from coded_pin.pin import _extract_cid
        output = '{"root": {"/": "bafybeig3x7abc123"}, "shards": []}'
        assert _extract_cid(output) == "bafybeig3x7abc123"

    def test_json_root_string(self):
        from coded_pin.pin import _extract_cid
        output = '{"root": "bafybeig3x7abc123"}'
        assert _extract_cid(output) == "bafybeig3x7abc123"

    def test_regex_fallback(self):
        from coded_pin.pin import _extract_cid
        # Valid base32 CIDv1 (only a-z and 2-7, >=50 chars after "baf")
        output = "Uploaded: bafybeigdyhc3tjrxmpkj5f2wmdklzxpzatqnmhvkahsqmrzmjgmipzfty"
        cid = _extract_cid(output)
        assert cid.startswith("baf")

    def test_raises_on_empty(self):
        from coded_pin.pin import _extract_cid
        with pytest.raises(ValueError, match="Could not parse CID"):
            _extract_cid("no cid here")

    def test_gateway_url(self):
        from coded_pin.pin import gateway_url
        url = gateway_url("bafybeiabc123")
        assert url == "https://bafybeiabc123.ipfs.w3s.link"

    def test_gateway_url_with_path(self):
        from coded_pin.pin import gateway_url
        url = gateway_url("bafybeiabc123", ".zattrs")
        assert url == "https://bafybeiabc123.ipfs.w3s.link/.zattrs"


# ─────────────────────────────────────────────────────────────────────────────
# native.py tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNative:
    def test_write_zarr_to_icechunk(self, sample_zarr, tmp_path):
        """Write a Zarr store to Icechunk without pinning."""
        from coded_pin.native import publish_native

        result = publish_native(
            str(sample_zarr),
            output_dir=tmp_path / "ic_output",
            collection_name="test-native",
            pin=False,
        )

        assert result["store_path"] is not None
        assert result["snapshot_id"] is not None
        assert result["cid"] is None  # no pin

        # Verify we can round-trip read
        storage = icechunk.local_filesystem_storage(result["store_path"])
        repo = icechunk.Repository.open(storage)
        store = repo.readonly_session("main").store
        ds_out = xr.open_zarr(store)
        assert "sst" in ds_out.data_vars

    def test_write_netcdf_to_icechunk(self, sample_netcdf, tmp_path):
        """Write a NetCDF file to Icechunk without pinning."""
        from coded_pin.native import publish_native

        result = publish_native(
            str(sample_netcdf),
            output_dir=tmp_path / "ic_output",
            collection_name="test-native-nc",
            pin=False,
        )

        assert result["snapshot_id"] is not None

    def test_rechunking(self, sample_zarr, tmp_path):
        """Test that rechunking is applied."""
        from coded_pin.native import publish_native

        result = publish_native(
            str(sample_zarr),
            output_dir=tmp_path / "ic_output",
            collection_name="test-rechunked",
            pin=False,
            chunks={"time": 1, "lat": 2, "lon": 4},
        )

        assert result["snapshot_id"] is not None

    def test_pin_called_when_enabled(self, sample_zarr, tmp_path):
        """upload_to_storacha should be called when pin=True."""
        from coded_pin import native as native_mod

        with patch.object(native_mod, "upload_to_storacha", return_value="bafytest123") as mock_upload:
            result = native_mod.publish_native(
                str(sample_zarr),
                output_dir=tmp_path / "ic_output",
                collection_name="test-pinned",
                pin=True,
            )

        mock_upload.assert_called_once()
        assert result["cid"] == "bafytest123"
        assert "w3s.link" in result["gateway_url"]


# ─────────────────────────────────────────────────────────────────────────────
# ipns.py tests
# ─────────────────────────────────────────────────────────────────────────────

class TestIpns:
    def test_ipns_unavailable_returns_empty(self):
        from coded_pin import ipns as ipns_mod
        with patch("shutil.which", return_value=None):
            result = ipns_mod.ensure_key("test-key")
        assert result == ""

    def test_gateway_url(self):
        from coded_pin.ipns import ipns_gateway_url
        url = ipns_gateway_url("k51qzi5uqu5abc")
        assert "k51qzi5uqu5abc" in url
        assert "ipns" in url


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCli:
    def test_help(self):
        from click.testing import CliRunner
        from coded_pin.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "virtual" in result.output
        assert "native" in result.output

    def test_virtual_help(self):
        from click.testing import CliRunner
        from coded_pin.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["virtual", "--help"])
        assert result.exit_code == 0

    def test_native_help(self):
        from click.testing import CliRunner
        from coded_pin.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["native", "--help"])
        assert result.exit_code == 0

    def test_native_cli_no_pin(self, sample_zarr, tmp_path):
        """End-to-end CLI test: native mode, no upload."""
        from click.testing import CliRunner
        from coded_pin.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            "native", str(sample_zarr),
            "--name", "cli-test",
            "--pin", "none",
            "--output-dir", str(tmp_path / "output"),
        ])

        assert result.exit_code == 0, result.output
        assert "Snapshot" in result.output or "Committed" in result.output
