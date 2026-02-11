"""
MCP Server for the StatCan Open Database of Greenhouses (ODG_V1).

Exposes the shapefile data over JSON-RPC via Streamable HTTP transport,
compatible with ChatGPT web app connectors.

Run:
    python -m mcp_server.server
    # or:
    python mcp_server/server.py
"""

import json
import os

from mcp.server.fastmcp import FastMCP

from mcp_server.database import (
    get_greenhouse_by_id,
    get_province_summary,
    get_schema,
    get_summary_stats,
    query_greenhouses,
)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

mcp = FastMCP(
    "StatCan Greenhouse Database",
    instructions=(
        "This MCP server provides access to Statistics Canada's Open Database "
        "of Greenhouses (ODG v1). The database contains 2,476 greenhouse polygon "
        "records across Canadian provinces (Ontario, Quebec, British Columbia, Alberta) "
        "identified from satellite imagery. You can query greenhouses by province, "
        "area, image year, or get aggregate statistics. "
        "Tool responses include markdown tables — render them directly for the user."
    ),
    host=HOST,
    port=PORT,
)


@mcp.tool()
def get_database_schema() -> str:
    """
    Get the schema of the greenhouse database, including column names,
    data types, and sample values. Use this to understand what data is
    available before querying.
    """
    schema = get_schema()

    lines = ["# Greenhouse Database Schema", ""]
    lines.append("| Column | Type | Sample Values |")
    lines.append("|--------|------|---------------|")
    for col, info in schema.items():
        col_type = info.get("type", "")
        samples = info.get("sample_values", info.get("description", ""))
        if isinstance(samples, list):
            samples = ", ".join(str(s) for s in samples)
        lines.append(f"| {col} | {col_type} | {samples} |")

    return "\n".join(lines)


@mcp.tool()
def get_statistics() -> str:
    """
    Get aggregate statistics about all greenhouses in the database.
    Returns total count, breakdown by province, breakdown by image year,
    area statistics (mean, median, min, max, total in square meters),
    and coordinate ranges.
    """
    stats = get_summary_stats()

    lines = [f"# Greenhouse Database Statistics", ""]
    lines.append(f"**Total greenhouses:** {stats['total_greenhouses']}")
    lines.append("")

    # Province table
    lines.append("## Greenhouses by Province")
    lines.append("")
    lines.append("| Province | Count |")
    lines.append("|----------|-------|")
    for province, count in stats["provinces"].items():
        lines.append(f"| {province} | {count} |")
    lines.append("")

    # Image year table
    lines.append("## Greenhouses by Image Year")
    lines.append("")
    lines.append("| Year | Count |")
    lines.append("|------|-------|")
    for year, count in stats["image_years"].items():
        lines.append(f"| {year} | {count} |")
    lines.append("")

    # Area stats table
    area = stats["area_stats_sq_meters"]
    lines.append("## Area Statistics (square meters)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Mean | {area['mean']:,.2f} |")
    lines.append(f"| Median | {area['median']:,.2f} |")
    lines.append(f"| Min | {area['min']:,.2f} |")
    lines.append(f"| Max | {area['max']:,.2f} |")
    lines.append(f"| Total | {area['total']:,.2f} |")
    lines.append("")

    # Coordinate ranges
    lat = stats["latitude_range"]
    lon = stats["longitude_range"]
    lines.append("## Geographic Coverage")
    lines.append("")
    lines.append("| Coordinate | Min | Max |")
    lines.append("|------------|-----|-----|")
    lines.append(f"| Latitude | {lat['min']} | {lat['max']} |")
    lines.append(f"| Longitude | {lon['min']} | {lon['max']} |")

    return "\n".join(lines)


@mcp.tool()
def search_greenhouses(
    province: str | None = None,
    min_area_sq_meters: float | None = None,
    max_area_sq_meters: float | None = None,
    image_year: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """
    Search and filter greenhouses in the database.

    Args:
        province: Filter by province name (e.g. "Ontario", "Quebec",
                  "British Columbia", "Alberta"). Case-insensitive partial match.
        min_area_sq_meters: Minimum greenhouse area in square meters.
        max_area_sq_meters: Maximum greenhouse area in square meters.
        image_year: Filter by the year the satellite image was taken
                    (e.g. 2017, 2018, 2020, 2021).
        limit: Maximum number of records to return (default 20, max 500).
        offset: Number of records to skip for pagination.

    Returns:
        Markdown table of greenhouse records with pagination info.
    """
    result = query_greenhouses(
        province=province,
        min_area=min_area_sq_meters,
        max_area=max_area_sq_meters,
        image_year=image_year,
        limit=limit,
        offset=offset,
    )

    total = result["total"]
    records = result["records"]
    off = result["offset"]
    lim = result["limit"]

    lines = [f"# Search Results", ""]
    lines.append(f"**Showing {off + 1}–{off + len(records)} of {total} greenhouses**")
    lines.append("")

    if records:
        lines.append("| ID | Province | Data Source | Image Year | Latitude | Longitude | Area (m²) |")
        lines.append("|----|----------|-------------|------------|----------|-----------|-----------|")
        for r in records:
            lines.append(
                f"| {r['id']} "
                f"| {r['province']} "
                f"| {r['data_source']} "
                f"| {r['image_year']} "
                f"| {r['latitude']} "
                f"| {r['longitude']} "
                f"| {r['area_sq_meters']:,.2f} |"
            )
    else:
        lines.append("*No greenhouses found matching the given filters.*")

    if total > off + lim:
        lines.append("")
        lines.append(f"*Use `offset={off + lim}` to see the next page.*")

    return "\n".join(lines)


@mcp.tool()
def get_greenhouse(greenhouse_id: int) -> str:
    """
    Get detailed information about a specific greenhouse by its ID,
    including its GeoJSON polygon geometry.

    Args:
        greenhouse_id: The numeric ID of the greenhouse (0-based index).
    """
    record = get_greenhouse_by_id(greenhouse_id)
    if record is None:
        return f"**Error:** Greenhouse with ID {greenhouse_id} not found."

    geojson = record.pop("geometry_geojson", None)

    lines = [f"# Greenhouse #{record['id']}", ""]
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| ID | {record['id']} |")
    lines.append(f"| Province | {record['province']} |")
    lines.append(f"| Data Source | {record['data_source']} |")
    lines.append(f"| Image Year | {record['image_year']} |")
    lines.append(f"| Latitude | {record['latitude']} |")
    lines.append(f"| Longitude | {record['longitude']} |")
    lines.append(f"| PRUID | {record['pruid']} |")
    lines.append(f"| Area (m²) | {record['area_sq_meters']:,.2f} |")
    if record.get('perimeter_meters') is not None:
        lines.append(f"| Perimeter (m) | {record['perimeter_meters']:,.2f} |")

    if geojson:
        lines.append("")
        lines.append("## GeoJSON Geometry")
        lines.append("")
        lines.append(f"```json\n{json.dumps(geojson, indent=2)}\n```")

    return "\n".join(lines)


@mcp.tool()
def get_provinces() -> str:
    """
    Get a summary breakdown by province, including greenhouse count,
    total area, average area, and which image years are available
    for each province.
    """
    summary = get_province_summary()

    lines = ["# Greenhouse Summary by Province", ""]
    lines.append("| Province | Count | Total Area (m²) | Avg Area (m²) | Image Years |")
    lines.append("|----------|-------|------------------|---------------|-------------|")
    for item in summary:
        years = ", ".join(str(y) for y in item["image_years"])
        lines.append(
            f"| {item['province']} "
            f"| {item['greenhouse_count']} "
            f"| {item['total_area_sq_meters']:,.2f} "
            f"| {item['avg_area_sq_meters']:,.2f} "
            f"| {years} |"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
