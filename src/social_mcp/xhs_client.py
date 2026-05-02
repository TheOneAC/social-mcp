from __future__ import annotations

import json
import re
from typing import Any

from playwright.async_api import Page


class XhsClient:
    """Xiaohongshu data client, operating through a Playwright Page.

    All operations are performed within the browser context, so cookies,
    headers, and anti-bot signals are handled automatically.
    """

    def __init__(self, page: Page):
        self._page = page

    # ── helpers ────────────────────────────────────────────────────

    async def _extract_initial_state(self) -> dict[str, Any]:
        """Extract the ``__INITIAL_STATE__`` JSON embedded in the page."""
        try:
            result = await self._page.evaluate("window.__INITIAL_STATE__")
            if result:
                return result
        except Exception:
            pass
        # Fallback: scrape from HTML
        html = await self._page.content()
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", html, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        return {}

    async def _goto(self, url: str, *, timeout: int = 20000):
        """Navigate and wait for content to settle."""
        await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await self._page.wait_for_timeout(1500)

    async def _current_note_ids(self) -> list[str]:
        """Extract note IDs currently visible on the page."""
        return await self._page.evaluate(
            """() => {
            const cards = document.querySelectorAll(
                "a[href*='/explore/'], a[href*='/discovery/item/'], section[class*='note-item'] a"
            );
            return [...new Set(
                [...cards].map(a => {
                    const m = a.href.match(/\\/([a-f0-9]{24})/);
                    return m ? m[1] : null;
                }).filter(Boolean)
            )];
        }"""
        )

    # ── read operations ────────────────────────────────────────────

    async def search_notes(
        self, keyword: str, sort: str = "general", note_type: str = "all", page: int = 1
    ) -> list[dict[str, Any]]:
        """Search notes by keyword."""
        sort_param = {"general": "general", "popular": "popular", "latest": "time_descending"}.get(
            sort, sort
        )
        url = (
            f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
            f"&source=web_search_result_notes&type={note_type}&sort={sort_param}&page={page}"
        )
        await self._goto(url)
        state = await self._extract_initial_state()
        note_list = (
            state.get("search", {})
            .get("notes", {})
            .get("items", [])
        )
        if not note_list:
            # Fallback: scrape from DOM
            note_list = await self._scrape_search_results()
        return note_list

    async def _scrape_search_results(self) -> list[dict[str, Any]]:
        """Fallback scrape of note cards from the current page."""
        return await self._page.evaluate(
            """() => {
            const items = document.querySelectorAll(
                "section[class*='note-item'], div[class*='feeds-page'] section"
            );
            return [...items].map(el => ({
                title: el.querySelector("a[class*='title']")?.textContent?.trim(),
                link: el.querySelector("a")?.href,
                likes: el.querySelector("span[class*='like']")?.textContent?.trim(),
                author: el.querySelector("a[class*='author']")?.textContent?.trim(),
            }));
        }"""
        )

    async def get_feed(self) -> list[dict[str, Any]]:
        """Get the recommendation feed."""
        await self._goto("https://www.xiaohongshu.com/explore")
        state = await self._extract_initial_state()
        feed = (
            state.get("feed", {})
            .get("recommend", {})
            .get("items", [])
        )
        if not feed:
            feed = await self._scrape_search_results()
        return feed

    async def get_hot(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get trending / hot notes."""
        if category:
            url = f"https://www.xiaohongshu.com/page/{category}"
        else:
            url = "https://www.xiaohongshu.com/explore?nav=discovery"
        await self._goto(url)
        state = await self._extract_initial_state()
        return (
            state.get("discovery", {}).get("items", [])
        )

    async def get_note_detail(self, note_id: str) -> dict[str, Any]:
        """Get full detail of a single note by ID."""
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        await self._goto(url)
        state = await self._extract_initial_state()
        note = state.get("note", {}).get("noteDetailMap", {}).get(note_id, {})
        if not note:
            note = await self._scrape_note_detail()
        return note

    async def _scrape_note_detail(self) -> dict[str, Any]:
        """Fallback scrape of the current note page."""
        return await self._page.evaluate(
            """() => {
            const title = document.querySelector("div[class*='title']")?.textContent;
            const content = document.querySelector("div[class*='content']")?.textContent;
            const author = document.querySelector("span[class*='username']")?.textContent;
            const images = [...document.querySelectorAll("img[class*='note-image']")]
                .map(i => i.src);
            return { title, content, author, images };
        }"""
        )

    async def get_comments(self, note_id: str) -> list[dict[str, Any]]:
        """Get comments on a note."""
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        await self._goto(url)
        state = await self._extract_initial_state()
        comments = (
            state.get("note", {})
            .get("noteDetailMap", {})
            .get(note_id, {})
            .get("interactInfo", {})
            .get("comments", [])
        )
        if not comments:
            comments = await self._scrape_comments()
        return comments

    async def _scrape_comments(self) -> list[dict[str, Any]]:
        """Fallback scrape of comments from the current page."""
        return await self._page.evaluate(
            """() => {
            const items = document.querySelectorAll("div[class*='comment-item']");
            return [...items].map(el => ({
                user: el.querySelector("span[class*='name']")?.textContent,
                content: el.querySelector("div[class*='content']")?.textContent,
                likes: el.querySelector("span[class*='like']")?.textContent,
                time: el.querySelector("span[class*='date']")?.textContent,
            }));
        }"""
        )

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user profile info."""
        url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
        await self._goto(url)
        return await self._extract_initial_state()

    async def get_user_notes(self, user_id: str) -> list[dict[str, Any]]:
        """Get notes published by a user."""
        url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
        await self._goto(url)
        state = await self._extract_initial_state()
        return (
            state.get("user", {})
            .get("notes", {})
            .get("items", [])
        )

    async def search_users(self, keyword: str) -> list[dict[str, Any]]:
        """Search for users by keyword."""
        url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_users"
        await self._goto(url)
        state = await self._extract_initial_state()
        return (
            state.get("search", {})
            .get("user", {})
            .get("items", [])
        )

    # ── interaction operations ─────────────────────────────────────

    async def like_note(self, note_id: str) -> bool:
        """Like a note. Returns True on success."""
        return await self._page.evaluate(
            f"""async () => {{
            try {{
                const resp = await fetch(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/feed/like",
                    {{ method: "POST", headers: {{ "content-type": "application/json" }},
                       body: JSON.stringify({{ id: "{note_id}" }}) }}
                );
                return resp.ok;
            }} catch (e) {{ return false; }}
        }}"""
        )

    async def unlike_note(self, note_id: str) -> bool:
        """Unlike a note."""
        return await self._page.evaluate(
            f"""async () => {{
            try {{
                const resp = await fetch(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/feed/unlike",
                    {{ method: "POST", headers: {{ "content-type": "application/json" }},
                       body: JSON.stringify({{ id: "{note_id}" }}) }}
                );
                return resp.ok;
            }} catch (e) {{ return false; }}
        }}"""
        )

    async def favorite_note(self, note_id: str) -> bool:
        """Favorite (bookmark) a note."""
        return await self._page.evaluate(
            f"""async () => {{
            try {{
                const resp = await fetch(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/feed/favorite",
                    {{ method: "POST", headers: {{ "content-type": "application/json" }},
                       body: JSON.stringify({{ id: "{note_id}" }}) }}
                );
                return resp.ok;
            }} catch (e) {{ return false; }}
        }}"""
        )

    async def unfavorite_note(self, note_id: str) -> bool:
        """Unfavorite a note."""
        return await self._page.evaluate(
            f"""async () => {{
            try {{
                const resp = await fetch(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/feed/unfavorite",
                    {{ method: "POST", headers: {{ "content-type": "application/json" }},
                       body: JSON.stringify({{ id: "{note_id}" }}) }}
                );
                return resp.ok;
            }} catch (e) {{ return false; }}
        }}"""
        )

    async def comment_on_note(
        self, note_id: str, content: str
    ) -> bool:
        """Post a comment on a note."""
        return await self._page.evaluate(
            f"""async () => {{
            try {{
                const resp = await fetch(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/comment/post",
                    {{ method: "POST", headers: {{ "content-type": "application/json" }},
                       body: JSON.stringify({{ feed_id: "{note_id}", content: "{content}" }}) }}
                );
                return resp.ok;
            }} catch (e) {{ return false; }}
        }}"""
        )

    async def reply_comment(
        self, note_id: str, comment_id: str, content: str
    ) -> bool:
        """Reply to a comment on a note."""
        return await self._page.evaluate(
            f"""async () => {{
            try {{
                const resp = await fetch(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/comment/post",
                    {{ method: "POST", headers: {{ "content-type": "application/json" }},
                       body: JSON.stringify({{
                           feed_id: "{note_id}",
                           content: "{content}",
                           target_comment_id: "{comment_id}"
                       }}) }}
                );
                return resp.ok;
            }} catch (e) {{ return false; }}
        }}"""
        )

    async def delete_note(self, note_id: str) -> bool:
        """Delete one of the user's own notes."""
        return await self._page.evaluate(
            f"""async () => {{
            try {{
                const resp = await fetch(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/feed/delete",
                    {{ method: "POST", headers: {{ "content-type": "application/json" }},
                       body: JSON.stringify({{ id: "{note_id}" }}) }}
                );
                return resp.ok;
            }} catch (e) {{ return false; }}
        }}"""
        )

    async def get_current_user_profile(self) -> dict[str, Any]:
        """Get detailed profile of the currently authenticated user."""
        await self._goto("https://www.xiaohongshu.com/user/my")
        return await self._extract_initial_state()
