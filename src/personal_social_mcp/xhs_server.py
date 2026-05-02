"""Xiaohongshu (小红书) MCP Server — rate-limited wrapper around xhs-cli."""

from __future__ import annotations

import os
import subprocess

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from personal_social_mcp._rate_limiter import RateLimiter

_limiter = RateLimiter(max_per_second=1.0, daily_max=500)

_XHS_PATH = os.environ.get(
    "XHS_CLI_PATH",
    os.path.expanduser("~/.local/share/mise/installs/python/3.12.13/bin/xhs"),
)


def _run_xhs(args: list[str]) -> str:
    """Run xhs-cli with the given args and return stdout."""
    env = os.environ.copy()
    shim_dir = os.path.expanduser("~/.local/bin")
    path = env.get("PATH", "")
    if shim_dir not in path:
        env["PATH"] = f"{shim_dir}:{path}"

    result = subprocess.run(
        [_XHS_PATH] + args,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if result.returncode != 0:
        error_msg = result.stderr.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"xhs-cli failed: {error_msg}")
    return result.stdout


server = Server("xiaohongshu")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="search",
            description="Search notes by keyword.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Search keyword"},
                    "sort": {
                        "type": "string",
                        "enum": ["general", "popular", "latest"],
                        "description": "Sort order (default general)",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["all", "video", "image"],
                        "description": "Note type filter (default all)",
                    },
                    "page": {"type": "integer", "description": "Page number (default 1)"},
                },
                "required": ["keyword"],
            },
        ),
        Tool(
            name="feed",
            description="Browse the recommendation feed.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="hot",
            description="Browse hot/trending notes by category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "fashion", "food", "cosmetics", "movie",
                            "career", "love", "home", "gaming", "travel", "fitness",
                        ],
                        "description": "Category filter",
                    },
                },
            },
        ),
        Tool(
            name="read",
            description="Read a note by ID or URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id_or_url": {"type": "string", "description": "Note ID or full URL"},
                    "xsec_token": {
                        "type": "string",
                        "description": "Security token (needed for direct ID access)",
                    },
                },
                "required": ["id_or_url"],
            },
        ),
        Tool(
            name="comments",
            description="View comments on a note by ID, URL, or short index.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id_or_url": {"type": "string", "description": "Note ID, URL, or short index"},
                    "xsec_token": {"type": "string", "description": "Security token"},
                    "all": {
                        "type": "boolean",
                        "description": "Auto-paginate to fetch ALL comments",
                        "default": False,
                    },
                },
                "required": ["id_or_url"],
            },
        ),
        Tool(
            name="user",
            description="View user profile info by user ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="user-posts",
            description="List a user's published notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor from previous response",
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="search-user",
            description="Search for users by keyword.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Search keyword"},
                },
                "required": ["keyword"],
            },
        ),
        Tool(
            name="status",
            description="Check current login status and user info.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="whoami",
            description="Show detailed profile of current user (level, fans, likes).",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    await _limiter.acquire()

    try:
        if name == "search":
            cmd = ["search", arguments["keyword"], "--json"]
            if arguments.get("sort"):
                cmd += ["--sort", arguments["sort"]]
            if arguments.get("type"):
                cmd += ["--type", arguments["type"]]
            if arguments.get("page"):
                cmd += ["--page", str(arguments["page"])]
            output = _run_xhs(cmd)

        elif name == "feed":
            output = _run_xhs(["feed", "--json"])

        elif name == "hot":
            cmd = ["hot", "--json"]
            if arguments.get("category"):
                cmd += ["-c", arguments["category"]]
            output = _run_xhs(cmd)

        elif name == "read":
            cmd = ["read", arguments["id_or_url"], "--json"]
            if arguments.get("xsec_token"):
                cmd += ["--xsec-token", arguments["xsec_token"]]
            output = _run_xhs(cmd)

        elif name == "comments":
            cmd = ["comments", arguments["id_or_url"], "--json"]
            if arguments.get("xsec_token"):
                cmd += ["--xsec-token", arguments["xsec_token"]]
            if arguments.get("all"):
                cmd += ["--all"]
            output = _run_xhs(cmd)

        elif name == "user":
            output = _run_xhs(["user", arguments["user_id"], "--json"])

        elif name == "user-posts":
            cmd = ["user-posts", arguments["user_id"], "--json"]
            if arguments.get("cursor"):
                cmd += ["--cursor", arguments["cursor"]]
            output = _run_xhs(cmd)

        elif name == "search-user":
            output = _run_xhs(["search-user", arguments["keyword"], "--json"])

        elif name == "status":
            output = _run_xhs(["status"])

        elif name == "whoami":
            output = _run_xhs(["whoami", "--json"])

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]

    return [TextContent(type="text", text=output)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
