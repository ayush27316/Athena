"""Allow running with: python -m mcp_server"""
from mcp_server.server import mcp

mcp.run(transport="streamable-http")
