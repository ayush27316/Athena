"""Tests for the database layer - verifies shapefile loading and querying."""

import pytest

from mcp_server.database import (
    get_greenhouse_by_id,
    get_province_summary,
    get_schema,
    get_summary_stats,
    load_data,
    query_greenhouses,
)


class TestLoadData:
    def test_loads_shapefile(self):
        gdf = load_data()
        assert gdf is not None
        assert len(gdf) > 0

    def test_has_expected_columns(self):
        gdf = load_data()
        expected_cols = ["DataSource", "ImageDate", "Latitude", "Longitude", "PRUID", "PROV_TERR"]
        for col in expected_cols:
            assert col in gdf.columns, f"Missing column: {col}"

    def test_reprojected_to_wgs84(self):
        gdf = load_data()
        assert gdf.crs is not None
        assert gdf.crs.to_epsg() == 4326

    def test_record_count(self):
        gdf = load_data()
        # The dataset should have ~2476 records
        assert len(gdf) > 2000
        assert len(gdf) < 3000


class TestGetSchema:
    def test_returns_all_columns(self):
        schema = get_schema()
        assert "DataSource" in schema
        assert "ImageDate" in schema
        assert "Latitude" in schema
        assert "Longitude" in schema
        assert "PRUID" in schema
        assert "PROV_TERR" in schema
        assert "geometry" in schema

    def test_schema_has_type_info(self):
        schema = get_schema()
        assert "type" in schema["DataSource"]
        assert "sample_values" in schema["DataSource"]


class TestGetSummaryStats:
    def test_returns_total_count(self):
        stats = get_summary_stats()
        assert "total_greenhouses" in stats
        assert stats["total_greenhouses"] > 2000

    def test_returns_province_breakdown(self):
        stats = get_summary_stats()
        assert "provinces" in stats
        provinces = stats["provinces"]
        assert len(provinces) > 0
        # Ontario should have the most greenhouses
        assert "Ontario" in provinces

    def test_returns_area_stats(self):
        stats = get_summary_stats()
        area = stats["area_stats_sq_meters"]
        assert area["min"] >= 0  # some records may have degenerate polygons
        assert area["max"] > area["min"]
        assert area["mean"] > 0
        assert area["total"] > 0

    def test_returns_coordinate_ranges(self):
        stats = get_summary_stats()
        lat = stats["latitude_range"]
        lon = stats["longitude_range"]
        # Canada latitudes are roughly 42-84 N
        assert lat["min"] > 40
        assert lat["max"] < 85
        # Canada longitudes are roughly -141 to -52 W
        assert lon["min"] > -145
        assert lon["max"] < -50


class TestQueryGreenhouses:
    def test_default_query(self):
        result = query_greenhouses()
        assert "total" in result
        assert "records" in result
        assert result["total"] > 0
        assert len(result["records"]) <= 50  # default limit

    def test_filter_by_province(self):
        result = query_greenhouses(province="Ontario")
        assert result["total"] > 0
        for record in result["records"]:
            assert "Ontario" in record["province"]

    def test_filter_by_province_case_insensitive(self):
        result = query_greenhouses(province="ontario")
        assert result["total"] > 0

    def test_filter_by_image_year(self):
        result = query_greenhouses(image_year=2020)
        assert result["total"] >= 0
        for record in result["records"]:
            assert record["image_year"] == 2020

    def test_filter_by_min_area(self):
        result = query_greenhouses(min_area=10000)
        for record in result["records"]:
            assert record["area_sq_meters"] >= 10000

    def test_pagination(self):
        page1 = query_greenhouses(limit=5, offset=0)
        page2 = query_greenhouses(limit=5, offset=5)
        assert len(page1["records"]) == 5
        assert len(page2["records"]) == 5
        # Records should be different
        ids1 = {r["id"] for r in page1["records"]}
        ids2 = {r["id"] for r in page2["records"]}
        assert ids1.isdisjoint(ids2)

    def test_limit_capped_at_500(self):
        result = query_greenhouses(limit=1000)
        assert result["limit"] == 500

    def test_record_fields(self):
        result = query_greenhouses(limit=1)
        record = result["records"][0]
        assert "id" in record
        assert "data_source" in record
        assert "image_year" in record
        assert "latitude" in record
        assert "longitude" in record
        assert "province" in record
        assert "pruid" in record
        assert "area_sq_meters" in record


class TestGetGreenhouseById:
    def test_valid_id(self):
        record = get_greenhouse_by_id(0)
        assert record is not None
        assert record["id"] == 0
        assert "geometry_geojson" in record
        assert record["geometry_geojson"]["type"] in ("Polygon", "MultiPolygon")

    def test_invalid_id_negative(self):
        record = get_greenhouse_by_id(-1)
        assert record is None

    def test_invalid_id_too_large(self):
        record = get_greenhouse_by_id(999999)
        assert record is None

    def test_has_all_fields(self):
        record = get_greenhouse_by_id(0)
        expected_fields = [
            "id", "data_source", "image_year", "latitude", "longitude",
            "province", "pruid", "area_sq_meters", "geometry_geojson",
        ]
        for field in expected_fields:
            assert field in record, f"Missing field: {field}"


class TestGetProvinceSummary:
    def test_returns_list(self):
        summary = get_province_summary()
        assert isinstance(summary, list)
        assert len(summary) > 0

    def test_summary_fields(self):
        summary = get_province_summary()
        for item in summary:
            assert "province" in item
            assert "greenhouse_count" in item
            assert "total_area_sq_meters" in item
            assert "avg_area_sq_meters" in item
            assert "image_years" in item

    def test_counts_sum_to_total(self):
        summary = get_province_summary()
        total = sum(item["greenhouse_count"] for item in summary)
        stats = get_summary_stats()
        assert total == stats["total_greenhouses"]
