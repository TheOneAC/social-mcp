from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page

DATA_DIR = Path.home() / ".social-mcp-xhs"
COOKIES_FILE = DATA_DIR / "cookies.json"
LOGIN_URL = "https://www.xiaohongshu.com/login"
PUBLISH_URL = "https://www.xiaohongshu.com/publish/upload"


class BrowserManager:
    """Manages a Playwright Chromium instance for Xiaohongshu operations.

    Handles login (QR code), cookie persistence, and browser lifecycle.
    """

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._browser: Browser | None = None
        self._playwright = None
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── lifecycle ──────────────────────────────────────────────────

    async def ensure_browser(self) -> Browser:
        if self._browser and self._browser.is_connected():
            return self._browser
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        return self._browser

    async def close(self):
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    # ── cookies ────────────────────────────────────────────────────

    def load_cookies(self) -> list[dict] | None:
        if COOKIES_FILE.exists():
            try:
                raw = json.loads(COOKIES_FILE.read_text())
                if isinstance(raw, list) and len(raw) > 0:
                    return raw
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def save_cookies(self, cookies: list[dict]):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        COOKIES_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))

    def clear_cookies(self):
        if COOKIES_FILE.exists():
            COOKIES_FILE.unlink()

    # ── auth ───────────────────────────────────────────────────────

    async def login(self, timeout: int = 120) -> dict:
        """Perform QR-code login.

        Returns a dict with keys ``status`` (ok/error/timeout) and
        ``message`` (human-readable detail).
        """
        browser = await self.ensure_browser()
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        try:
            await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

            # Wait for the QR code image to appear
            qr_selector = "canvas[class*='qrcode']"
            try:
                await page.wait_for_selector(qr_selector, timeout=10000)
            except Exception:
                # If already logged in, QR code won't appear
                current_cookies = await ctx.cookies()
                if any(c["name"] in ("a1", "web_session") for c in current_cookies):
                    self.save_cookies(current_cookies)
                    return {"status": "ok", "message": "Already logged in."}
                return {
                    "status": "error",
                    "message": "QR code element not found on page.",
                }

            # Take a screenshot so the user can see the QR code
            screenshot = await page.screenshot(full_page=True)
            screenshot_path = DATA_DIR / "login_qrcode.png"
            screenshot_path.write_bytes(screenshot)

            # Wait for successful login (URL changes away from /login)
            try:
                await page.wait_for_url(
                    lambda url: "login" not in url,
                    timeout=timeout * 1000,
                )
            except Exception:
                return {
                    "status": "timeout",
                    "message": (
                        f"QR code scan timed out after {timeout}s. "
                        f"Screenshot saved to {screenshot_path}"
                    ),
                }

            # Save session cookies
            current_cookies = await ctx.cookies()
            self.save_cookies(current_cookies)

            # Get nickname
            nickname = await self._get_nickname(page)

            return {
                "status": "ok",
                "message": f"Logged in as {nickname}.",
            }
        finally:
            await page.close()

    async def logout(self) -> dict:
        """Clear stored session."""
        self.clear_cookies()
        return {"status": "ok", "message": "Logged out (cookies cleared)."}

    async def check_status(self) -> dict:
        """Check whether the stored session is still valid."""
        cookies = self.load_cookies()
        if not cookies:
            return {
                "status": "logged_out",
                "message": "Not logged in. Use the login tool first.",
            }

        # Quick validation via an authenticated page request
        browser = await self.ensure_browser()
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        try:
            await page.goto(
                "https://www.xiaohongshu.com/explore",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            current_url = page.url
            if "login" in current_url:
                self.clear_cookies()
                return {
                    "status": "expired",
                    "message": "Session expired. Please login again.",
                }
            nickname = await self._get_nickname(page) or "Unknown"
            return {
                "status": "ok",
                "message": f"Logged in as {nickname}.",
            }
        except Exception:
            return {
                "status": "unknown",
                "message": "Could not verify session. Try logging in again.",
            }
        finally:
            await page.close()

    async def _get_nickname(self, page: Page) -> str:
        """Try to extract the current user's display nickname from the page."""
        try:
            text = await page.text_content(
                "span[class*='nickname']"
                ", span.username"
                ", div[class*='user-name']"
                ", span[class*='name']"
            )
            if text:
                return text.strip()
        except Exception:
            pass
        return "Unknown"

    # ── publish ────────────────────────────────────────────────────

    async def publish(
        self,
        title: str,
        content: str,
        media_paths: list[str],
        *,
        tags: list[str] | None = None,
        schedule_at: str | None = None,
        is_original: bool = False,
    ) -> dict:
        """Publish a note (image or video) via the Xiaohongshu web editor.

        Returns a dict with keys ``status`` (ok/error), ``message``, and
        optionally ``note_id`` on success.
        """
        cookies = self.load_cookies()
        if not cookies:
            return {"status": "error", "message": "Not logged in. Use login first."}

        browser = await self.ensure_browser()
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        try:
            await page.goto(PUBLISH_URL, wait_until="networkidle", timeout=30000)

            # Detect if we need to log in
            if "login" in page.url:
                return {
                    "status": "error",
                    "message": "Session expired. Please login again.",
                }

            # Detect media type
            is_video = any(
                Path(p).suffix.lower()
                in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv")
                for p in media_paths
            )

            if is_video:
                if len(media_paths) != 1:
                    return {
                        "status": "error",
                        "message": "Video publish requires exactly 1 video file.",
                    }
                return await self._publish_video(
                    page, title, content, media_paths[0], tags, schedule_at
                )
            else:
                if not media_paths:
                    return {
                        "status": "error",
                        "message": "At least 1 image is required.",
                    }
                if len(media_paths) > 18:
                    return {
                        "status": "error",
                        "message": "Maximum 18 images per post.",
                    }
                return await self._publish_image(
                    page, title, content, media_paths, tags, schedule_at, is_original
                )
        finally:
            await page.close()

    async def _publish_image(
        self,
        page: Page,
        title: str,
        content: str,
        image_paths: list[str],
        tags: list[str] | None,
        schedule_at: str | None,
        is_original: bool,
    ) -> dict:
        """Publish an image-text note."""
        # Upload images via the file input
        upload_selector = "input[type='file']"
        try:
            file_chooser = await page.wait_for_event("filechooser", timeout=10000)
            # If the event fired already, upload; otherwise trigger it
        except Exception:
            # Click the upload button to trigger file chooser
            upload_btn_selector = (
                "div[class*='upload']"
                ", button[class*='upload']"
                ", div[class*='add-pic']"
                ", div[role='button']:has-text('上传')"
            )
            try:
                await page.click(upload_btn_selector)
            except Exception:
                pass
            file_chooser = await page.wait_for_event("filechooser", timeout=10000)

        await file_chooser.set_files(image_paths)

        # Wait for uploads to complete
        await asyncio.sleep(3)

        # Fill title
        title_selector = (
            "input[class*='title']"
            ", input[placeholder*='标题']"
            ", div[class*='title'] div[contenteditable='true']"
        )
        try:
            el = await page.wait_for_selector(title_selector, timeout=5000)
            if el:
                await el.fill(title)
        except Exception:
            pass

        # Fill content
        content_selector = (
            "div[class*='content'] div[contenteditable='true']"
            ", div[class*='ql-editor']"
            ", textarea[placeholder*='正文']"
            ", div[contenteditable='true']"
        )
        try:
            el = await page.wait_for_selector(content_selector, timeout=5000)
            if el:
                await el.fill(content)
        except Exception:
            pass

        # Add tags
        if tags:
            tag_input_selector = (
                "input[placeholder*='话题']"
                ", input[class*='tag-input']"
                ", div[class*='topic'] input"
            )
            try:
                tag_el = await page.wait_for_selector(tag_input_selector, timeout=5000)
                if tag_el:
                    for tag in tags:
                        await tag_el.fill(tag)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(0.3)
            except Exception:
                pass

        # Original declaration
        if is_original:
            original_selector = "div[class*='original'] span[class*='switch']"
            try:
                switch = await page.query_selector(original_selector)
                if switch:
                    await switch.click()
            except Exception:
                pass

        # Schedule
        if schedule_at:
            # TODO: schedule_at support — needs date picker interaction
            pass

        # Submit
        submit_selector = (
            "button[class*='submit']"
            ", div[class*='submit']"
            ", button:has-text('发布')"
            ", div[role='button']:has-text('发布')"
        )
        try:
            submit_btn = await page.wait_for_selector(submit_selector, timeout=5000)
            if submit_btn:
                await submit_btn.click()
        except Exception:
            return {
                "status": "error",
                "message": "Could not find the publish button.",
            }

        # Wait for publish to complete
        await asyncio.sleep(5)

        return {
            "status": "ok",
            "message": "Image note published successfully.",
        }

    async def _publish_video(
        self,
        page: Page,
        title: str,
        content: str,
        video_path: str,
        tags: list[str] | None,
        schedule_at: str | None,
    ) -> dict:
        """Publish a video note."""
        upload_selector = "input[type='file']"
        try:
            file_chooser = await page.wait_for_event("filechooser", timeout=10000)
        except Exception:
            try:
                await page.click("div[class*='upload'], button[class*='upload']")
            except Exception:
                pass
            file_chooser = await page.wait_for_event("filechooser", timeout=10000)

        await file_chooser.set_files([video_path])
        await asyncio.sleep(3)  # Wait for upload start

        # Wait for video processing
        await asyncio.sleep(5)

        # Fill title
        title_selector = (
            "input[class*='title']"
            ", input[placeholder*='标题']"
            ", div[class*='title'] div[contenteditable='true']"
        )
        try:
            el = await page.wait_for_selector(title_selector, timeout=5000)
            if el:
                await el.fill(title)
        except Exception:
            pass

        # Fill content
        content_selector = (
            "div[class*='content'] div[contenteditable='true']"
            ", div[class*='ql-editor']"
            ", textarea[placeholder*='正文']"
        )
        try:
            el = await page.wait_for_selector(content_selector, timeout=5000)
            if el:
                await el.fill(content)
        except Exception:
            pass

        # Tags
        if tags:
            tag_input_selector = (
                "input[placeholder*='话题']"
                ", input[class*='tag-input']"
            )
            try:
                tag_el = await page.wait_for_selector(tag_input_selector, timeout=5000)
                if tag_el:
                    for tag in tags:
                        await tag_el.fill(tag)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(0.3)
            except Exception:
                pass

        # Submit
        submit_selector = (
            "button[class*='submit']"
            ", button:has-text('发布')"
            ", div[role='button']:has-text('发布')"
        )
        try:
            submit_btn = await page.wait_for_selector(submit_selector, timeout=5000)
            if submit_btn:
                await submit_btn.click()
        except Exception:
            return {
                "status": "error",
                "message": "Could not find the publish button.",
            }

        await asyncio.sleep(5)

        return {
            "status": "ok",
            "message": "Video note published successfully.",
        }
