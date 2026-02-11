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
        "Tool responses use a structured table format with type, columns, and rows — "
        "render them as tables for the user."
    ),
    host=HOST,
    port=PORT,
)


@mcp.tool()
def get_database_schema() -> str:
    """
   schema for all columns
    """
    schema = get_schema()

    rows = []
    for col, info in schema.items():
        col_type = info.get("type", "")
        rows.append([col, col_type])

    return json.dumps({
        "type": "table",
        "columns": ["Column", "Type"],
        "rows": rows,
    }, indent=2, default=str)


@mcp.tool()
def get_statistics() -> str:
    """
    Get aggregate statistics about all greenhouses in the database.
    Returns total count, breakdown by province, breakdown by image year,
    area statistics (mean, median, min, max, total in square meters),
    and coordinate ranges.
    """
    stats = get_summary_stats()

    province_table = {
        "type": "table",
        "columns": ["Province", "Count"],
        "rows": [[p, c] for p, c in stats["provinces"].items()],
    }

    year_table = {
        "type": "table",
        "columns": ["Year", "Count"],
        "rows": [[y, c] for y, c in stats["image_years"].items()],
    }

    area = stats["area_stats_sq_meters"]
    area_table = {
        "type": "table",
        "columns": ["Metric", "Value (m²)"],
        "rows": [
            ["Mean", area["mean"]],
            ["Median", area["median"]],
            ["Min", area["min"]],
            ["Max", area["max"]],
            ["Total", area["total"]],
        ],
    }

    lat = stats["latitude_range"]
    lon = stats["longitude_range"]
    geo_table = {
        "type": "table",
        "columns": ["Coordinate", "Min", "Max"],
        "rows": [
            ["Latitude", lat["min"], lat["max"]],
            ["Longitude", lon["min"], lon["max"]],
        ],
    }

    return json.dumps({
        "total_greenhouses": stats["total_greenhouses"],
        "provinces": province_table,
        "image_years": year_table,
        "area_stats": area_table,
        "geographic_coverage": geo_table,
    }, indent=2)


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
        JSON with total count, pagination info, and a table of greenhouse records.
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

    rows = []
    for r in records:
        rows.append([
            r["id"],
            r["province"],
            r["data_source"],
            r["image_year"],
            r["latitude"],
            r["longitude"],
            r["area_sq_meters"],
        ])

    return json.dumps({
        "total": total,
        "offset": off,
        "limit": lim,
        "results": {
            "type": "table",
            "columns": ["ID", "Province", "Data Source", "Image Year", "Latitude", "Longitude", "Area (m²)"],
            "rows": rows,
        },
    }, indent=2)


@mcp.tool()
def get_greenhouse(greenhouse_id: int) -> str:
    record = get_greenhouse_by_id(greenhouse_id)
    if record is None:
        return json.dumps({"error": f"Greenhouse with ID {greenhouse_id} not found"})

    geojson = record.pop("geometry_geojson", None)

    detail_rows = [
        ["ID", record["id"]],
        ["Province", record["province"]],
        ["Data Source", record["data_source"]],
        ["Image Year", record["image_year"]],
        ["Latitude", record["latitude"]],
        ["Longitude", record["longitude"]],
        ["PRUID", record["pruid"]],
        ["Area (m²)", record["area_sq_meters"]],
    ]
    if record.get("perimeter_meters") is not None:
        detail_rows.append(["Perimeter (m)", record["perimeter_meters"]])

    output = {
        "details": {
            "type": "table",
            "columns": ["Field", "Value"],
            "rows": detail_rows,
        },
    }
    if geojson:
        output["geometry_geojson"] = geojson

    return json.dumps(output, indent=2, default=str)


@mcp.tool()
def get_provinces() -> str:
    summary = get_province_summary()

    rows = []
    for item in summary:
        years = ", ".join(str(y) for y in item["image_years"])
        rows.append([
            item["province"],
            item["greenhouse_count"],
            item["total_area_sq_meters"],
            item["avg_area_sq_meters"],
            years,
        ])

    return json.dumps({
        "type": "table",
        "columns": ["Province", "Count", "Total Area (m²)", "Avg Area (m²)", "Image Years"],
        "rows": rows,
    }, indent=2)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
