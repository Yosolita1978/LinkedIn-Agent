import json
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class LinkedInBrowser:
    """Manages Playwright browser for LinkedIn with cookie-based authentication."""

    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    FEED_URL = "https://www.linkedin.com/feed/"
    LOGIN_URL = "https://www.linkedin.com/login"
    CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"
    FOLLOWERS_URL = "https://www.linkedin.com/mynetwork/network-manager/people-follow/followers/"

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

        if "/login" in current_url or "/checkpoint" in current_url:
            return False

        feed_indicator = await self._page.query_selector("div.feed-shared-update-v2")
        return feed_indicator is not None

    async def manual_login(self) -> bool:
        """
        Open browser in headed mode for manual login.
        Call this once to establish initial session.
        Returns True if login successful and cookies saved.
        """
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

        input()

        if await self.is_logged_in():
            await self._save_cookies()
            print("Cookies saved successfully!")
            return True

        print("Login verification failed. Please try again.")
        return False

    async def scrape_connections(self) -> list[dict]:
        """
        Scrape the connections list page.
        Returns list of dicts with: name, headline, profile_url
        """
        await self._page.goto(self.CONNECTIONS_URL, wait_until="domcontentloaded")
        await self._page.wait_for_selector('div[data-view-name="connections-list"]', timeout=10000)

        cards = await self._page.query_selector_all('div[data-view-name="connections-list"] > div')
        connections = []

        for card in cards:
            connection = await self._extract_connection_card(card)
            if connection:
                connections.append(connection)

        return connections

    async def _extract_connection_card(self, card) -> dict | None:
        """Extract data from a single connection card element."""
        try:
            link_el = await card.query_selector('a[data-view-name="connections-profile"]')
            if not link_el:
                return None

            profile_url = await link_el.get_attribute("href")

            name_el = await card.query_selector("a.f89e0a9a")
            name = await name_el.inner_text() if name_el else ""

            headline_el = await card.query_selector("p.d45641c5")
            headline = await headline_el.inner_text() if headline_el else ""

            return {
                "name": name.strip(),
                "headline": headline.strip(),
                "profile_url": profile_url if profile_url.startswith("http") else f"{self.LINKEDIN_BASE_URL}{profile_url}",
            }
        except Exception:
            return None

    async def scrape_followers(self) -> list[dict]:
        """
        Scrape the followers list page.
        Returns list of dicts with: name, headline, profile_url
        """
        await self._page.goto(self.FOLLOWERS_URL, wait_until="domcontentloaded")
        
        # Wait for content to load
        await self._page.wait_for_timeout(2000)

        # Try the same selector pattern as connections first
        cards = await self._page.query_selector_all('div[data-view-name="connections-list"] > div')
        
        # If that doesn't work, try alternative selectors
        if not cards:
            cards = await self._page.query_selector_all('div[data-view-name="followers-list"] > div')
        
        if not cards:
            # Fallback: look for profile links and work up
            cards = await self._page.query_selector_all('a[data-view-name="followers-profile"]')
            if cards:
                # Get parent containers
                new_cards = []
                for link in cards:
                    parent = await link.evaluate_handle("el => el.closest('div.f21c1da8')")
                    if parent:
                        new_cards.append(parent)
                cards = new_cards

        followers = []
        for card in cards:
            follower = await self._extract_follower_card(card)
            if follower:
                followers.append(follower)

        return followers

    async def _extract_follower_card(self, card) -> dict | None:
        """Extract data from a single follower card element."""
        try:
            # Try multiple selector patterns
            link_el = await card.query_selector('a[data-view-name="followers-profile"]')
            if not link_el:
                link_el = await card.query_selector('a[data-view-name="connections-profile"]')
            if not link_el:
                link_el = await card.query_selector('a[href*="/in/"]')
            
            if not link_el:
                return None

            profile_url = await link_el.get_attribute("href")

            # Name
            name_el = await card.query_selector("a.f89e0a9a")
            if not name_el:
                name_el = await card.query_selector("span.f89e0a9a")
            name = await name_el.inner_text() if name_el else ""

            # Headline
            headline_el = await card.query_selector("p.d45641c5")
            if not headline_el:
                headline_el = await card.query_selector("p.f389f326")
            headline = await headline_el.inner_text() if headline_el else ""

            return {
                "name": name.strip(),
                "headline": headline.strip(),
                "profile_url": profile_url if profile_url.startswith("http") else f"{self.LINKEDIN_BASE_URL}{profile_url}",
            }
        except Exception:
            return None

    @property
    def page(self) -> Page:
        """Get the current page. Raises if browser not started."""
        if self._page is None:
            raise RuntimeError("Browser not started. Call start() or use async with.")
        return self._page