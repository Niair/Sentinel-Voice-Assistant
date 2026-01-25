"""MCP client and server configuration for tool-calling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_mcp_adapters.client import MultiServerMCPClient

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

SERVERS = {
    "math": {
        "transport": "stdio",
        "command": r"E:\VS_Code\Scripts\uv.exe",
        "args": ["run", "fastmcp", "run", r"E:\_Projects\GAIP\MCP\chat_bot_with_mcp\local_mcp.py"],
        "env": {},
        "cwd": r"E:\_Projects\GAIP\MCP\chat_bot_with_mcp",
    },
    "expense": {
        "transport": "sse",
        "url": "https://nihal-finance-server.fastmcp.app/mcp",
    },
}


class SafeMCPClient:
    """Wrapper around MultiServerMCPClient with safe init and fallback to no tools on error."""

    def __init__(self) -> None:
        self._client: MultiServerMCPClient | None = None
        self._tools: list["BaseTool"] = []

    async def initialize(self) -> None:
        """Initialize MCP client; on failure, keep _tools empty."""
        try:
            self._client = MultiServerMCPClient(connections=SERVERS)
            self._tools = await self._client.get_tools()
        except Exception as e:
            print(f"⚠️ MCP client failed to initialize: {e}")
            self._client = None
            self._tools = []

    def get_tools(self) -> list["BaseTool"]:
        return self._tools
