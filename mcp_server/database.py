from pathlib import Path

import geopandas as gpd
import pandas as pd

SHAPEFILE_PATH = Path(__file__).resolve().parent.parent / "ODG_V1" / "odg_v1.shp"

PROVINCE_LOOKUP = {
    24: "Quebec",
    35: "Ontario",
    47: "Saskatchewan",
    48: "Alberta",
    59: "British Columbia",
}

_gdf: gpd.GeoDataFrame | None = None


def load_data() -> gpd.GeoDataFrame:
    """Load the shapefile into a GeoDataFrame. Caches the result."""
    global _gdf
    if _gdf is not None:
        return _gdf

    if not SHAPEFILE_PATH.exists():
        raise FileNotFoundError(
            f"Shapefile not found at {SHAPEFILE_PATH}. "
            "Ensure the ODG_V1 folder is present in the project root."
        )

    gdf = gpd.read_file(SHAPEFILE_PATH)

    # Reproject to WGS84 (EPSG:4326) so coordinates are in lat/lon degrees
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    _gdf = gdf
    return _gdf


def get_schema() -> dict:
    """Return the database schema (column names, types, sample values)."""
    gdf = load_data()
    schema = {}
    for col in gdf.columns:
        if col == "geometry":
            schema[col] = {"type": "geometry (polygon)", "description": "Greenhouse polygon boundary"}
        else:
            dtype = str(gdf[col].dtype)
            sample = gdf[col].dropna().head(3).tolist()
            schema[col] = {"type": dtype, "sample_values": sample}
    return schema


def get_summary_stats() -> dict:
    """Return aggregate statistics about the greenhouse dataset."""
    gdf = load_data()

    # Calculate area in square meters using a projected CRS
    gdf_proj = gdf.to_crs(epsg=3347)  # StatCan Lambert
    areas = gdf_proj.geometry.area

    province_counts = gdf["PROV_TERR"].value_counts().to_dict()
    image_year_counts = gdf["ImageDate"].value_counts().sort_index().to_dict()

    return {
        "total_greenhouses": len(gdf),
        "provinces": province_counts,
        "image_years": {str(k): v for k, v in image_year_counts.items()},
        "area_stats_sq_meters": {
            "mean": round(float(areas.mean()), 2),
            "median": round(float(areas.median()), 2),
            "min": round(float(areas.min()), 2),
            "max": round(float(areas.max()), 2),
            "total": round(float(areas.sum()), 2),
        },
        "latitude_range": {
            "min": round(float(gdf["Latitude"].min()), 4),
            "max": round(float(gdf["Latitude"].max()), 4),
        },
        "longitude_range": {
            "min": round(float(gdf["Longitude"].min()), 4),
            "max": round(float(gdf["Longitude"].max()), 4),
        },
    }


def query_greenhouses(
    province: str | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    image_year: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    Query greenhouses with optional filters.

    Args:
        province: Filter by province/territory name (e.g. "Ontario", "Quebec")
        min_area: Minimum area in square meters
        max_area: Maximum area in square meters
        image_year: Filter by satellite image year
        limit: Max records to return (default 50, max 500)
        offset: Number of records to skip for pagination
    """
    gdf = load_data()
    result = gdf.copy()

    # Calculate area for filtering
    gdf_proj = result.to_crs(epsg=3347)
    result["area_sq_m"] = gdf_proj.geometry.area

    if province:
        result = result[result["PROV_TERR"].str.contains(province, case=False, na=False)]

    if min_area is not None:
        result = result[result["area_sq_m"] >= min_area]

    if max_area is not None:
        result = result[result["area_sq_m"] <= max_area]

    if image_year is not None:
        result = result[result["ImageDate"] == image_year]

    total = len(result)

    # Apply pagination
    limit = min(limit, 500)
    result = result.iloc[offset : offset + limit]

    # Convert to list of dicts (without geometry for JSON serialization)
    records = []
    for _, row in result.iterrows():
        record = {
            "id": int(row.name),
            "data_source": str(row.get("DataSource", "")),
            "image_year": int(row["ImageDate"]) if pd.notna(row.get("ImageDate")) else None,
            "latitude": round(float(row["Latitude"]), 6) if pd.notna(row.get("Latitude")) else None,
            "longitude": round(float(row["Longitude"]), 6) if pd.notna(row.get("Longitude")) else None,
            "province": str(row.get("PROV_TERR", "")),
            "pruid": int(row["PRUID"]) if pd.notna(row.get("PRUID")) else None,
            "area_sq_meters": round(float(row["area_sq_m"]), 2),
            "perimeter_meters": round(float(row["Shape_Leng"]), 2) if pd.notna(row.get("Shape_Leng")) else None,
        }
        records.append(record)

    return {"total": total, "offset": offset, "limit": limit, "records": records}


def get_greenhouse_by_id(greenhouse_id: int) -> dict | None:
    """Get a single greenhouse record by its index ID, including geometry as GeoJSON."""
    gdf = load_data()
    if greenhouse_id < 0 or greenhouse_id >= len(gdf):
        return None

    row = gdf.iloc[greenhouse_id]

    # Calculate area
    gdf_proj = gdf.iloc[[greenhouse_id]].to_crs(epsg=3347)
    area = float(gdf_proj.geometry.area.iloc[0])

    # Get geometry as GeoJSON
    geojson = row.geometry.__geo_interface__

    return {
        "id": greenhouse_id,
        "data_source": str(row.get("DataSource", "")),
        "image_year": int(row["ImageDate"]) if pd.notna(row.get("ImageDate")) else None,
        "latitude": round(float(row["Latitude"]), 6) if pd.notna(row.get("Latitude")) else None,
        "longitude": round(float(row["Longitude"]), 6) if pd.notna(row.get("Longitude")) else None,
        "province": str(row.get("PROV_TERR", "")),
        "pruid": int(row["PRUID"]) if pd.notna(row.get("PRUID")) else None,
        "area_sq_meters": round(area, 2),
        "perimeter_meters": round(float(row["Shape_Leng"]), 2) if pd.notna(row.get("Shape_Leng")) else None,
        "geometry_geojson": geojson,
    }


def get_province_summary() -> list[dict]:
    """Get a breakdown of greenhouse counts and total area by province."""
    gdf = load_data()
    gdf_proj = gdf.to_crs(epsg=3347)
    gdf = gdf.copy()
    gdf["area_sq_m"] = gdf_proj.geometry.area

    summary = []
    for province in sorted(gdf["PROV_TERR"].dropna().unique()):
        subset = gdf[gdf["PROV_TERR"] == province]
        summary.append({
            "province": province,
            "greenhouse_count": len(subset),
            "total_area_sq_meters": round(float(subset["area_sq_m"].sum()), 2),
            "avg_area_sq_meters": round(float(subset["area_sq_m"].mean()), 2),
            "image_years": sorted(subset["ImageDate"].dropna().unique().astype(int).tolist()),
        })

    return summary
