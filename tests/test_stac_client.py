"""Unit tests for CDSE STAC client."""

import pytest
from unittest.mock import MagicMock, patch
from src.stac_client import CDSESTACClient, STACError


def test_bbox_validation():
    client = CDSESTACClient()
    # Invalid length
    with pytest.raises(ValueError, match="bbox must contain exactly 4 floats"):
        client.search_scenes(bbox=[80.0, 26.0, 81.0], datetime_range="2024-01-01/2024-01-02")

    # Inverted coordinates
    with pytest.raises(ValueError, match="Invalid bounding box"):
        client.search_scenes(bbox=[81.0, 26.0, 80.0, 27.0], datetime_range="2024-01-01/2024-01-02")


def test_extract_item_metadata():
    client = CDSESTACClient()
    mock_item = {
        "id": "S2A_MSIL2A_20240527T050651_N0510_R019_T44RMQ_20240527T101752",
        "collection": "sentinel-2-l2a",
        "geometry": {"type": "Polygon", "coordinates": [[[80.0, 26.0], [81.5, 26.0], [81.5, 27.5], [80.0, 27.5], [80.0, 26.0]]]},
        "bbox": [80.0, 26.0, 81.5, 27.5],
        "properties": {
            "datetime": "2024-05-27T05:06:51.024000Z",
            "eo:cloud_cover": 0.0,
            "platform": "sentinel-2a",
            "s2:mgrs_tile": "44RMQ"
        },
        "assets": {
            "B03_10m": {
                "href": "s3://eodata/path/to/B03_10m.jp2",
                "alternate": {
                    "https": {
                        "href": "https://download.dataspace.copernicus.eu/odata/v1/Products(123)/Nodes(B03)/$value"
                    }
                },
                "type": "image/jp2",
                "file:size": 102400
            },
            "B08_10m": {
                "href": "s3://eodata/path/to/B08_10m.jp2",
                "alternate": {
                    "https": {
                        "href": "https://download.dataspace.copernicus.eu/odata/v1/Products(123)/Nodes(B08)/$value"
                    }
                },
                "type": "image/jp2",
                "file:size": 105600
            },
            "thumbnail": {
                "href": "https://datahub.creodias.eu/odata/v1/Assets(456)/$value"
            }
        }
    }

    meta = client.extract_item_metadata(mock_item)
    assert meta["id"] == "S2A_MSIL2A_20240527T050651_N0510_R019_T44RMQ_20240527T101752"
    assert meta["cloud_cover"] == 0.0
    assert meta["tile_id"] == "44RMQ"
    assert meta["thumbnail_url"] == "https://datahub.creodias.eu/odata/v1/Assets(456)/$value"
    assert meta["b03_asset"] is not None
    assert meta["b03_asset"]["https_href"] == "https://download.dataspace.copernicus.eu/odata/v1/Products(123)/Nodes(B03)/$value"
    assert meta["b08_asset"] is not None
    assert meta["b08_asset"]["https_href"] == "https://download.dataspace.copernicus.eu/odata/v1/Products(123)/Nodes(B08)/$value"


def test_stac_http_error_handling():
    client = CDSESTACClient()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(client.session, "post", return_value=mock_response):
        with pytest.raises(STACError, match="HTTP 500"):
            client.search_scenes(bbox=[80.88, 26.80, 81.00, 26.90], datetime_range="2024-01-01/2024-01-02")
