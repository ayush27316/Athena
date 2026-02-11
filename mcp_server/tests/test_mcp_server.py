"""
Tests for the MCP server - verifies tools are registered and return
well-structured markdown tables that ChatGPT can render.

Uses FastMCP's direct call_tool/list_tools methods for in-process testing
without starting an HTTP server.
"""

import pytest

from mcp_server.server import mcp

pytestmark = pytest.mark.asyncio


def _get_text(result) -> str:
    """Extract text from tool call result.

    call_tool returns a tuple of (content_blocks, extras_dict).
    """
    content_blocks = result[0] if isinstance(result, tuple) else result
    return content_blocks[0].text


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
    async def test_returns_markdown_table(self):
        result = await mcp.call_tool("get_database_schema", {})
        text = _get_text(result)
        assert "# Greenhouse Database Schema" in text
        assert "| Column | Type | Sample Values |" in text
        assert "DataSource" in text
        assert "geometry" in text

    async def test_table_has_all_columns(self):
        result = await mcp.call_tool("get_database_schema", {})
        text = _get_text(result)
        for col in ["DataSource", "ImageDate", "Latitude", "Longitude", "PRUID", "PROV_TERR"]:
            assert col in text, f"Missing column {col} in schema table"


class TestGetStatistics:
    async def test_returns_markdown_with_total(self):
        result = await mcp.call_tool("get_statistics", {})
        text = _get_text(result)
        assert "# Greenhouse Database Statistics" in text
        assert "**Total greenhouses:**" in text
        assert "2476" in text or "2,476" in text

    async def test_has_province_table(self):
        result = await mcp.call_tool("get_statistics", {})
        text = _get_text(result)
        assert "## Greenhouses by Province" in text
        assert "| Province | Count |" in text
        assert "Ontario" in text

    async def test_has_area_stats_table(self):
        result = await mcp.call_tool("get_statistics", {})
        text = _get_text(result)
        assert "## Area Statistics" in text
        assert "| Metric | Value |" in text
        assert "Mean" in text
        assert "Median" in text

    async def test_has_geographic_coverage(self):
        result = await mcp.call_tool("get_statistics", {})
        text = _get_text(result)
        assert "## Geographic Coverage" in text
        assert "Latitude" in text
        assert "Longitude" in text


class TestSearchGreenhouses:
    async def test_default_search_returns_table(self):
        result = await mcp.call_tool("search_greenhouses", {})
        text = _get_text(result)
        assert "# Search Results" in text
        assert "| ID | Province | Data Source | Image Year | Latitude | Longitude | Area" in text
        # Should have data rows (pipes in table body)
        lines = text.strip().split("\n")
        data_rows = [l for l in lines if l.startswith("| ") and "---" not in l and "ID" not in l]
        assert len(data_rows) > 0

    async def test_filter_by_province(self):
        result = await mcp.call_tool("search_greenhouses", {"province": "Ontario"})
        text = _get_text(result)
        assert "Ontario" in text
        # All data rows should contain Ontario
        lines = text.strip().split("\n")
        data_rows = [l for l in lines if l.startswith("| ") and "---" not in l and "ID" not in l and "Showing" not in l]
        for row in data_rows:
            assert "Ontario" in row

    async def test_filter_by_year(self):
        result = await mcp.call_tool("search_greenhouses", {"image_year": 2020})
        text = _get_text(result)
        lines = text.strip().split("\n")
        data_rows = [l for l in lines if l.startswith("| ") and "---" not in l and "ID" not in l and "Showing" not in l]
        for row in data_rows:
            assert "2020" in row

    async def test_pagination_info(self):
        result = await mcp.call_tool("search_greenhouses", {"limit": 3, "offset": 0})
        text = _get_text(result)
        assert "Showing 1" in text

    async def test_empty_result(self):
        result = await mcp.call_tool("search_greenhouses", {"province": "NonExistentProvince"})
        text = _get_text(result)
        assert "No greenhouses found" in text


class TestGetGreenhouse:
    async def test_valid_id_returns_detail_table(self):
        result = await mcp.call_tool("get_greenhouse", {"greenhouse_id": 0})
        text = _get_text(result)
        assert "# Greenhouse #0" in text
        assert "| Field | Value |" in text
        assert "Province" in text
        assert "Latitude" in text
        assert "Area" in text

    async def test_includes_geojson(self):
        result = await mcp.call_tool("get_greenhouse", {"greenhouse_id": 0})
        text = _get_text(result)
        assert "## GeoJSON Geometry" in text
        assert "```json" in text
        assert "Polygon" in text

    async def test_invalid_id(self):
        result = await mcp.call_tool("get_greenhouse", {"greenhouse_id": 999999})
        text = _get_text(result)
        assert "Error" in text
        assert "not found" in text


class TestGetProvinces:
    async def test_returns_province_table(self):
        result = await mcp.call_tool("get_provinces", {})
        text = _get_text(result)
        assert "# Greenhouse Summary by Province" in text
        assert "| Province | Count | Total Area" in text

    async def test_all_provinces_present(self):
        result = await mcp.call_tool("get_provinces", {})
        text = _get_text(result)
        for province in ["Alberta", "British Columbia", "Ontario", "Quebec"]:
            assert province in text, f"Missing province: {province}"

    async def test_has_image_years(self):
        result = await mcp.call_tool("get_provinces", {})
        text = _get_text(result)
        assert "Image Years" in text
        # Should have actual year values
        assert "2020" in text
