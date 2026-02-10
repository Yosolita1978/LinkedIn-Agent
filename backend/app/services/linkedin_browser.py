import json
import logging
import asyncio
import random
from functools import wraps
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout

# Configure logging
logger = logging.getLogger(__name__)

# Common Chrome user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


async def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
    """Add a random delay to simulate human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def random_viewport() -> dict:
    """Generate a random but realistic viewport size."""
    # Common screen resolutions with slight variations
    base_widths = [1280, 1366, 1440, 1536, 1920]
    base_heights = [720, 768, 800, 864, 900, 1080]

    width = random.choice(base_widths) + random.randint(-20, 20)
    height = random.choice(base_heights) + random.randint(-20, 20)

    return {"width": width, "height": height}


class LinkedInError(Exception):
    """Base exception for LinkedIn-related errors."""
    pass


class AuthenticationError(LinkedInError):
    """Raised when authentication fails or session is invalid."""
    pass


class ScrapingError(LinkedInError):
    """Raised when scraping fails after retries."""
    pass


def async_retry(max_attempts: int = 3, base_delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


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
        self._storage_state_path = cookies_path.parent / "storage_state.json"
        logger.debug(f"Initialized LinkedInBrowser with cookies path: {cookies_path}")

    async def __aenter__(self) -> "LinkedInBrowser":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def start(self, headless: bool = True) -> None:
        """Start the browser and load session state if available."""
        logger.info(f"Starting browser (headless={headless})")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Anti-detection: random viewport and user agent each session
        viewport = random_viewport()
        user_agent = random.choice(USER_AGENTS)
        logger.debug(f"Using viewport {viewport['width']}x{viewport['height']}, UA: {user_agent[:50]}...")

        # Load full storage state (cookies + localStorage) if available
        storage_state = None
        if self._storage_state_path.exists():
            storage_state = str(self._storage_state_path)
            logger.info(f"Loading storage state from {self._storage_state_path}")

        self._context = await self._browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/New_York",
            storage_state=storage_state,
        )
        self._page = await self._context.new_page()

        # Fall back to cookies-only if no storage state
        if not storage_state and self._cookies_path.exists():
            await self._load_cookies()
            logger.info("Loaded existing cookies (no storage state found)")
        elif not storage_state:
            logger.info("No cookies or storage state found, will need to authenticate")

    async def stop(self) -> None:
        """Close browser and cleanup resources."""
        logger.info("Stopping browser")
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
        try:
            with open(self._cookies_path, "r") as f:
                cookies = json.load(f)
            await self._context.add_cookies(cookies)
            logger.debug(f"Loaded {len(cookies)} cookies from {self._cookies_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cookies file: {e}")
            raise LinkedInError(f"Invalid cookies file: {e}")

    async def _save_cookies(self) -> None:
        """Save current cookies and full storage state to files."""
        self._cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies = await self._context.cookies()
        with open(self._cookies_path, "w") as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Saved {len(cookies)} cookies to {self._cookies_path}")

        # Also save full storage state (cookies + localStorage + sessionStorage)
        await self._context.storage_state(path=str(self._storage_state_path))
        logger.info(f"Saved storage state to {self._storage_state_path}")

    async def _human_scroll(self, scroll_amount: int = 300, steps: int = 3) -> None:
        """
        Scroll the page in a human-like way with variable speeds.

        Args:
            scroll_amount: Total pixels to scroll
            steps: Number of scroll steps (more = smoother)
        """
        step_size = scroll_amount // steps
        for _ in range(steps):
            # Random scroll amount per step
            scroll = step_size + random.randint(-50, 50)
            await self._page.evaluate(f"window.scrollBy(0, {scroll})")
            # Random pause between scrolls
            await random_delay(0.1, 0.4)

    async def _navigate_with_delay(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to a URL with human-like delays before and after."""
        await random_delay(0.3, 0.8)  # Pre-navigation delay
        await self._page.goto(url, wait_until=wait_until, timeout=15000)
        await random_delay(0.5, 1.2)  # Post-navigation delay (reading time)

    async def is_logged_in(self) -> bool:
        """Check if we have a valid authenticated session."""
        logger.debug("Checking login status...")
        try:
            await self._navigate_with_delay(self.FEED_URL)
        except PlaywrightTimeout:
            logger.warning("Timeout loading feed page")
            return False

        current_url = self._page.url
        logger.debug(f"Current URL after navigation: {current_url}")

        if "/login" in current_url or "/checkpoint" in current_url:
            logger.info("Not logged in - redirected to login/checkpoint")
            return False

        feed_indicator = await self._page.query_selector("div.feed-shared-update-v2")
        is_logged = feed_indicator is not None
        logger.info(f"Login status: {'authenticated' if is_logged else 'not authenticated'}")
        return is_logged

    async def get_own_profile_url(self) -> str | None:
        """Get the authenticated user's own profile URL from the nav bar."""
        try:
            # The profile link in the nav bar points to the user's own profile
            me_link = await self._page.query_selector(
                'a[href*="/in/"][class*="global-nav"],'
                'a[href*="/in/"].ember-view.block,'
                'img[alt*="Photo of"]'
            )
            if me_link:
                href = await me_link.evaluate('el => el.closest("a")?.href || el.parentElement?.href')
                if href and "/in/" in href:
                    logger.debug(f"Own profile URL: {href}")
                    return href

            # Fallback: look for the "Me" menu link
            me_nav = await self._page.query_selector('a[href*="/in/"][data-control-name="identity_welcome_message"]')
            if me_nav:
                href = await me_nav.get_attribute("href")
                if href:
                    return href if href.startswith("http") else f"{self.LINKEDIN_BASE_URL}{href}"

        except Exception as e:
            logger.debug(f"Could not get own profile URL: {e}")

        return None

    async def manual_login(self) -> bool:
        """
        Open browser in headed mode for manual login.
        Call this once to establish initial session.
        Returns True if login successful and cookies saved.
        """
        logger.info("Starting manual login process")
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
            logger.info("Manual login successful, cookies saved")
            return True

        logger.error("Manual login verification failed")
        return False

    @async_retry(max_attempts=3, base_delay=2.0, exceptions=(PlaywrightTimeout, ScrapingError))
    async def scrape_connections(self, max_items: int = 50) -> list[dict]:
        """
        Scrape the connections list page with pagination.

        Args:
            max_items: Maximum number of connections to scrape (default 50)

        Returns list of dicts with: name, headline, profile_url
        """
        logger.info(f"Starting connections scrape (max {max_items} items)")

        # Navigate with human-like delays
        await self._navigate_with_delay(self.CONNECTIONS_URL)

        try:
            await self._page.wait_for_selector('div[data-view-name="connections-list"]', timeout=10000)
        except PlaywrightTimeout:
            logger.error("Connections list container not found")
            raise ScrapingError("Could not find connections list on page")

        connections = []
        seen_urls = set()
        no_new_items_count = 0
        max_scroll_attempts = 20  # Safety limit

        for scroll_attempt in range(max_scroll_attempts):
            # Query all figures currently on page
            figures = await self._page.query_selector_all('figure[aria-label*="profile picture"]')
            initial_count = len(connections)

            for figure in figures:
                if len(connections) >= max_items:
                    break

                try:
                    aria_label = await figure.get_attribute('aria-label')
                    if not aria_label or "profile picture" not in aria_label:
                        continue

                    # Extract name by removing the "...s profile picture" suffix
                    idx = aria_label.find("s profile picture")
                    if idx > 0:
                        name = aria_label[:idx-1].strip()
                    else:
                        name = aria_label.replace("profile picture", "").strip()

                    # Clean up any trailing apostrophes (various unicode apostrophes)
                    name = name.rstrip("''\u2019")

                    # Find the parent link to get the URL
                    parent_link = await figure.evaluate('el => el.closest("a")?.href')
                    if not parent_link or parent_link in seen_urls:
                        continue

                    seen_urls.add(parent_link)

                    connections.append({
                        "name": name,
                        "headline": "",
                        "profile_url": parent_link,
                    })
                except Exception as e:
                    logger.debug(f"Error extracting from figure: {e}")
                    continue

            # Check if we've reached our limit
            if len(connections) >= max_items:
                logger.info(f"Reached max items limit ({max_items})")
                break

            # Check if we found new items this scroll
            new_items = len(connections) - initial_count
            if new_items == 0:
                no_new_items_count += 1
                if no_new_items_count >= 3:
                    logger.info("No new items found after 3 scroll attempts, stopping")
                    break
            else:
                no_new_items_count = 0
                logger.debug(f"Found {new_items} new connections (total: {len(connections)})")

            # Scroll to load more
            await self._human_scroll(800, steps=4)
            await random_delay(1.5, 3.0)

        logger.info(f"Scraped {len(connections)} connections")
        return connections

    @async_retry(max_attempts=3, base_delay=2.0, exceptions=(PlaywrightTimeout, ScrapingError))
    async def scrape_followers(self, max_items: int = 50) -> list[dict]:
        """
        Scrape the followers list page with pagination.

        Args:
            max_items: Maximum number of followers to scrape (default 50)

        Returns list of dicts with: name, headline, profile_url
        """
        logger.info(f"Starting followers scrape (max {max_items} items)")

        # Navigate with human-like delays
        await self._navigate_with_delay(self.FOLLOWERS_URL)

        followers = []
        seen_urls = set()
        no_new_items_count = 0
        max_scroll_attempts = 20  # Safety limit

        for scroll_attempt in range(max_scroll_attempts):
            # Query all cards currently on page
            cards = await self._page.query_selector_all(
                'div[data-view-name="search-entity-result-universal-template"]'
            )
            initial_count = len(followers)

            for card in cards:
                if len(followers) >= max_items:
                    break

                follower = await self._extract_follower_card(card)
                if follower and follower["profile_url"] not in seen_urls:
                    seen_urls.add(follower["profile_url"])
                    followers.append(follower)

            # Check if we've reached our limit
            if len(followers) >= max_items:
                logger.info(f"Reached max items limit ({max_items})")
                break

            # Check if we found new items this scroll
            new_items = len(followers) - initial_count
            if new_items == 0:
                no_new_items_count += 1
                if no_new_items_count >= 3:
                    logger.info("No new items found after 3 scroll attempts, stopping")
                    break
            else:
                no_new_items_count = 0
                logger.debug(f"Found {new_items} new followers (total: {len(followers)})")

            # Scroll to load more
            await self._human_scroll(800, steps=4)
            await random_delay(1.5, 3.0)

        logger.info(f"Scraped {len(followers)} followers")
        return followers

    async def _extract_follower_card(self, card) -> dict | None:
        """Extract data from a single follower card element."""
        try:
            # Find ALL profile links - there are usually two: image link and name link
            link_els = await card.query_selector_all('a[href*="/in/"]')
            if not link_els:
                logger.debug("No profile link found in follower card")
                return None

            profile_url = None
            name = ""

            # The second link typically contains just the name text
            for link_el in link_els:
                href = await link_el.get_attribute("href")
                if href and "/in/" in href:
                    if not profile_url:
                        profile_url = href

                    # Get the text content
                    text = (await link_el.inner_text()).strip()

                    # Skip if it's the image link (contains Status text or is empty)
                    if text and "Status is" not in text and len(text) > 1:
                        name = text
                        break

            # Headline - look for the subtitle/occupation text
            headline = ""
            headline_selectors = [
                'div.t-14.t-black.t-normal',
                'span.t-14.t-black.t-normal',
                'div.entity-result__primary-subtitle',
                'span.entity-result__primary-subtitle',
                'div.linked-area div.t-14',
            ]
            for selector in headline_selectors:
                headline_el = await card.query_selector(selector)
                if headline_el:
                    headline = (await headline_el.inner_text()).strip()
                    break

            if not profile_url:
                logger.debug("No profile URL found")
                return None

            if not name:
                logger.debug(f"Empty name for profile: {profile_url}")
                return None

            # Final cleanup - remove "Status is reachable" if it got through
            if "Status is" in name:
                logger.debug(f"Name contains status text, skipping: {name}")
                return None

            return {
                "name": name,
                "headline": headline,
                "profile_url": profile_url if profile_url.startswith("http") else f"{self.LINKEDIN_BASE_URL}{profile_url}",
            }
        except Exception as e:
            logger.debug(f"Error extracting follower card: {e}")
            return None

    @async_retry(max_attempts=2, base_delay=2.0, exceptions=(PlaywrightTimeout, ScrapingError))
    async def scrape_profile(self, profile_url: str) -> dict | None:
        """
        Scrape detailed information from a LinkedIn profile page.

        Args:
            profile_url: Full URL to the LinkedIn profile

        Returns dict with: name, headline, location, about, company, experience, education
        """
        logger.info(f"Scraping profile: {profile_url}")

        # Navigate with human-like delays
        await self._navigate_with_delay(profile_url)

        # Scroll down to load lazy content
        for _ in range(2):
            await self._human_scroll(800, steps=2)
            await random_delay(0.3, 0.6)

        try:
            profile = {}

            # Name - try multiple selectors
            name = ""
            for sel in ['h1.text-heading-xlarge', 'h1[class*="heading"]', 'h1']:
                el = await self._page.query_selector(sel)
                if el:
                    name = (await el.inner_text()).strip()
                    if name:
                        break
            profile["name"] = name

            # Headline - below the name
            headline = ""
            for sel in [
                'div.text-body-medium.break-words',
                'div[class*="text-body-medium"]',
                'div[data-generated-suggestion-target]',
                '.pv-text-details__left-panel div:nth-child(2)',
            ]:
                el = await self._page.query_selector(sel)
                if el:
                    headline = (await el.inner_text()).strip()
                    if headline:
                        break
            profile["headline"] = headline

            # Location
            location = ""
            for sel in [
                'span.text-body-small.inline.t-black--light.break-words',
                'span[class*="text-body-small"][class*="break-words"]',
                '.pv-text-details__left-panel span[class*="text-body-small"]',
            ]:
                el = await self._page.query_selector(sel)
                if el:
                    location = (await el.inner_text()).strip()
                    if location:
                        break
            profile["location"] = location

            # About section
            about = ""
            for sel in [
                'section:has(#about) div.display-flex.full-width',
                'section:has(#about) span[class*="visually-hidden"] ~ span',
                'section:has(#about) div[class*="inline-show-more-text"]',
                '#about ~ div',
            ]:
                el = await self._page.query_selector(sel)
                if el:
                    about = (await el.inner_text()).strip()
                    if about:
                        break
            profile["about"] = about[:500]

            # Current company - from the intro card
            company = ""
            for sel in [
                'div.inline-show-more-text--is-collapsed button[aria-label*="Current company"]',
                'button[aria-label*="Current company"]',
                'div[aria-label*="Current company"]',
                'section:has(#experience) li:first-child span[aria-hidden="true"]',
            ]:
                el = await self._page.query_selector(sel)
                if el:
                    company = (await el.inner_text()).strip()
                    if company:
                        break
            profile["company"] = company

            # Experience - get list of positions
            experience = []
            exp_items = await self._page.query_selector_all('section:has(#experience) li.artdeco-list__item')
            if not exp_items:
                exp_items = await self._page.query_selector_all('section:has(#experience) li[class*="list__item"]')
            for item in exp_items[:5]:
                try:
                    title_el = await item.query_selector('div.display-flex.flex-wrap span[aria-hidden="true"]')
                    if not title_el:
                        title_el = await item.query_selector('span[aria-hidden="true"]')
                    company_el = await item.query_selector('span.t-14.t-normal span[aria-hidden="true"]')

                    title = (await title_el.inner_text()).strip() if title_el else ""
                    company_name = (await company_el.inner_text()).strip() if company_el else ""

                    if title:
                        experience.append({"title": title, "company": company_name})
                except Exception:
                    continue
            profile["experience"] = experience

            # Education - get list of schools
            education = []
            edu_items = await self._page.query_selector_all('section:has(#education) li.artdeco-list__item')
            if not edu_items:
                edu_items = await self._page.query_selector_all('section:has(#education) li[class*="list__item"]')
            for item in edu_items[:3]:
                try:
                    school_el = await item.query_selector('div.display-flex.flex-wrap span[aria-hidden="true"]')
                    if not school_el:
                        school_el = await item.query_selector('span[aria-hidden="true"]')
                    degree_el = await item.query_selector('span.t-14.t-normal span[aria-hidden="true"]')

                    school = (await school_el.inner_text()).strip() if school_el else ""
                    degree = (await degree_el.inner_text()).strip() if degree_el else ""

                    if school:
                        education.append({"school": school, "degree": degree})
                except Exception:
                    continue
            profile["education"] = education

            profile["profile_url"] = profile_url

            logger.info(f"Scraped profile: {profile.get('name', 'Unknown')} | headline={bool(headline)} | location={bool(location)} | company={bool(company)}")
            return profile

        except Exception as e:
            logger.error(f"Error scraping profile: {e}")
            return None

    async def _human_type(self, text: str, min_delay: float = 0.03, max_delay: float = 0.12) -> None:
        """Type text character by character with random delays to simulate human typing."""
        for char in text:
            await self._page.keyboard.type(char)
            await asyncio.sleep(random.uniform(min_delay, max_delay))

    async def send_connection_request(self, profile_url: str, note: str = "") -> dict:
        """
        Send a connection request to a LinkedIn profile with an optional personalized note.

        Args:
            profile_url: Full URL to the LinkedIn profile
            note: Optional personalized connection note (max 300 chars, will be truncated)

        Returns:
            dict with keys:
                success (bool): Whether the request was sent
                status (str): "sent", "already_connected", "already_pending", or "failed"
                profile_url (str): The profile URL
                error (str | None): Error message if failed
        """
        logger.info(f"Sending connection request to: {profile_url}")

        result = {
            "success": False,
            "status": "failed",
            "profile_url": profile_url,
            "error": None,
        }

        try:
            # Navigate to profile with human-like delays
            await self._navigate_with_delay(profile_url)
            await self._human_scroll(300, steps=2)
            await random_delay(0.5, 1.5)

            # --- Detect current relationship status ---

            # Check if already connected (primary action is "Message")
            message_btn = await self._page.query_selector(
                'main button[aria-label*="Message"]'
            )
            if message_btn and await message_btn.is_visible():
                btn_text = (await message_btn.inner_text()).strip().lower()
                if btn_text == "message":
                    logger.info(f"Already connected: {profile_url}")
                    result["status"] = "already_connected"
                    return result

            # Check if invitation already pending
            pending_btn = await self._page.query_selector(
                'main button[aria-label*="Pending"]'
            )
            if pending_btn and await pending_btn.is_visible():
                logger.info(f"Invitation already pending: {profile_url}")
                result["status"] = "already_pending"
                return result

            # --- Find the Connect button ---

            connect_btn = None

            # Try 1: Direct Connect button with aria-label (most reliable)
            connect_btn = await self._page.query_selector(
                'main button[aria-label*="Invite"][aria-label*="connect"]'
            )
            if connect_btn and not await connect_btn.is_visible():
                connect_btn = None

            # Try 2: Button in the profile actions area with exact text
            if not connect_btn:
                action_buttons = await self._page.query_selector_all(
                    'main section button'
                )
                for btn in action_buttons:
                    btn_text = (await btn.inner_text()).strip()
                    if btn_text == "Connect" and await btn.is_visible():
                        connect_btn = btn
                        break

            # Try 3: Look inside the "More" dropdown
            if not connect_btn:
                logger.debug("Connect button not visible, checking More dropdown")
                more_btn = await self._page.query_selector(
                    'main button[aria-label="More actions"]'
                )
                if more_btn and await more_btn.is_visible():
                    await random_delay(0.3, 0.8)
                    await more_btn.click()
                    await random_delay(0.5, 1.0)

                    # Find "Connect" option in the dropdown menu
                    dropdown_items = await self._page.query_selector_all(
                        'div[role="listbox"] div[role="option"], '
                        'ul[role="menu"] li, '
                        'div.artdeco-dropdown__content li'
                    )
                    for item in dropdown_items:
                        item_text = (await item.inner_text()).strip()
                        if "Connect" in item_text and "Connected" not in item_text:
                            connect_btn = item
                            logger.debug("Found Connect in More dropdown")
                            break

                    # Close dropdown if Connect not found there
                    if not connect_btn:
                        await self._page.keyboard.press("Escape")
                        await random_delay(0.2, 0.5)

            if not connect_btn:
                logger.warning(f"Connect button not found: {profile_url}")
                await self.save_debug_snapshot("connect_btn_not_found")
                result["error"] = "Connect button not found on profile"
                return result

            # --- Click Connect ---

            await random_delay(0.5, 1.0)
            await connect_btn.click()
            await random_delay(1.0, 2.0)

            # --- Handle the connection modal ---

            if note:
                # Truncate to LinkedIn's 300-character limit
                note = note[:300]

                # Look for "Add a note" button in the modal
                add_note_btn = None
                add_note_selectors = [
                    'button[aria-label="Add a note"]',
                    'button:has-text("Add a note")',
                ]
                for selector in add_note_selectors:
                    add_note_btn = await self._page.query_selector(selector)
                    if add_note_btn and await add_note_btn.is_visible():
                        break
                    add_note_btn = None

                if add_note_btn:
                    await random_delay(0.3, 0.8)
                    await add_note_btn.click()
                    await random_delay(0.5, 1.0)

                    # Find the textarea and type the note like a human
                    textarea = None
                    textarea_selectors = [
                        'textarea[name="message"]',
                        'textarea#custom-message',
                        'textarea',
                    ]
                    for selector in textarea_selectors:
                        textarea = await self._page.query_selector(selector)
                        if textarea and await textarea.is_visible():
                            break
                        textarea = None

                    if textarea:
                        await textarea.click()
                        await random_delay(0.2, 0.5)
                        await self._human_type(note)
                        await random_delay(0.5, 1.0)
                    else:
                        logger.warning("Note textarea not found")
                        await self.save_debug_snapshot("note_textarea_not_found")
                        await self._page.keyboard.press("Escape")
                        result["status"] = "note_not_supported"
                        result["error"] = "Could not add note — textarea not found. Send manually."
                        return result
                else:
                    logger.warning("'Add a note' button not found")
                    await self._page.keyboard.press("Escape")
                    result["status"] = "note_not_supported"
                    result["error"] = "Could not add note — button not found. Send manually with the note below."
                    return result

            # --- Click Send ---

            send_btn = None
            send_selectors = [
                'button[aria-label="Send invitation"]',
                'button[aria-label="Send now"]',
                'button:has-text("Send")',
            ]
            for selector in send_selectors:
                send_btn = await self._page.query_selector(selector)
                if send_btn and await send_btn.is_visible():
                    break
                send_btn = None

            if not send_btn:
                logger.warning("Send button not found in modal")
                await self.save_debug_snapshot("send_btn_not_found")
                # Try pressing Escape to close modal
                await self._page.keyboard.press("Escape")
                result["error"] = "Send button not found in modal"
                return result

            await random_delay(0.3, 0.8)
            await send_btn.click()
            await random_delay(1.5, 3.0)

            logger.info(f"Connection request sent to: {profile_url}")
            result["success"] = True
            result["status"] = "sent"
            return result

        except PlaywrightTimeout as e:
            logger.error(f"Timeout sending connection request: {e}")
            await self.save_debug_snapshot("connect_timeout")
            result["error"] = f"Timeout: {e}"
            return result
        except Exception as e:
            logger.error(f"Error sending connection request: {e}")
            await self.save_debug_snapshot("connect_error")
            result["error"] = str(e)
            return result

    async def save_debug_snapshot(self, name: str) -> Path:
        """
        Save current page HTML and screenshot for debugging.
        Returns the path to the debug directory.
        """
        debug_dir = self._cookies_path.parent
        debug_dir.mkdir(parents=True, exist_ok=True)

        html_path = debug_dir / f"{name}_debug.html"
        png_path = debug_dir / f"{name}_debug.png"

        html = await self._page.content()
        with open(html_path, "w") as f:
            f.write(html)

        await self._page.screenshot(path=png_path, full_page=True)

        logger.info(f"Saved debug snapshot to {debug_dir}/{name}_debug.*")
        return debug_dir

    @property
    def page(self) -> Page:
        """Get the current page. Raises if browser not started."""
        if self._page is None:
            raise RuntimeError("Browser not started. Call start() or use async with.")
        return self._page
