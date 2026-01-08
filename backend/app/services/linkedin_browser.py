import json
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class LinkedInBrowser:
    """Manages Playwright browser for LinkedIn with cookie-based authentication."""

    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    FEED_URL = "https://www.linkedin.com/feed/"
    LOGIN_URL = "https://www.linkedin.com/login"

    def __init__(self, cookies_path: Path | None = None):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        if cookies_path is None:
            cookies_path = Path(__file__).parents[2] / "playwright-data" / "cookies.json"
        self._cookies_path = cookies_path

    async def __aenter__(self) -> "LinkedInBrowser":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def start(self, headless: bool = True) -> None:
        """Start the browser and load cookies if available."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()

        if self._cookies_path.exists():
            await self._load_cookies()

    async def stop(self) -> None:
        """Close browser and cleanup resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    async def _load_cookies(self) -> None:
        """Load cookies from file into browser context."""
        with open(self._cookies_path, "r") as f:
            cookies = json.load(f)
        await self._context.add_cookies(cookies)

    async def _save_cookies(self) -> None:
        """Save current cookies to file."""
        self._cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies = await self._context.cookies()
        with open(self._cookies_path, "w") as f:
            json.dump(cookies, f, indent=2)

    async def is_logged_in(self) -> bool:
        """Check if we have a valid authenticated session."""
        await self._page.goto(self.FEED_URL, wait_until="domcontentloaded")
        current_url = self._page.url

        # If redirected to login page, we're not authenticated
        if "/login" in current_url or "/checkpoint" in current_url:
            return False

        # Check for feed-specific element
        feed_indicator = await self._page.query_selector("div.feed-shared-update-v2")
        return feed_indicator is not None

    async def manual_login(self) -> bool:
        """
        Open browser in headed mode for manual login.
        Call this once to establish initial session.
        Returns True if login successful and cookies saved.
        """
        # Must restart in headed mode
        await self.stop()
        await self.start(headless=False)

        await self._page.goto(self.LOGIN_URL, wait_until="domcontentloaded")

        print("=" * 50)
        print("MANUAL LOGIN REQUIRED")
        print("1. Log in to LinkedIn in the browser window")
        print("2. Complete any 2FA if prompted")
        print("3. Wait until you see your feed")
        print("4. Press Enter here when done...")
        print("=" * 50)

        input()  # Blocks until user presses Enter

        if await self.is_logged_in():
            await self._save_cookies()
            print("Cookies saved successfully!")
            return True

        print("Login verification failed. Please try again.")
        return False

    @property
    def page(self) -> Page:
        """Get the current page. Raises if browser not started."""
        if self._page is None:
            raise RuntimeError("Browser not started. Call start() or use async with.")
        return self._page