# Web Scraping Series: Part 2 - Playwright Basics

*Building the Browser Automation Foundation*

---

## Introduction

In Part 1, we set up our project structure. Now we'll build the core browser automation class that will power all our scraping.

**What we'll cover:**
- Playwright's async API
- The context manager pattern
- Browser lifecycle management
- Cookie persistence

---

## The LinkedInBrowser Class

Our scraper will be encapsulated in a class that:
1. Manages browser lifecycle (start/stop)
2. Handles cookie persistence
3. Provides async context manager support (`async with`)

### Why a Class?

We could write functions, but a class gives us:
- **State management**: Browser, context, and page instances
- **Cleanup guarantees**: `__aexit__` ensures browser closes
- **Encapsulation**: All LinkedIn logic in one place

---

## Step 1: Basic Structure

Create `backend/app/services/linkedin_browser.py`:

```python
import json
from pathlib import Path
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
)


class LinkedInBrowser:
    """Manages Playwright browser for LinkedIn scraping."""

    LINKEDIN_BASE_URL = "https://www.linkedin.com"

    def __init__(self, cookies_path: Path | None = None):
        # Browser instances (set in start())
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        # Cookie storage path
        if cookies_path is None:
            cookies_path = Path(__file__).parents[2] / "playwright-data" / "cookies.json"
        self._cookies_path = cookies_path
```

**Key points:**
- Type hints for all instance variables
- Default cookie path relative to project
- Underscore prefix for "private" attributes

---

## Step 2: Async Context Manager

The context manager pattern ensures cleanup even if exceptions occur:

```python
async def __aenter__(self) -> "LinkedInBrowser":
    """Called when entering 'async with' block."""
    await self.start()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """Called when exiting 'async with' block."""
    await self.stop()
```

**Usage:**
```python
async with LinkedInBrowser() as browser:
    # browser.start() already called
    await browser.do_something()
# browser.stop() automatically called, even if exception raised
```

---

## Step 3: Browser Lifecycle

### Starting the Browser

```python
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

    # Load saved cookies if they exist
    if self._cookies_path.exists():
        await self._load_cookies()
```

**Understanding the hierarchy:**
```
Playwright
└── Browser (Chromium instance)
    └── Context (like an incognito window)
        └── Page (a tab)
```

### Stopping the Browser

```python
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
```

**Important:** Close in reverse order of creation, and set to `None` to prevent reuse.

---

## Step 4: Cookie Persistence

Cookies let us stay logged in across sessions:

### Loading Cookies

```python
async def _load_cookies(self) -> None:
    """Load cookies from file into browser context."""
    with open(self._cookies_path, "r") as f:
        cookies = json.load(f)
    await self._context.add_cookies(cookies)
```

### Saving Cookies

```python
async def _save_cookies(self) -> None:
    """Save current cookies to file."""
    self._cookies_path.parent.mkdir(parents=True, exist_ok=True)
    cookies = await self._context.cookies()
    with open(self._cookies_path, "w") as f:
        json.dump(cookies, f, indent=2)
```

**Cookie format (simplified):**
```json
[
  {
    "name": "li_at",
    "value": "AQEDAQNj...",
    "domain": ".linkedin.com",
    "path": "/",
    "expires": 1735689600,
    "httpOnly": true,
    "secure": true
  }
]
```

The `li_at` cookie is LinkedIn's session token—the key to staying logged in.

---

## Step 5: Page Property

Provide safe access to the page:

```python
@property
def page(self) -> Page:
    """Get the current page. Raises if browser not started."""
    if self._page is None:
        raise RuntimeError("Browser not started. Call start() or use async with.")
    return self._page
```

---

## Complete Code

```python
import json
from pathlib import Path
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
)


class LinkedInBrowser:
    """Manages Playwright browser for LinkedIn scraping."""

    LINKEDIN_BASE_URL = "https://www.linkedin.com"

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
        with open(self._cookies_path, "r") as f:
            cookies = json.load(f)
        await self._context.add_cookies(cookies)

    async def _save_cookies(self) -> None:
        self._cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies = await self._context.cookies()
        with open(self._cookies_path, "w") as f:
            json.dump(cookies, f, indent=2)

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started.")
        return self._page
```

---

## Testing It

Create `backend/test_browser.py`:

```python
import asyncio
from app.services.linkedin_browser import LinkedInBrowser


async def main():
    async with LinkedInBrowser() as browser:
        await browser.page.goto("https://www.linkedin.com")
        print(f"Title: {await browser.page.title()}")
        print(f"URL: {browser.page.url}")


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
uv run python test_browser.py
```

---

## Key Takeaways

1. **Async context managers** ensure cleanup
2. **Cookie persistence** maintains sessions
3. **Browser hierarchy**: Playwright → Browser → Context → Page
4. **Type hints** make the code self-documenting

---

## What's Next

In Part 3, we'll implement:
- LinkedIn authentication flow
- Session validation
- Manual login with cookie capture

---

*Previous: [Part 1 - Project Setup](./01-project-setup.md)*
*Next: [Part 3 - Cookie Authentication](./03-cookie-authentication.md)*
