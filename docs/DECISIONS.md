# Decision Log

This document records key technical decisions made during development, including context, alternatives considered, and reasoning.

---

## ADR-001: Cookie-Based Authentication

**Date**: January 2026

**Status**: Accepted

### Context

We need to authenticate with LinkedIn to access profile data. Options:
1. Store username/password and automate login
2. Use LinkedIn API (official)
3. Cookie-based authentication (manual login once)

### Decision

Use cookie-based authentication with manual login.

### Reasoning

- **Security**: No credentials stored in code or config files
- **Reliability**: Avoids CAPTCHAs and 2FA automation complexity
- **Simplicity**: Playwright makes cookie persistence easy
- **Legal**: LinkedIn API has strict access requirements

### Implementation

```python
# Manual login (once)
await browser.manual_login()  # Opens browser, user logs in
# Cookies saved to playwright-data/cookies.json

# Subsequent runs
cookies = load_cookies()
context.add_cookies(cookies)  # Session restored
```

### Trade-offs

- Requires manual intervention for first login
- Cookies expire (need to re-login periodically)
- Cannot run in fully headless CI/CD

---

## ADR-002: Playwright Over Selenium

**Date**: January 2026

**Status**: Accepted

### Context

Need browser automation for LinkedIn scraping. Options:
1. Selenium (traditional choice)
2. Playwright (modern alternative)
3. Puppeteer (Node.js focused)

### Decision

Use Playwright with Python async API.

### Reasoning

- **Async native**: Better performance with `asyncio`
- **Auto-wait**: Built-in waiting for elements
- **Modern API**: Cleaner than Selenium
- **Browser install**: Single command (`playwright install`)
- **Python support**: First-class, not a port

### Trade-offs

- Smaller community than Selenium
- Fewer tutorials/Stack Overflow answers
- Learning curve for Selenium users

---

## ADR-003: Figure aria-label for Name Extraction

**Date**: January 2026

**Status**: Accepted

### Context

LinkedIn's DOM uses hashed CSS class names (e.g., `a.f89e0a9a`) that change frequently. Need a stable way to extract names from connection cards.

### Alternatives Tried

1. **Hashed class selectors** (`a.f89e0a9a`): Broke when LinkedIn updated
2. **Nested link text** (`p a`): Elements appeared empty in headless mode
3. **Direct inner_text()**: Returned empty strings

### Decision

Extract names from `<figure aria-label="Name's profile picture">`.

### Reasoning

- **Accessibility attributes are stable**: LinkedIn maintains them for screen readers
- **Always present**: Every profile picture has this attribute
- **Contains full name**: Including titles like "MBA"

### Implementation

```python
figures = await page.query_selector_all('figure[aria-label*="profile picture"]')
for figure in figures:
    aria_label = await figure.get_attribute('aria-label')
    # "John Doe's profile picture" -> "John Doe"
    name = aria_label.replace("s profile picture", "")[:-1]  # Handle apostrophe
```

### Gotcha: Unicode Apostrophes

LinkedIn uses curly apostrophes (`'` U+2019) not straight ones (`'`). Solution:

```python
idx = aria_label.find("s profile picture")
name = aria_label[:idx-1].strip()  # Works with any apostrophe
```

---

## ADR-004: Pagination via Scroll Loop

**Date**: January 2026

**Status**: Accepted

### Context

LinkedIn uses infinite scroll. The initial page load only shows ~10 items. Need to load more for users with many connections.

### Decision

Implement scroll-based pagination with:
- Maximum items limit (default 50)
- Detection of "no new items" (stop after 3 attempts)
- Safety limit (max 20 scroll attempts)

### Implementation

```python
for scroll_attempt in range(max_scroll_attempts):
    items = await page.query_selector_all(selector)
    new_count = extract_new_items(items)

    if len(all_items) >= max_items:
        break  # Reached limit

    if new_count == 0:
        no_new_count += 1
        if no_new_count >= 3:
            break  # No more items

    await human_scroll(800)  # Trigger lazy load
    await random_delay(1.5, 3.0)
```

### Trade-offs

- Slower than API access
- Can't get exact counts upfront
- Requires anti-detection delays

---

## ADR-005: Anti-Detection Strategy

**Date**: January 2026

**Status**: Accepted

### Context

LinkedIn detects and blocks automated browsers. Need to appear human-like.

### Decision

Implement multiple anti-detection measures:

1. **User Agent Rotation**
   ```python
   USER_AGENTS = [
       "Mozilla/5.0 (Macintosh...) Chrome/120...",
       "Mozilla/5.0 (Windows...) Chrome/119...",
       # 5 total variations
   ]
   user_agent = random.choice(USER_AGENTS)
   ```

2. **Viewport Randomization**
   ```python
   width = random.choice([1280, 1366, 1440]) + random.randint(-20, 20)
   height = random.choice([720, 800, 900]) + random.randint(-20, 20)
   ```

3. **Random Delays**
   ```python
   async def random_delay(min_s=0.5, max_s=2.0):
       await asyncio.sleep(random.uniform(min_s, max_s))
   ```

4. **Human-like Scrolling**
   ```python
   async def human_scroll(amount, steps=3):
       for _ in range(steps):
           scroll = amount/steps + random.randint(-50, 50)
           await page.evaluate(f"window.scrollBy(0, {scroll})")
           await random_delay(0.1, 0.4)
   ```

### Trade-offs

- Slower scraping (necessary delays)
- More code complexity
- Not 100% detection-proof

---

## ADR-006: Retry with Exponential Backoff

**Date**: January 2026

**Status**: Accepted

### Context

Network issues and LinkedIn rate limiting can cause transient failures.

### Decision

Implement async retry decorator with exponential backoff.

### Implementation

```python
def async_retry(max_attempts=3, base_delay=1.0, exceptions=(Exception,)):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        delay += random.uniform(0, 1)  # Jitter
                        await asyncio.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator
```

### Usage

```python
@async_retry(max_attempts=3, base_delay=2.0, exceptions=(TimeoutError,))
async def scrape_connections():
    ...
```

---

## ADR-007: Structured Logging

**Date**: January 2026

**Status**: Accepted

### Context

Need visibility into scraping operations for debugging and monitoring.

### Decision

Use Python's `logging` module with structured format.

### Implementation

```python
logger = logging.getLogger(__name__)

# In code
logger.info(f"Starting connections scrape (max {max_items} items)")
logger.debug(f"Found {len(items)} items")
logger.warning("No new items found")
logger.error(f"Failed to scrape: {e}")
```

### Output Format

```
2026-01-27 22:15:00 - app.services.linkedin_browser - INFO - Starting connections scrape
```

---

## ADR-008: Custom Exception Hierarchy

**Date**: January 2026

**Status**: Accepted

### Context

Need to distinguish between different error types for proper handling.

### Decision

Create custom exception classes:

```python
class LinkedInError(Exception):
    """Base exception for LinkedIn-related errors."""
    pass

class AuthenticationError(LinkedInError):
    """Session invalid or login required."""
    pass

class ScrapingError(LinkedInError):
    """Failed to scrape after retries."""
    pass
```

### Usage

```python
try:
    await scrape_connections()
except AuthenticationError:
    await manual_login()  # Re-authenticate
except ScrapingError:
    save_debug_snapshot()  # Debug
```

---

## Future Decisions Pending

- **Database choice**: Supabase vs local SQLite for development
- **Message queue**: For background scraping jobs
- **Rate limiting strategy**: Per-day limits on profiles/messages
- **AI prompt engineering**: How to structure Claude prompts
