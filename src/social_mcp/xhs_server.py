"""Xiaohongshu (小红书) MCP Server — browser-automated full-featured server."""

from __future__ import annotations

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from social_mcp._rate_limiter import RateLimiter
from social_mcp.xhs_browser import BrowserManager
from social_mcp.xhs_client import XhsClient

_limiter = RateLimiter(max_per_second=1.0, daily_max=500)

_browser_mgr = BrowserManager(headless=True)
_client: XhsClient | None = None

server = Server("xiaohongshu")

# ── lifecycle helpers ──────────────────────────────────────────────


async def _ensure_client():
    global _client
    if _client is not None:
        return
    browser = await _browser_mgr.ensure_browser()
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    saved = _browser_mgr.load_cookies()
    if saved:
        try:
            await ctx.add_cookies(saved)
        except Exception:
            pass
    page = (ctx.pages or [await ctx.new_page()])[0]
    _client = XhsClient(page)


async def _get_client() -> XhsClient:
    if _client is None:
        await _ensure_client()
    return _client  # type: ignore[return-value]


# ── tool definitions ───────────────────────────────────────────────


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        # ── auth ──────────────────────────────────────────────────
        Tool(
            name="login",
            description=(
                "Log in to Xiaohongshu via QR code. "
                "A browser window will open — scan the QR code with the Xiaohongshu app. "
                "The session is saved for future use."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "integer",
                        "description": "Seconds to wait for QR scan (default 120)",
                    },
                },
            },
        ),
        Tool(
            name="logout",
            description="Clear the saved session and log out.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="status",
            description="Check whether the current session is authenticated.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── read / browse ─────────────────────────────────────────
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
                    "page": {
                        "type": "integer",
                        "description": "Page number (default 1)",
                    },
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
            description="Browse hot / trending notes by category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "fashion",
                            "food",
                            "cosmetics",
                            "movie",
                            "career",
                            "love",
                            "home",
                            "gaming",
                            "travel",
                            "fitness",
                        ],
                        "description": "Category filter (optional)",
                    },
                },
            },
        ),
        Tool(
            name="read",
            description="Read a note by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "Note ID (24-char hex string from the URL)",
                    },
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="comments",
            description="View comments on a note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "Note ID",
                    },
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="user",
            description="View a user's profile by user ID.",
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
            description="List notes published by a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
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
            name="whoami",
            description="Show the currently authenticated user's profile.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── interaction ───────────────────────────────────────────
        Tool(
            name="like",
            description="Like or unlike a note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                    "unlike": {
                        "type": "boolean",
                        "description": "Set to true to unlike instead of like",
                    },
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="favorite",
            description="Favorite (bookmark) or unfavorite a note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                    "unfavorite": {
                        "type": "boolean",
                        "description": "Set to true to unfavorite instead",
                    },
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="comment",
            description="Post a comment on a note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                    "content": {"type": "string", "description": "Comment text"},
                },
                "required": ["note_id", "content"],
            },
        ),
        Tool(
            name="reply-comment",
            description="Reply to an existing comment on a note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                    "comment_id": {"type": "string", "description": "Target comment ID"},
                    "content": {"type": "string", "description": "Reply content"},
                },
                "required": ["note_id", "comment_id", "content"],
            },
        ),
        # ── manage ────────────────────────────────────────────────
        Tool(
            name="delete-note",
            description="Delete one of your own notes. Requires login.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID to delete"},
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="publish",
            description=(
                "Publish a new note (image or video). "
                "For image posts: provide 1-18 image file paths. "
                "For video posts: provide exactly 1 video file path."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title (max 20 characters / 40 display units)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Body text (max 1000 characters)",
                    },
                    "media_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Local file paths or HTTP(S) URLs. "
                            "Image: 1-18 files. Video: exactly 1 file."
                        ),
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Topic tags (optional)",
                    },
                    "schedule_at": {
                        "type": "string",
                        "description": "ISO8601 schedule time (optional)",
                    },
                },
                "required": ["title", "content", "media_paths"],
            },
        ),
    ]


# ── tool call handler ──────────────────────────────────────────────


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    await _limiter.acquire()

    try:
        client = await _get_client()

        # ── auth ──────────────────────────────────────────────────
        if name == "login":
            timeout = arguments.get("timeout", 120)
            result = await _browser_mgr.login(timeout=timeout)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        if name == "logout":
            result = await _browser_mgr.logout()
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        if name == "status":
            result = await _browser_mgr.check_status()
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        # ── read / browse ─────────────────────────────────────────
        if name == "search":
            results = await client.search_notes(
                keyword=arguments["keyword"],
                sort=arguments.get("sort", "general"),
                note_type=arguments.get("type", "all"),
                page=arguments.get("page", 1),
            )
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False))]

        if name == "feed":
            results = await client.get_feed()
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False))]

        if name == "hot":
            results = await client.get_hot(category=arguments.get("category"))
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False))]

        if name == "read":
            result = await client.get_note_detail(note_id=arguments["note_id"])
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        if name == "comments":
            results = await client.get_comments(note_id=arguments["note_id"])
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False))]

        if name == "user":
            result = await client.get_user_info(user_id=arguments["user_id"])
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        if name == "user-posts":
            results = await client.get_user_notes(user_id=arguments["user_id"])
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False))]

        if name == "search-user":
            results = await client.search_users(keyword=arguments["keyword"])
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False))]

        if name == "whoami":
            result = await client.get_current_user_profile()
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        # ── interaction ───────────────────────────────────────────
        if name == "like":
            unlike = arguments.get("unlike", False)
            ok = await client.unlike_note(arguments["note_id"]) if unlike else await client.like_note(arguments["note_id"])
            return [TextContent(type="text", text=json.dumps(
                {"action": "unlike" if unlike else "like", "ok": ok},
                ensure_ascii=False,
            ))]

        if name == "favorite":
            unfav = arguments.get("unfavorite", False)
            ok = await client.unfavorite_note(arguments["note_id"]) if unfav else await client.favorite_note(arguments["note_id"])
            return [TextContent(type="text", text=json.dumps(
                {"action": "unfavorite" if unfav else "favorite", "ok": ok},
                ensure_ascii=False,
            ))]

        if name == "comment":
            ok = await client.comment_on_note(
                note_id=arguments["note_id"],
                content=arguments["content"],
            )
            return [TextContent(type="text", text=json.dumps(
                {"action": "comment", "ok": ok},
                ensure_ascii=False,
            ))]

        if name == "reply-comment":
            ok = await client.reply_comment(
                note_id=arguments["note_id"],
                comment_id=arguments["comment_id"],
                content=arguments["content"],
            )
            return [TextContent(type="text", text=json.dumps(
                {"action": "reply", "ok": ok},
                ensure_ascii=False,
            ))]

        # ── manage ────────────────────────────────────────────────
        if name == "delete-note":
            ok = await client.delete_note(arguments["note_id"])
            return [TextContent(type="text", text=json.dumps(
                {"action": "delete", "ok": ok},
                ensure_ascii=False,
            ))]

        if name == "publish":
            result = await _browser_mgr.publish(
                title=arguments["title"],
                content=arguments["content"],
                media_paths=arguments["media_paths"],
                tags=arguments.get("tags"),
                schedule_at=arguments.get("schedule_at"),
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# ── entry point ────────────────────────────────────────────────────


async def main():
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        await _browser_mgr.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
