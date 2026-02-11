# StatCan Greenhouse Database — MCP Server

An MCP (Model Context Protocol) server that exposes Statistics Canada's **Open Database of Greenhouses (ODG v1)** over JSON-RPC via Streamable HTTP transport. Compatible with **ChatGPT web app** connectors.

## Data Source

[Statistics Canada — Open Database of Greenhouses](https://www.statcan.gc.ca/en/lode/databases)

The database contains **2,476 greenhouse polygon records** across Canadian provinces identified from satellite imagery:

| Province | Count | Image Years |
|---|---|---|
| Ontario | 1,324 | 2018, 2020 |
| British Columbia | 901 | 2017, 2020, 2021 |
| Quebec | 195 | 2020 |
| Alberta | 56 | 2021 |

## Setup

```bash
# Create virtual environment
python3 -m venv mcp_server/.venv
source mcp_server/.venv/bin/activate

# Install dependencies
pip install -r mcp_server/requirements.txt
```

## Run the Server

```bash
# From the project root
source mcp_server/.venv/bin/activate
python -m mcp_server

# Custom host/port (defaults: 0.0.0.0:8080)
HOST=0.0.0.0 PORT=8080 python -m mcp_server
```

The server starts at `http://localhost:8080/mcp` using the Streamable HTTP transport.

## Run Tests

```bash
source mcp_server/.venv/bin/activate
python -m pytest mcp_server/tests/ -v
```

## Connect to ChatGPT

1. **Start the server** locally (see above)

2. **Expose to the internet** using ngrok:
   ```bash
   ngrok http 8080
   ```
   This gives you a public URL like `https://abc123.ngrok-free.app`

3. **Add as connector in ChatGPT**:
   - Go to **Settings → Connectors → Create**
   - Name: `StatCan Greenhouses`
   - Server URL: `https://abc123.ngrok-free.app/mcp`
   - Check "I trust this provider"

4. **Use in chat**: Enable the connector in the composer and ask questions like:
   - "How many greenhouses are in Ontario?"
   - "Show me the largest greenhouses in British Columbia"
   - "What's the total greenhouse area by province?"

## Available MCP Tools

| Tool | Description |
|---|---|
| `get_database_schema` | Returns column names, types, and sample values |
| `get_statistics` | Aggregate stats: counts by province/year, area statistics, coordinate ranges |
| `search_greenhouses` | Query with filters: province, min/max area, image year, pagination |
| `get_greenhouse` | Get a single greenhouse by ID including GeoJSON geometry |
| `get_provinces` | Province-level summary: counts, total/avg area, image years |

## Architecture

```
mcp_server/
├── server.py          # MCP server with 5 tools, Streamable HTTP transport
├── database.py        # Shapefile loading (geopandas) and query functions
├── __main__.py        # Entry point for python -m mcp_server
├── requirements.txt   # Python dependencies
└── tests/
    ├── test_database.py     # 25 tests for the data layer
    └── test_mcp_server.py   # 14 tests for MCP tool registration & responses
```

## Protocol

- **Transport**: Streamable HTTP (MCP spec 2025-03-26)
- **Endpoint**: `POST /mcp` (JSON-RPC 2.0)
- **Session**: Server assigns `Mcp-Session-Id` header on initialize
