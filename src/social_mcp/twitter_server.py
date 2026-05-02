"""Twitter/X MCP Server — rate-limited wrapper around twitter-cli."""

from __future__ import annotations

import os
import subprocess

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from social_mcp._rate_limiter import RateLimiter

_limiter = RateLimiter(max_per_second=1.0, daily_max=500)

_TWITTER_PATH = os.environ.get(
    "TWITTER_CLI_PATH",
    os.path.expanduser("~/.local/bin/twitter"),
)


def _run_twitter(args: list[str]) -> str:
    """Run twitter-cli with the given args and return stdout."""
    env = os.environ.copy()
    env["TWITTER_AUTH_TOKEN"] = os.environ.get("TWITTER_AUTH_TOKEN", "")
    env["TWITTER_CT0"] = os.environ.get("TWITTER_CT0", "")

    shim_dir = os.path.expanduser("~/.local/bin")
    path = env.get("PATH", "")
    if shim_dir not in path:
        env["PATH"] = f"{shim_dir}:{path}"

    result = subprocess.run(
        [_TWITTER_PATH, "-c"] + args,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if result.returncode != 0:
        error_msg = result.stderr.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"twitter-cli failed: {error_msg}")
    return result.stdout


server = Server("twitter")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="search",
            description="Search tweets by query string with optional filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (supports operators like from:, lang:)"},
                    "limit": {"type": "integer", "description": "Number of results (default 10, max 20)", "default": 10},
                    "from": {"type": "string", "description": "Only tweets from this user (without @)"},
                    "to": {"type": "string", "description": "Only tweets directed at this user (without @)"},
                    "since": {"type": "string", "description": "Tweets since date (YYYY-MM-DD)"},
                    "until": {"type": "string", "description": "Tweets until date (YYYY-MM-DD)"},
                    "lang": {"type": "string", "description": "Filter by language code (e.g. en, zh, ja)"},
                    "type": {
                        "type": "string",
                        "enum": ["top", "latest", "photos", "videos"],
                        "description": "Search tab",
                    },
                    "exclude_retweets": {"type": "boolean", "description": "Exclude retweets", "default": False},
                    "exclude_replies": {"type": "boolean", "description": "Exclude replies", "default": False},
                    "min_likes": {"type": "integer", "description": "Minimum number of likes"},
                },
            },
        ),
        Tool(
            name="feed",
            description="Fetch home timeline.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of tweets (default 10, max 50)", "default": 10},
                },
            },
        ),
        Tool(
            name="bookmarks",
            description="Fetch bookmarked tweets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of bookmarks (default 10, max 50)", "default": 10},
                },
            },
        ),
        Tool(
            name="show",
            description="View a tweet and its replies by tweet ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Tweet ID to view"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="likes",
            description="Show tweets liked by a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Twitter username (without @)"},
                    "limit": {"type": "integer", "description": "Number of tweets (default 10, max 50)", "default": 10},
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="user",
            description="View a user's profile information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Twitter username (without @)"},
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="user-posts",
            description="List tweets posted by a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Twitter username (without @)"},
                    "limit": {"type": "integer", "description": "Number of tweets (default 10, max 50)", "default": 10},
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="status",
            description="Check whether the current Twitter/X session is authenticated.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="whoami",
            description="Show the currently authenticated user's profile.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="following",
            description="List accounts a user is following.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Twitter username (without @)"},
                    "limit": {"type": "integer", "description": "Number of results (default 20, max 50)", "default": 20},
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="followers",
            description="List followers of a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Twitter username (without @)"},
                    "limit": {"type": "integer", "description": "Number of results (default 20, max 50)", "default": 20},
                },
                "required": ["username"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    await _limiter.acquire()

    try:
        if name == "search":
            query = arguments["query"]
            limit = min(int(arguments.get("limit", 10)), 20)
            cmd = ["search", query, "-n", str(limit)]
            if arguments.get("from"):
                cmd += ["--from", arguments["from"].lstrip("@")]
            if arguments.get("to"):
                cmd += ["--to", arguments["to"].lstrip("@")]
            if arguments.get("since"):
                cmd += ["--since", arguments["since"]]
            if arguments.get("until"):
                cmd += ["--until", arguments["until"]]
            if arguments.get("lang"):
                cmd += ["--lang", arguments["lang"]]
            if arguments.get("type"):
                cmd += ["-t", arguments["type"]]
            if arguments.get("exclude_retweets"):
                cmd += ["--exclude", "retweets"]
            if arguments.get("exclude_replies"):
                cmd += ["--exclude", "replies"]
            if arguments.get("min_likes") is not None:
                cmd += ["--min-likes", str(arguments["min_likes"])]
            output = _run_twitter(cmd)

        elif name == "feed":
            limit = min(int(arguments.get("limit", 10)), 20)
            output = _run_twitter(["feed", "-n", str(limit)])

        elif name == "bookmarks":
            limit = min(int(arguments.get("limit", 10)), 20)
            output = _run_twitter(["bookmarks", "-n", str(limit)])

        elif name == "show":
            output = _run_twitter(["tweet", arguments["id"]])

        elif name == "likes":
            username = arguments["username"].lstrip("@")
            limit = min(int(arguments.get("limit", 10)), 20)
            output = _run_twitter(["likes", username, "-n", str(limit)])

        elif name == "user":
            username = arguments["username"].lstrip("@")
            output = _run_twitter(["user", username])

        elif name == "user-posts":
            username = arguments["username"].lstrip("@")
            limit = min(int(arguments.get("limit", 10)), 20)
            output = _run_twitter(["user-posts", username, "-n", str(limit)])

        elif name == "status":
            output = _run_twitter(["status"])

        elif name == "whoami":
            output = _run_twitter(["whoami"])

        elif name == "following":
            username = arguments["username"].lstrip("@")
            limit = min(int(arguments.get("limit", 20)), 50)
            output = _run_twitter(["following", username, "-n", str(limit)])

        elif name == "followers":
            username = arguments["username"].lstrip("@")
            limit = min(int(arguments.get("limit", 20)), 50)
            output = _run_twitter(["followers", username, "-n", str(limit)])

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]

    return [TextContent(type="text", text=output)]


async def _async_main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Synchronous entry point for CLI (pyproject.toml [project.scripts])."""
    import asyncio
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
