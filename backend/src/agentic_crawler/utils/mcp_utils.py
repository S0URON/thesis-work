"""MCP utilities for working with Firecrawl tools."""

from typing import List, Any
from mcp import ClientSession
from langchain_mcp_adapters.tools import load_mcp_tools


async def load_firecrawl_tools(session: ClientSession) -> List[Any]:
    """
    Load Firecrawl MCP tools from session.

    Args:
        session: Active MCP client session

    Returns:
        List of loaded tools
    """
    return await load_mcp_tools(session)


def extract_tool_names(tools: List[Any]) -> List[str]:
    """
    Extract tool names from tool list.

    Args:
        tools: List of tools

    Returns:
        List of tool names
    """
    return [tool.name for tool in tools]


def find_tool_by_name(tools: List[Any], name: str) -> Any:
    """
    Find tool by name.

    Args:
        tools: List of tools
        name: Tool name to find

    Returns:
        Tool if found, None otherwise
    """
    for tool in tools:
        if tool.name == name:
            return tool
    return None
