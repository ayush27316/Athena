import json
import os
from typing import Any, Dict, List, Optional

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from mcp_server.database import (
    get_greenhouse_by_id,
    get_province_summary,
    get_schema,
    get_summary_stats,
    query_greenhouses,
)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

MIME_TYPE_HTML = "text/html+skybridge"

TEMPLATE_GREENHOUSE_DETAIL = "ui://widget/greenhouse-detail-map.html"
TEMPLATE_GREENHOUSE_SEARCH = "ui://widget/greenhouse-search-map.html"
TEMPLATE_STATISTICS_DASHBOARD = "ui://widget/greenhouse-statistics-dashboard.html"
TEMPLATE_PROVINCES_SUMMARY = "ui://widget/greenhouse-provinces-summary.html"
TEMPLATE_SCHEMA_TABLE = "ui://widget/greenhouse-schema-table.html"


def _split_env_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _transport_security_settings() -> TransportSecuritySettings:
    """
    Configure basic transport security for Skybridge / Apps clients.
    """
    allowed_hosts = _split_env_list(os.getenv("MCP_ALLOWED_HOSTS"))
    allowed_origins = _split_env_list(os.getenv("MCP_ALLOWED_ORIGINS"))
    if not allowed_hosts and not allowed_origins:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


def _tool_meta(template_uri: str, invoking: str, invoked: str) -> Dict[str, Any]:
    return {
        "openai/outputTemplate": template_uri,
        "openai/toolInvocation/invoking": invoking,
        "openai/toolInvocation/invoked": invoked,
        "openai/widgetAccessible": True,
    }


mcp = FastMCP(
    "StatCan Greenhouse Database",
    instructions=(
        "This MCP server provides access to Statistics Canada's Open Database "
        "of Greenhouses (ODG v1). The database contains 2,476 greenhouse polygon "
        "records across Canadian provinces (Ontario, Quebec, British Columbia, Alberta) "
        "identified from satellite imagery. You can query greenhouses by province, "
        "area, image year, or get aggregate statistics. "
        "Tool responses use a structured table format with type, columns, and rows — "
        "render them as tables for the user. "
        "Several tools also expose interactive map and chart widgets via Skybridge "
        "output templates, but the plain JSON text content remains fully usable in "
        "non-Apps MCP clients."
    ),
    host=HOST,
    port=PORT,
    stateless_http=True,
    transport_security=_transport_security_settings(),
)


@mcp.resource(
    TEMPLATE_GREENHOUSE_DETAIL,
    title="Greenhouse detail map",
    mime_type=MIME_TYPE_HTML,
)
async def greenhouse_detail_template() -> str:
    # Leaflet map focused on a single greenhouse geometry with a details panel.
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Greenhouse Detail</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""
    />
    <style>
      html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #111827;
        background: #f3f4f6;
      }
      .layout {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      @media (min-width: 768px) {
        .layout {
          flex-direction: row;
        }
      }
      #map {
        flex: 2;
        min-height: 260px;
      }
      .sidebar {
        flex: 1;
        padding: 1rem;
        background: #ffffff;
        border-left: 1px solid #e5e7eb;
        overflow-y: auto;
      }
      .sidebar h1 {
        font-size: 1.1rem;
        margin: 0 0 0.5rem 0;
      }
      .sidebar table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
      }
      .sidebar th,
      .sidebar td {
        padding: 0.25rem 0.35rem;
        border-bottom: 1px solid #e5e7eb;
        text-align: left;
      }
      .sidebar th {
        font-weight: 600;
        width: 40%;
        color: #374151;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.15rem 0.45rem;
        border-radius: 999px;
        font-size: 0.7rem;
        background: #e0f2fe;
        color: #0369a1;
        font-weight: 500;
      }
    </style>
  </head>
  <body>
    <div class="layout">
      <div id="map"></div>
      <aside class="sidebar">
        <h1>
          Greenhouse
          <span id="gh-id" class="badge"></span>
        </h1>
        <div id="province-pill" class="badge" style="margin-bottom: 0.5rem;"></div>
        <table id="details-table"></table>
      </aside>
    </div>

    <script
      src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
      integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
      crossorigin=""
    ></script>
    <script>
      function getStructuredContent() {
        try {
          if (window.openai && window.openai.toolOutput) {
            return window.openai.toolOutput.structuredContent || null;
          }
        } catch (e) {
          console.error("Unable to read toolOutput from window.openai", e);
        }
        return null;
      }

      function renderDetails(data) {
        const idEl = document.getElementById("gh-id");
        const provEl = document.getElementById("province-pill");
        const table = document.getElementById("details-table");
        if (!data || !data.details) return;

        const rows = data.details.rows || [];
        const mapByField = {};
        rows.forEach(([field, value]) => {
          mapByField[field] = value;
        });

        if (idEl && mapByField["ID"] != null) {
          idEl.textContent = "#" + mapByField["ID"];
        }
        if (provEl && mapByField["Province"]) {
          provEl.textContent = mapByField["Province"];
        }

        table.innerHTML = "";
        rows.forEach(([field, value]) => {
          const tr = document.createElement("tr");
          const th = document.createElement("th");
          const td = document.createElement("td");
          th.textContent = field;
          td.textContent = value;
          tr.appendChild(th);
          tr.appendChild(td);
          table.appendChild(tr);
        });
      }

      function renderMap(data) {
        const map = L.map("map");
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        }).addTo(map);

        let fitDone = false;

        if (data && data.geometry_geojson) {
          const layer = L.geoJSON(data.geometry_geojson, {
            style: {
              color: "#2563eb",
              weight: 2,
              fillColor: "#60a5fa",
              fillOpacity: 0.3,
            },
          }).addTo(map);
          try {
            const bounds = layer.getBounds();
            if (bounds.isValid()) {
              map.fitBounds(bounds.pad(0.4));
              fitDone = true;
            }
          } catch (e) {
            console.warn("Unable to fit bounds for greenhouse geometry", e);
          }
        }

        const latRow = (data.details?.rows || []).find(
          (r) => r[0] === "Latitude"
        );
        const lonRow = (data.details?.rows || []).find(
          (r) => r[0] === "Longitude"
        );
        const lat = latRow ? Number(latRow[1]) : null;
        const lon = lonRow ? Number(lonRow[1]) : null;

        if (!fitDone && lat && lon) {
          map.setView([lat, lon], 14);
          L.marker([lat, lon]).addTo(map);
        } else if (!fitDone) {
          map.setView([56.1304, -106.3468], 4); // Canada fallback
        }
      }

      document.addEventListener("DOMContentLoaded", function () {
        const data = getStructuredContent();
        if (!data) {
          console.warn("No structuredContent found for greenhouse detail.");
          return;
        }
        renderDetails(data);
        renderMap(data);
      });
    </script>
  </body>
</html>
    """.strip()


@mcp.resource(
    TEMPLATE_GREENHOUSE_SEARCH,
    title="Greenhouse search map and table",
    mime_type=MIME_TYPE_HTML,
)
async def greenhouse_search_template() -> str:
    # Leaflet map with filterable greenhouse search results.
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Greenhouse Search</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""
    />
    <style>
      html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #111827;
        background: #f3f4f6;
      }
      .layout {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      #map {
        height: 260px;
      }
      @media (min-width: 768px) {
        #map {
          height: 320px;
        }
      }
      .controls {
        padding: 0.75rem 1rem;
        background: #ffffff;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.75rem;
        border-bottom: 1px solid #e5e7eb;
      }
      .controls label {
        display: flex;
        flex-direction: column;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
        gap: 0.15rem;
      }
      .controls input,
      .controls select {
        border-radius: 0.375rem;
        border: 1px solid #d1d5db;
        padding: 0.25rem 0.5rem;
        font-size: 0.85rem;
      }
      .controls button {
        align-self: end;
        padding: 0.4rem 0.8rem;
        border-radius: 999px;
        border: none;
        background: #2563eb;
        color: white;
        font-size: 0.8rem;
        font-weight: 500;
        cursor: pointer;
      }
      .controls button:disabled {
        opacity: 0.5;
        cursor: default;
      }
      .table-wrapper {
        flex: 1;
        overflow: auto;
        background: #ffffff;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
      }
      thead {
        position: sticky;
        top: 0;
        background: #f9fafb;
        z-index: 1;
      }
      th, td {
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid #e5e7eb;
        text-align: left;
      }
      th {
        font-weight: 600;
        color: #374151;
        font-size: 0.75rem;
      }
      tbody tr:hover {
        background: #f3f4f6;
      }
      .pill {
        display: inline-flex;
        padding: 0.1rem 0.45rem;
        border-radius: 999px;
        background: #eff6ff;
        color: #1d4ed8;
        font-size: 0.7rem;
      }
      .summary {
        padding: 0.4rem 1rem;
        font-size: 0.78rem;
        color: #4b5563;
        background: #f9fafb;
        border-top: 1px solid #e5e7eb;
      }
    </style>
  </head>
  <body>
    <div class="layout">
      <div id="map"></div>
      <section class="controls">
        <label>
          Province
          <input id="filter-province" placeholder="Ontario, Quebec, ..." />
        </label>
        <label>
          Min area (m²)
          <input id="filter-min-area" type="number" min="0" step="1" />
        </label>
        <label>
          Max area (m²)
          <input id="filter-max-area" type="number" min="0" step="1" />
        </label>
        <label>
          Image year
          <input id="filter-year" type="number" min="1900" max="2100" step="1" />
        </label>
        <button id="apply-filters">Apply filters</button>
      </section>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr id="results-header-row"></tr>
          </thead>
          <tbody id="results-body"></tbody>
        </table>
      </div>
      <div class="summary" id="results-summary"></div>
    </div>

    <script
      src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
      integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
      crossorigin=""
    ></script>
    <script>
      let map;
      let markersLayer;

      function getStructuredContent() {
        try {
          if (window.openai && window.openai.toolOutput) {
            return window.openai.toolOutput.structuredContent || null;
          }
        } catch (e) {
          console.error("Unable to read toolOutput from window.openai", e);
        }
        return null;
      }

      function ensureMap() {
        if (map) return map;
        map = L.map("map");
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 18,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        }).addTo(map);
        map.setView([56.1304, -106.3468], 4);
        markersLayer = L.layerGroup().addTo(map);
        return map;
      }

      function renderTable(data) {
        const headerRow = document.getElementById("results-header-row");
        const body = document.getElementById("results-body");
        const summary = document.getElementById("results-summary");

        headerRow.innerHTML = "";
        body.innerHTML = "";

        if (!data || !data.results) {
          summary.textContent = "No data available.";
          return;
        }

        const table = data.results;
        const cols = table.columns || [];
        const rows = table.rows || [];

        cols.forEach((col) => {
          const th = document.createElement("th");
          th.textContent = col;
          headerRow.appendChild(th);
        });

        rows.forEach((row) => {
          const tr = document.createElement("tr");
          row.forEach((value, idx) => {
            const td = document.createElement("td");
            if (cols[idx] === "Province" && value) {
              const span = document.createElement("span");
              span.className = "pill";
              span.textContent = value;
              td.appendChild(span);
            } else {
              td.textContent = value;
            }
            tr.appendChild(td);
          });
          body.appendChild(tr);
        });

        summary.textContent = `Showing ${rows.length.toLocaleString()} of ${String(
          data.total || 0
        )} matching greenhouses (offset ${data.offset || 0}).`;
      }

      function renderMap(data) {
        const m = ensureMap();
        markersLayer.clearLayers();

        if (!data || !data.results) return;
        const rows = data.results.rows || [];

        const bounds = [];
        rows.forEach((row) => {
          const lat = Number(row[4]);
          const lon = Number(row[5]);
          if (!isFinite(lat) || !isFinite(lon)) return;
          const id = row[0];
          const province = row[1];
          const year = row[3];
          const area = row[6];
          const marker = L.circleMarker([lat, lon], {
            radius: 6,
            color: "#2563eb",
            fillColor: "#60a5fa",
            fillOpacity: 0.8,
          });
          marker.bindPopup(
            `<strong>Greenhouse #${id}</strong><br/>` +
              `${province || "Unknown province"}<br/>` +
              `Year: ${year || "n/a"}<br/>Area: ${area?.toLocaleString?.() || area} m²`
          );
          marker.addTo(markersLayer);
          bounds.push([lat, lon]);
        });

        if (bounds.length) {
          try {
            m.fitBounds(bounds, { padding: [20, 20] });
          } catch (e) {
            console.warn("Unable to fit bounds for search results", e);
          }
        }
      }

      async function applyFilters() {
        const btn = document.getElementById("apply-filters");
        if (!window.openai || !window.openai.callTool) {
          console.warn("window.openai.callTool is not available in this host.");
          return;
        }

        const province = document.getElementById("filter-province").value || null;
        const minAreaRaw = document.getElementById("filter-min-area").value;
        const maxAreaRaw = document.getElementById("filter-max-area").value;
        const yearRaw = document.getElementById("filter-year").value;

        const args = {};
        if (province) args.province = province;
        if (minAreaRaw) args.min_area_sq_meters = Number(minAreaRaw);
        if (maxAreaRaw) args.max_area_sq_meters = Number(maxAreaRaw);
        if (yearRaw) args.image_year = Number(yearRaw);

        btn.disabled = true;
        btn.textContent = "Filtering...";

        try {
          const result = await window.openai.callTool({
            name: "search_greenhouses",
            arguments: args,
          });
          const data = result.structuredContent || null;
          renderTable(data);
          renderMap(data);
        } catch (e) {
          console.error("Error calling search_greenhouses from widget", e);
        } finally {
          btn.disabled = false;
          btn.textContent = "Apply filters";
        }
      }

      document.addEventListener("DOMContentLoaded", function () {
        const data = getStructuredContent();
        if (data) {
          renderTable(data);
          renderMap(data);
        }
        const btn = document.getElementById("apply-filters");
        btn.addEventListener("click", function (evt) {
          evt.preventDefault();
          applyFilters();
        });
      });
    </script>
  </body>
</html>
    """.strip()


@mcp.resource(
    TEMPLATE_STATISTICS_DASHBOARD,
    title="Greenhouse statistics dashboard",
    mime_type=MIME_TYPE_HTML,
)
async def greenhouse_statistics_template() -> str:
    # Simple dashboard using Chart.js to visualize aggregate statistics.
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Greenhouse Statistics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f3f4f6;
        color: #111827;
      }
      .wrapper {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 1rem;
      }
      .cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 0.75rem;
      }
      .card {
        background: #ffffff;
        border-radius: 0.75rem;
        padding: 0.75rem 0.9rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
      }
      .card h2 {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #6b7280;
        margin: 0 0 0.2rem 0;
      }
      .card .value {
        font-size: 1.2rem;
        font-weight: 600;
      }
      .grid {
        display: grid;
        grid-template-columns: minmax(0, 1.5fr) minmax(0, 1.5fr);
        gap: 1rem;
      }
      @media (max-width: 768px) {
        .grid {
          grid-template-columns: minmax(0, 1fr);
        }
      }
      .panel {
        background: #ffffff;
        border-radius: 0.75rem;
        padding: 0.75rem 0.9rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
      }
      .panel h3 {
        font-size: 0.9rem;
        margin: 0 0 0.3rem 0;
      }
      canvas {
        max-height: 260px;
      }
    </style>
  </head>
  <body>
    <div class="wrapper">
      <div class="cards">
        <div class="card">
          <h2>Total greenhouses</h2>
          <div id="total-greenhouses" class="value">–</div>
        </div>
        <div class="card">
          <h2>Total area (m²)</h2>
          <div id="area-total" class="value">–</div>
        </div>
        <div class="card">
          <h2>Mean area (m²)</h2>
          <div id="area-mean" class="value">–</div>
        </div>
        <div class="card">
          <h2>Median area (m²)</h2>
          <div id="area-median" class="value">–</div>
        </div>
      </div>

      <div class="grid">
        <div class="panel">
          <h3>Greenhouses by province</h3>
          <canvas id="province-chart"></canvas>
        </div>
        <div class="panel">
          <h3>Greenhouses by image year</h3>
          <canvas id="year-chart"></canvas>
        </div>
      </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
    <script>
      function getStructuredContent() {
        try {
          if (window.openai && window.openai.toolOutput) {
            return window.openai.toolOutput.structuredContent || null;
          }
        } catch (e) {
          console.error("Unable to read toolOutput from window.openai", e);
        }
        return null;
      }

      function formatNumber(value) {
        if (value == null) return "–";
        try {
          return Number(value).toLocaleString();
        } catch {
          return String(value);
        }
      }

      function renderCards(data) {
        document.getElementById("total-greenhouses").textContent = formatNumber(
          data.total_greenhouses
        );

        const areaTable = data.area_stats;
        if (!areaTable || !Array.isArray(areaTable.rows)) return;
        const map = {};
        areaTable.rows.forEach(([metric, value]) => {
          map[metric] = value;
        });

        document.getElementById("area-total").textContent = formatNumber(
          map["Total"]
        );
        document.getElementById("area-mean").textContent = formatNumber(
          map["Mean"]
        );
        document.getElementById("area-median").textContent = formatNumber(
          map["Median"]
        );
      }

      function renderProvinceChart(data) {
        const table = data.provinces;
        if (!table || !Array.isArray(table.rows)) return;
        const labels = table.rows.map((r) => r[0]);
        const counts = table.rows.map((r) => r[1]);
        const ctx = document.getElementById("province-chart").getContext("2d");
        new Chart(ctx, {
          type: "bar",
          data: {
            labels,
            datasets: [
              {
                label: "Greenhouses",
                data: counts,
                backgroundColor: "#60a5fa",
                borderRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
            },
            scales: {
              x: { ticks: { font: { size: 10 } } },
              y: {
                beginAtZero: true,
                ticks: { precision: 0, font: { size: 10 } },
              },
            },
          },
        });
      }

      function renderYearChart(data) {
        const table = data.image_years;
        if (!table || !Array.isArray(table.rows)) return;
        const labels = table.rows.map((r) => r[0]);
        const counts = table.rows.map((r) => r[1]);
        const ctx = document.getElementById("year-chart").getContext("2d");
        new Chart(ctx, {
          type: "bar",
          data: {
            labels,
            datasets: [
              {
                label: "Greenhouses",
                data: counts,
                backgroundColor: "#34d399",
                borderRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
            },
            scales: {
              x: { ticks: { font: { size: 10 } } },
              y: {
                beginAtZero: true,
                ticks: { precision: 0, font: { size: 10 } },
              },
            },
          },
        });
      }

      document.addEventListener("DOMContentLoaded", function () {
        const data = getStructuredContent();
        if (!data) {
          console.warn("No structuredContent found for statistics dashboard.");
          return;
        }
        renderCards(data);
        renderProvinceChart(data);
        renderYearChart(data);
      });
    </script>
  </body>
</html>
    """.strip()


@mcp.resource(
    TEMPLATE_PROVINCES_SUMMARY,
    title="Greenhouse provinces summary",
    mime_type=MIME_TYPE_HTML,
)
async def greenhouse_provinces_template() -> str:
    # Compact table of provinces with counts and area.
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Greenhouse Provinces</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f3f4f6;
        color: #111827;
      }
      .wrapper {
        padding: 0.75rem 1rem;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
        background: #ffffff;
        border-radius: 0.75rem;
        overflow: hidden;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
      }
      thead {
        background: #f9fafb;
      }
      th, td {
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #e5e7eb;
        text-align: left;
      }
      th {
        font-size: 0.75rem;
        font-weight: 600;
        color: #374151;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      tbody tr:last-child td {
        border-bottom: none;
      }
      tbody tr:hover {
        background: #f3f4f6;
      }
      .pill {
        display: inline-flex;
        padding: 0.1rem 0.45rem;
        border-radius: 999px;
        background: #eff6ff;
        color: #1d4ed8;
        font-size: 0.7rem;
      }
    </style>
  </head>
  <body>
    <div class="wrapper">
      <table>
        <thead>
          <tr>
            <th>Province</th>
            <th>Greenhouses</th>
            <th>Total area (m²)</th>
            <th>Avg area (m²)</th>
            <th>Image years</th>
          </tr>
        </thead>
        <tbody id="provinces-body"></tbody>
      </table>
    </div>

    <script>
      function getStructuredContent() {
        try {
          if (window.openai && window.openai.toolOutput) {
            return window.openai.toolOutput.structuredContent || null;
          }
        } catch (e) {
          console.error("Unable to read toolOutput from window.openai", e);
        }
        return null;
      }

      function renderTable(table) {
        const body = document.getElementById("provinces-body");
        body.innerHTML = "";
        if (!table || !Array.isArray(table.rows)) return;

        table.rows.forEach((row) => {
          const tr = document.createElement("tr");
          const [province, count, totalArea, avgArea, years] = row;

          const tdProvince = document.createElement("td");
          const span = document.createElement("span");
          span.className = "pill";
          span.textContent = province;
          tdProvince.appendChild(span);
          tr.appendChild(tdProvince);

          const tdCount = document.createElement("td");
          tdCount.textContent = count.toLocaleString
            ? count.toLocaleString()
            : count;
          tr.appendChild(tdCount);

          const tdTotal = document.createElement("td");
          tdTotal.textContent = totalArea.toLocaleString
            ? totalArea.toLocaleString()
            : totalArea;
          tr.appendChild(tdTotal);

          const tdAvg = document.createElement("td");
          tdAvg.textContent = avgArea.toLocaleString
            ? avgArea.toLocaleString()
            : avgArea;
          tr.appendChild(tdAvg);

          const tdYears = document.createElement("td");
          tdYears.textContent = years;
          tr.appendChild(tdYears);

          body.appendChild(tr);
        });
      }

      document.addEventListener("DOMContentLoaded", function () {
        const data = getStructuredContent();
        if (!data) return;
        renderTable(data);
      });
    </script>
  </body>
</html>
    """.strip()


@mcp.resource(
    TEMPLATE_SCHEMA_TABLE,
    title="Greenhouse database schema",
    mime_type=MIME_TYPE_HTML,
)
async def greenhouse_schema_template() -> str:
    # Simple tabular view of the database schema including sample values.
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Greenhouse Schema</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f3f4f6;
        color: #111827;
      }
      .wrapper {
        padding: 0.75rem 1rem;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
        background: #ffffff;
        border-radius: 0.75rem;
        overflow: hidden;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
      }
      thead {
        background: #f9fafb;
      }
      th, td {
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #e5e7eb;
        text-align: left;
      }
      th {
        font-size: 0.75rem;
        font-weight: 600;
        color: #374151;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      tbody tr:last-child td {
        border-bottom: none;
      }
      tbody tr:hover {
        background: #f3f4f6;
      }
      code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
          "Courier New", monospace;
        font-size: 0.75rem;
      }
    </style>
  </head>
  <body>
    <div class="wrapper">
      <table>
        <thead>
          <tr>
            <th>Column</th>
            <th>Type</th>
            <th>Sample values</th>
          </tr>
        </thead>
        <tbody id="schema-body"></tbody>
      </table>
    </div>

    <script>
      function getStructuredContent() {
        try {
          if (window.openai && window.openai.toolOutput) {
            return window.openai.toolOutput.structuredContent || null;
          }
        } catch (e) {
          console.error("Unable to read toolOutput from window.openai", e);
        }
        return null;
      }

      function renderSchema(table) {
        const body = document.getElementById("schema-body");
        body.innerHTML = "";
        if (!table || !Array.isArray(table.rows)) return;

        table.rows.forEach((row) => {
          const [name, type, sample] = row;
          const tr = document.createElement("tr");

          const tdName = document.createElement("td");
          tdName.textContent = name;
          tr.appendChild(tdName);

          const tdType = document.createElement("td");
          tdType.textContent = type;
          tr.appendChild(tdType);

          const tdSample = document.createElement("td");
          const code = document.createElement("code");
          code.textContent = Array.isArray(sample)
            ? JSON.stringify(sample)
            : String(sample ?? "");
          tdSample.appendChild(code);
          tr.appendChild(tdSample);

          body.appendChild(tr);
        });
      }

      document.addEventListener("DOMContentLoaded", function () {
        const data = getStructuredContent();
        if (!data) return;
        renderSchema(data);
      });
    </script>
  </body>
</html>
    """.strip()


@mcp.tool()
async def get_database_schema() -> types.CallToolResult:
    """
    Schema for all columns: name, type, and sample values.
    """
    schema = get_schema()

    rows: List[List[Any]] = []
    for col, info in schema.items():
        col_type = info.get("type", "")
        samples = info.get("sample_values", [])
        rows.append([col, col_type, samples])

    table = {
        "type": "table",
        "columns": ["Column", "Type", "Sample Values"],
        "rows": rows,
    }
    json_data: Dict[str, Any] = table
    json_text = json.dumps(json_data, indent=2, default=str)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json_text)],
        structuredContent=json_data,
        _meta=_tool_meta(
            TEMPLATE_SCHEMA_TABLE,
            "Loading greenhouse database schema",
            "Schema table rendered",
        ),
        isError=False,
    )


@mcp.tool()
async def get_statistics() -> types.CallToolResult:
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

    json_data: Dict[str, Any] = {
        "total_greenhouses": stats["total_greenhouses"],
        "provinces": province_table,
        "image_years": year_table,
        "area_stats": area_table,
        "geographic_coverage": geo_table,
    }
    json_text = json.dumps(json_data, indent=2, default=str)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json_text)],
        structuredContent=json_data,
        _meta=_tool_meta(
            TEMPLATE_STATISTICS_DASHBOARD,
            "Loading greenhouse statistics",
            "Statistics dashboard rendered",
        ),
        isError=False,
    )


@mcp.tool()
async def search_greenhouses(
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

    rows: List[List[Any]] = []
    for r in records:
        rows.append(
            [
                r["id"],
                r["province"],
                r["data_source"],
                r["image_year"],
                r["latitude"],
                r["longitude"],
                r["area_sq_meters"],
            ]
        )

    json_data: Dict[str, Any] = {
        "total": total,
        "offset": off,
        "limit": lim,
        "results": {
            "type": "table",
            "columns": [
                "ID",
                "Province",
                "Data Source",
                "Image Year",
                "Latitude",
                "Longitude",
                "Area (m²)",
            ],
            "rows": rows,
        },
    }
    json_text = json.dumps(json_data, indent=2, default=str)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json_text)],
        structuredContent=json_data,
        _meta=_tool_meta(
            TEMPLATE_GREENHOUSE_SEARCH,
            "Searching greenhouses",
            "Search map and table rendered",
        ),
        isError=False,
    )


@mcp.tool()
async def get_greenhouse(greenhouse_id: int) -> types.CallToolResult:
    record = get_greenhouse_by_id(greenhouse_id)
    if record is None:
        json_data = {"error": f"Greenhouse with ID {greenhouse_id} not found"}
        json_text = json.dumps(json_data, indent=2, default=str)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json_text)],
            structuredContent=json_data,
            _meta=_tool_meta(
                TEMPLATE_GREENHOUSE_DETAIL,
                "Looking up greenhouse",
                "Greenhouse not found",
            ),
            isError=True,
        )

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

    output: Dict[str, Any] = {
        "details": {
            "type": "table",
            "columns": ["Field", "Value"],
            "rows": detail_rows,
        },
    }
    if geojson:
        output["geometry_geojson"] = geojson

    json_text = json.dumps(output, indent=2, default=str)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json_text)],
        structuredContent=output,
        _meta=_tool_meta(
            TEMPLATE_GREENHOUSE_DETAIL,
            "Loading greenhouse detail",
            "Greenhouse detail map rendered",
        ),
        isError=False,
    )


@mcp.tool()
async def get_provinces() -> types.CallToolResult:
    summary = get_province_summary()

    rows: List[List[Any]] = []
    for item in summary:
        years = ", ".join(str(y) for y in item["image_years"])
        rows.append(
            [
                item["province"],
                item["greenhouse_count"],
                item["total_area_sq_meters"],
                item["avg_area_sq_meters"],
                years,
            ]
        )

    json_data: Dict[str, Any] = {
        "type": "table",
        "columns": [
            "Province",
            "Count",
            "Total Area (m²)",
            "Avg Area (m²)",
            "Image Years",
        ],
        "rows": rows,
    }
    json_text = json.dumps(json_data, indent=2, default=str)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json_text)],
        structuredContent=json_data,
        _meta=_tool_meta(
            TEMPLATE_PROVINCES_SUMMARY,
            "Loading greenhouse provinces summary",
            "Provinces summary rendered",
        ),
        isError=False,
    )

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
