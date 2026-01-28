# Web Scraping Series: Part 3 - Cookie Authentication

*Secure Login Without Storing Credentials*

---

## Introduction

LinkedIn has strong anti-automation measures. Automating the login form triggers CAPTCHAs, 2FA challenges, and account flags. Instead, we'll:

1. Open a browser window for manual login
2. Capture the session cookies
3. Reuse cookies for future sessions

**Why this approach:**
- No credentials in code or config
- Handles 2FA naturally (user does it manually)
- More reliable than form automation
- Lower detection risk

---

## The Authentication Flow

```
First Run:
┌─────────────────────────────────────────────┐
│ 1. Open browser (headed mode)               │
│ 2. Navigate to LinkedIn login               │
│ 3. User logs in manually                    │
│ 4. User completes 2FA if prompted           │
│ 5. Script captures cookies                  │
│ 6. Save cookies to file                     │
└─────────────────────────────────────────────┘

Subsequent Runs:
┌─────────────────────────────────────────────┐
│ 1. Load cookies from file                   │
│ 2. Navigate to LinkedIn                     │
│ 3. Already logged in!                       │
└─────────────────────────────────────────────┘
```

---

## Step 1: Add URL Constants

```python
class LinkedInBrowser:
    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    FEED_URL = "https://www.linkedin.com/feed/"
    LOGIN_URL = "https://www.linkedin.com/login"
```

---

## Step 2: Check Login Status

We need to verify if the loaded cookies are still valid:

```python
async def is_logged_in(self) -> bool:
    """Check if we have a valid authenticated session."""
    await self._page.goto(self.FEED_URL, wait_until="domcontentloaded")
    current_url = self._page.url

    # If redirected to login, we're not authenticated
    if "/login" in current_url or "/checkpoint" in current_url:
        return False

    # Look for an element that only appears when logged in
    feed_indicator = await self._page.query_selector("div.feed-shared-update-v2")
    return feed_indicator is not None
```

**How it works:**
1. Navigate to the feed (requires login)
2. Check if we were redirected to login page
3. Check if feed content is visible

---

## Step 3: Manual Login Flow

```python
async def manual_login(self) -> bool:
    """
    Open browser in headed mode for manual login.
    Call this once to establish initial session.
    Returns True if login successful and cookies saved.
    """
    # Restart browser in headed mode (visible)
    await self.stop()
    await self.start(headless=False)

    # Navigate to login page
    await self._page.goto(self.LOGIN_URL, wait_until="domcontentloaded")

    # Prompt user
    print("=" * 50)
    print("MANUAL LOGIN REQUIRED")
    print("1. Log in to LinkedIn in the browser window")
    print("2. Complete any 2FA if prompted")
    print("3. Wait until you see your feed")
    print("4. Press Enter here when done...")
    print("=" * 50)

    input()  # Wait for user

    # Verify login worked
    if await self.is_logged_in():
        await self._save_cookies()
        print("Cookies saved successfully!")
        return True

    print("Login verification failed. Please try again.")
    return False
```

**Key points:**
- `headless=False` opens a visible browser window
- `input()` pauses until user presses Enter
- Cookies are only saved after verifying login worked

---

## Step 4: Complete Authentication Module

Add to `linkedin_browser.py`:

```python
import json
from pathlib import Path
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeout,
)


class LinkedInBrowser:
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

    # ... (context manager methods from Part 2)

    async def is_logged_in(self) -> bool:
        """Check if we have a valid authenticated session."""
        try:
            await self._page.goto(
                self.FEED_URL,
                wait_until="domcontentloaded",
                timeout=15000
            )
        except PlaywrightTimeout:
            return False

        current_url = self._page.url

        if "/login" in current_url or "/checkpoint" in current_url:
            return False

        feed_indicator = await self._page.query_selector("div.feed-shared-update-v2")
        return feed_indicator is not None

    async def manual_login(self) -> bool:
        """Open browser for manual login, save cookies on success."""
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

        print("Login verification failed.")
        return False
```

---

## Step 5: Usage Script

Create `backend/test_auth.py`:

```python
import asyncio
from app.services.linkedin_browser import LinkedInBrowser


async def main():
    async with LinkedInBrowser() as browser:
        if not await browser.is_logged_in():
            print("Not logged in. Starting manual login...")
            success = await browser.manual_login()
            if not success:
                print("Login failed. Exiting.")
                return

        print("Successfully authenticated!")
        print(f"Current URL: {browser.page.url}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Running It

### First Time (No Cookies)

```bash
uv run python test_auth.py
```

Output:
```
Not logged in. Starting manual login...
==================================================
MANUAL LOGIN REQUIRED
1. Log in to LinkedIn in the browser window
2. Complete any 2FA if prompted
3. Wait until you see your feed
4. Press Enter here when done...
==================================================
```

1. A browser window opens
2. Log in to LinkedIn
3. Complete 2FA if prompted
4. Wait for your feed to load
5. Press Enter in the terminal

```
Cookies saved successfully!
Successfully authenticated!
```

### Subsequent Runs

```bash
uv run python test_auth.py
```

Output:
```
Successfully authenticated!
Current URL: https://www.linkedin.com/feed/
```

No browser window—cookies loaded automatically!

---

## Cookie File

Check `playwright-data/cookies.json`:

```json
[
  {
    "name": "li_at",
    "value": "AQEDAQNj...",
    "domain": ".linkedin.com",
    "path": "/",
    "expires": 1766000000,
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
  },
  {
    "name": "JSESSIONID",
    "value": "ajax:123...",
    ...
  }
  // ... more cookies
]
```

**Important:** Add `cookies.json` to `.gitignore`!

---

## Security Considerations

1. **Never commit cookies**: Add to `.gitignore`
2. **Cookies expire**: LinkedIn sessions last ~1 year
3. **One session per cookie file**: Don't share across accounts
4. **Revoke if compromised**: Log out from LinkedIn to invalidate

---

## Handling Expired Cookies

```python
async def ensure_authenticated(self) -> bool:
    """Ensure we're logged in, prompt for login if needed."""
    if await self.is_logged_in():
        return True

    print("Session expired. Please log in again.")
    return await self.manual_login()
```

---

## Key Takeaways

1. **Manual login is safer** than automating the login form
2. **Cookie persistence** avoids repeated logins
3. **Session validation** detects expired sessions
4. **Security first**: Never store credentials or commit cookies

---

## What's Next

In Part 4, we'll start scraping:
- Connection list extraction
- Handling LinkedIn's DOM structure
- Dealing with lazy-loaded content

---

*Previous: [Part 2 - Playwright Basics](./02-playwright-basics.md)*
*Next: [Part 4 - Scraping Lists](./04-scraping-lists.md)*
