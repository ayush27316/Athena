"""
Tests for the MCP server - verifies tools are registered and return
structured table format: {"type": "table", "columns": [...], "rows": [...]}.

Uses FastMCP's direct call_tool/list_tools methods for in-process testing
without starting an HTTP server.
"""

import json

import pytest

from mcp_server.server import mcp

pytestmark = pytest.mark.asyncio


def _get_json(result) -> dict | list:
    """Extract parsed JSON from tool call result."""
    content_blocks = result[0] if isinstance(result, tuple) else result
    return json.loads(content_blocks[0].text)


def _assert_table(obj, expected_columns=None):
    """Assert obj follows the table format: type, columns, rows."""
    assert obj["type"] == "table"
    assert isinstance(obj["columns"], list)
    assert isinstance(obj["rows"], list)
    if expected_columns:
        assert obj["columns"] == expected_columns
    # Every row should have the same number of values as columns
    for row in obj["rows"]:
        assert len(row) == len(obj["columns"])


class TestToolRegistration:
    async def test_lists_all_tools(self):
        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "get_database_schema",
            "get_statistics",
            "search_greenhouses",
            "get_greenhouse",
            "get_provinces",
        }
        assert expected == tool_names

    async def test_tools_have_descriptions(self):
        tools = await mcp.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"

    async def test_search_tool_has_parameters(self):
        tools = await mcp.list_tools()
        search_tool = next(t for t in tools if t.name == "search_greenhouses")
        schema = search_tool.inputSchema
        props = schema.get("properties", {})
        assert "province" in props
        assert "min_area_sq_meters" in props
        assert "image_year" in props
        assert "limit" in props
        assert "offset" in props


class TestGetDatabaseSchema:
    async def test_returns_table_format(self):
        data = _get_json(await mcp.call_tool("get_database_schema", {}))
        _assert_table(data, ["Column", "Type", "Sample Values"])

    async def test_has_all_columns(self):
        data = _get_json(await mcp.call_tool("get_database_schema", {}))
        col_names = [row[0] for row in data["rows"]]
        for col in ["DataSource", "ImageDate", "Latitude", "Longitude", "PRUID", "PROV_TERR", "geometry"]:
            assert col in col_names, f"Missing column {col}"


class TestGetStatistics:
    async def test_has_total_greenhouses(self):
        data = _get_json(await mcp.call_tool("get_statistics", {}))
        assert data["total_greenhouses"] > 2000

    async def test_provinces_table(self):
        data = _get_json(await mcp.call_tool("get_statistics", {}))
        _assert_table(data["provinces"], ["Province", "Count"])
        province_names = [row[0] for row in data["provinces"]["rows"]]
        assert "Ontario" in province_names

    async def test_image_years_table(self):
        data = _get_json(await mcp.call_tool("get_statistics", {}))
        _assert_table(data["image_years"], ["Year", "Count"])

    async def test_area_stats_table(self):
        data = _get_json(await mcp.call_tool("get_statistics", {}))
        _assert_table(data["area_stats"], ["Metric", "Value (m²)"])
        metrics = [row[0] for row in data["area_stats"]["rows"]]
        assert "Mean" in metrics
        assert "Median" in metrics
        assert "Total" in metrics

    async def test_geographic_coverage_table(self):
        data = _get_json(await mcp.call_tool("get_statistics", {}))
        _assert_table(data["geographic_coverage"], ["Coordinate", "Min", "Max"])


class TestSearchGreenhouses:
    async def test_default_search(self):
        data = _get_json(await mcp.call_tool("search_greenhouses", {}))
        assert data["total"] > 0
        _assert_table(data["results"], ["ID", "Province", "Data Source", "Image Year", "Latitude", "Longitude", "Area (m²)"])
        assert len(data["results"]["rows"]) > 0

    async def test_filter_by_province(self):
        data = _get_json(await mcp.call_tool("search_greenhouses", {"province": "Ontario"}))
        assert data["total"] > 0
        # Province is column index 1
        for row in data["results"]["rows"]:
            assert "Ontario" in row[1]

    async def test_filter_by_year(self):
        data = _get_json(await mcp.call_tool("search_greenhouses", {"image_year": 2020}))
        # Image Year is column index 3
        for row in data["results"]["rows"]:
            assert row[3] == 2020

    async def test_pagination(self):
        d1 = _get_json(await mcp.call_tool("search_greenhouses", {"limit": 3, "offset": 0}))
        d2 = _get_json(await mcp.call_tool("search_greenhouses", {"limit": 3, "offset": 3}))
        ids1 = {row[0] for row in d1["results"]["rows"]}
        ids2 = {row[0] for row in d2["results"]["rows"]}
        assert ids1.isdisjoint(ids2)

    async def test_empty_result(self):
        data = _get_json(await mcp.call_tool("search_greenhouses", {"province": "NonExistentProvince"}))
        assert data["total"] == 0
        assert len(data["results"]["rows"]) == 0


class TestGetGreenhouse:
    async def test_valid_id(self):
        data = _get_json(await mcp.call_tool("get_greenhouse", {"greenhouse_id": 0}))
        _assert_table(data["details"], ["Field", "Value"])
        # Check fields are present
        fields = [row[0] for row in data["details"]["rows"]]
        assert "ID" in fields
        assert "Province" in fields
        assert "Latitude" in fields
        assert "Area (m²)" in fields

    async def test_includes_geojson(self):
        data = _get_json(await mcp.call_tool("get_greenhouse", {"greenhouse_id": 0}))
        assert "geometry_geojson" in data
        assert data["geometry_geojson"]["type"] in ("Polygon", "MultiPolygon")

    async def test_invalid_id(self):
        data = _get_json(await mcp.call_tool("get_greenhouse", {"greenhouse_id": 999999}))
        assert "error" in data


class TestGetProvinces:
    async def test_returns_table_format(self):
        data = _get_json(await mcp.call_tool("get_provinces", {}))
        _assert_table(data, ["Province", "Count", "Total Area (m²)", "Avg Area (m²)", "Image Years"])

    async def test_all_provinces_present(self):
        data = _get_json(await mcp.call_tool("get_provinces", {}))
        provinces = [row[0] for row in data["rows"]]
        for p in ["Alberta", "British Columbia", "Ontario", "Quebec"]:
            assert p in provinces, f"Missing province: {p}"

    async def test_row_values_are_reasonable(self):
        data = _get_json(await mcp.call_tool("get_provinces", {}))
        for row in data["rows"]:
            assert row[1] > 0       # count > 0
            assert row[2] > 0       # total area > 0
            assert row[3] > 0       # avg area > 0
            assert len(row[4]) > 0  # image years not empty
