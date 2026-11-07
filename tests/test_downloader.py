"""Unit tests for CDSE Downloader and security/integrity validations."""

from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
import requests

from src.downloader import (
    CDSEDownloader,
    AuthenticationRequiredError,
    DownloadError,
    LocationTrustedSession,
    _mask_identity,
    verify_raster_file,
)


def test_missing_credentials_raises_auth_error():
    downloader = CDSEDownloader(username="", password="", access_token="")
    assert not downloader.has_credentials()

    with pytest.raises(AuthenticationRequiredError, match="credentials are not configured"):
        downloader.authenticate()


def test_has_credentials_detection():
    d1 = CDSEDownloader(username="test_user", password="secret_password")
    assert d1.has_credentials()

    d2 = CDSEDownloader(access_token="valid_jwt_token")
    assert d2.has_credentials()
    assert d2.authenticate() == "valid_jwt_token"

    d3 = CDSEDownloader(oauth_client_id="client_id", oauth_client_secret="client_secret")
    assert d3.has_credentials()
    assert d3.has_oauth_client()


def test_download_band_requires_auth():
    downloader = CDSEDownloader(username="", password="", access_token="")
    mock_meta = {
        "id": "test_scene",
        "b03_asset": {"https_href": "https://example.com/b03.jp2"}
    }
    with pytest.raises(AuthenticationRequiredError):
        downloader.download_band(mock_meta, "B03")


def test_mask_identity():
    assert _mask_identity("john.doe@example.com") == "jo***@example.com"
    assert _mask_identity("secretuser") == "se***"
    assert _mask_identity("") == "[not configured]"
    assert _mask_identity(None) == "[not configured]"


def test_location_trusted_session_redirect_auth():
    session = LocationTrustedSession()

    # Trusted Copernicus domain should retain auth
    old_url = "https://download.dataspace.copernicus.eu/odata/v1/Products(...)"
    new_url = "https://zipper.dataspace.copernicus.eu/download/file.jp2"
    assert session.should_strip_auth(old_url, new_url) is False

    # External domain should strip auth
    untrusted_url = "https://evil-third-party.com/file"
    assert session.should_strip_auth(old_url, untrusted_url) is True

    # S3 Presigned URL should strip auth to avoid conflicting headers
    s3_url = "https://eodata.s3.eu-central-1.amazonaws.com/granule.jp2?X-Amz-Signature=abcd"
    assert session.should_strip_auth(old_url, s3_url) is True


def test_download_rejects_html_error_response(tmp_path, monkeypatch):
    downloader = CDSEDownloader(access_token="test_token")
    mock_meta = {
        "id": "scene_123",
        "b03_asset": {"https_href": "https://download.dataspace.copernicus.eu/test/b03"}
    }

    class MockResponse:
        status_code = 200
        headers = {"content-type": "text/html; charset=utf-8"}
        text = "<html><body>502 Bad Gateway - Maintenance</body></html>"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def iter_content(self, chunk_size=8192):
            yield b"<html><body>502 Bad Gateway - Maintenance</body></html>"

    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: MockResponse())

    with pytest.raises(DownloadError, match="Server returned 'text/html; charset=utf-8'"):
        downloader.download_band(mock_meta, "B03", output_dir=tmp_path)


def test_download_rejects_truncated_file(tmp_path, monkeypatch):
    downloader = CDSEDownloader(access_token="test_token")
    mock_meta = {
        "id": "scene_123",
        "b03_asset": {"https_href": "https://download.dataspace.copernicus.eu/test/b03"}
    }

    class MockResponse:
        status_code = 200
        headers = {"content-type": "image/jp2"}
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def iter_content(self, chunk_size=8192):
            yield b"Truncated dummy byte sequence"

    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: MockResponse())

    with pytest.raises(DownloadError, match="suspiciously small"):
        downloader.download_band(mock_meta, "B03", output_dir=tmp_path)


def test_download_rejects_corrupted_raster_binary(tmp_path, monkeypatch):
    downloader = CDSEDownloader(access_token="test_token")
    mock_meta = {
        "id": "scene_123",
        "b03_asset": {"https_href": "https://download.dataspace.copernicus.eu/test/b03"}
    }

    # Simulate 1.5 MB of random garbage bytes (not a valid JP2 or GeoTIFF)
    garbage_bytes = b"X" * (1_500_000)

    class MockResponse:
        status_code = 200
        headers = {"content-type": "image/jp2"}
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def iter_content(self, chunk_size=65536):
            for i in range(0, len(garbage_bytes), chunk_size):
                yield garbage_bytes[i:i + chunk_size]

    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: MockResponse())

    with pytest.raises(DownloadError, match="not a valid JP2 raster"):
        downloader.download_band(mock_meta, "B03", output_dir=tmp_path)


def test_verify_raster_file_helper(tmp_path):
    # Non-existent file
    assert verify_raster_file(tmp_path / "non_existent.tif") is False

    # Corrupt / small file
    corrupt_file = tmp_path / "corrupt.tif"
    corrupt_file.write_bytes(b"not a valid raster header")
    assert verify_raster_file(corrupt_file) is False

    # Valid GeoTIFF generated via rasterio
    valid_file = tmp_path / "valid.tif"
    arr = np.ones((100, 100), dtype=np.uint16) * 1000
    transform = from_origin(80.88, 26.90, 10, 10)
    with rasterio.open(
        valid_file,
        "w",
        driver="GTiff",
        height=100,
        width=100,
        count=1,
        dtype=rasterio.uint16,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(arr, 1)

    # Note: verify_raster_file requires file size >= 100_000 bytes
    # Pad file so it passes the size threshold check
    with open(valid_file, "ab") as f:
        f.write(b"\x00" * 150_000)

    assert verify_raster_file(valid_file) is True


def test_generate_synthetic_sample(tmp_path):
    downloader = CDSEDownloader()
    p_b03 = downloader.generate_synthetic_sample(
        scene_id="TEST_SCENE",
        date_str="2023-10-10",
        band="B03",
        is_earlier=True,
        output_dir=tmp_path,
        clip_bbox=[80.88, 26.80, 81.00, 26.90]
    )
    assert p_b03.exists()
    assert verify_raster_file(p_b03) is True

    # Check raster tags and provenance
    with rasterio.open(p_b03) as src:
        tags = src.tags()
        assert tags.get("PROVENANCE") == "SYNTHETIC_BENCHMARK_SAMPLE"
        assert "NOT real satellite observations" in tags.get("DISCLAIMER", "")
        assert src.crs == "EPSG:32644"


def test_retrieve_band_modes(tmp_path):
    downloader = CDSEDownloader()
    scene_meta = {
        "id": "TEST_SCENE_2",
        "datetime": "2023-12-09T05:12:11Z",
        "tile_id": "T44RMQ"
    }

    # Test synthetic mode
    path_synth, prov_synth = downloader.retrieve_band(
        scene_meta, "B08", mode="synthetic", output_dir=tmp_path
    )
    assert prov_synth == "SYNTHETIC_BENCHMARK_SAMPLE"
    assert path_synth.exists()
    assert verify_raster_file(path_synth) is True
