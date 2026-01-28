# Web Scraping Series: Part 5 - Anti-Detection

*Making Your Scraper Look Human*

---

## Introduction

LinkedIn actively detects and blocks automated browsers. In this part, we'll implement techniques to appear more human-like:

- User agent rotation
- Viewport randomization
- Random delays
- Human-like scrolling

**The goal:** Make our automated browser indistinguishable from a human user.

---

## How Detection Works

LinkedIn looks for patterns:

| Signal | Bot Behavior | Human Behavior |
|--------|-------------|----------------|
| Timing | Fixed delays | Random pauses |
| Viewport | Always 1920x1080 | Varies by device |
| User Agent | Same every time | Different browsers |
| Scrolling | Instant jumps | Smooth, variable |
| Navigation | Immediate clicks | Reading pauses |

---

## Technique 1: User Agent Rotation

Instead of one user agent, use a pool:

```python
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
```

Select randomly at startup:

```python
user_agent = random.choice(USER_AGENTS)
```

**Tips:**
- Use recent Chrome versions (120, 119)
- Include different OS variants
- Update periodically as browsers release new versions

---

## Technique 2: Viewport Randomization

Real screens have different sizes:

```python
def random_viewport() -> dict:
    """Generate a random but realistic viewport size."""
    base_widths = [1280, 1366, 1440, 1536, 1920]
    base_heights = [720, 768, 800, 864, 900, 1080]

    # Add slight variation
    width = random.choice(base_widths) + random.randint(-20, 20)
    height = random.choice(base_heights) + random.randint(-20, 20)

    return {"width": width, "height": height}
```

The `±20` pixels add natural variation without breaking layouts.

---

## Technique 3: Random Delays

Humans don't click instantly. Add variable pauses:

```python
import asyncio
import random


async def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
    """Add a random delay to simulate human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)
```

**Where to use delays:**
- Before navigation
- After page load (reading time)
- Between actions (clicking, scrolling)
- Before extracting data

```python
async def _navigate_with_delay(self, url: str) -> None:
    """Navigate with human-like delays."""
    await random_delay(0.5, 1.5)       # Pre-navigation pause
    await self._page.goto(url, wait_until="domcontentloaded")
    await random_delay(1.0, 2.5)       # Reading time
```

---

## Technique 4: Human-Like Scrolling

Instant scrolling is a dead giveaway. Scroll in steps:

```python
async def _human_scroll(self, scroll_amount: int = 300, steps: int = 3) -> None:
    """Scroll the page in a human-like way with variable speeds."""
    step_size = scroll_amount // steps

    for _ in range(steps):
        # Random scroll amount per step
        scroll = step_size + random.randint(-50, 50)
        await self._page.evaluate(f"window.scrollBy(0, {scroll})")

        # Random pause between scrolls
        await random_delay(0.1, 0.4)
```

**How it works:**
1. Break the scroll into multiple steps
2. Each step has random variation
3. Pause between steps (like a human would)

---

## Applying Anti-Detection

Update the `start()` method:

```python
async def start(self, headless: bool = True) -> None:
    """Start browser with anti-detection measures."""
    self._playwright = await async_playwright().start()
    self._browser = await self._playwright.chromium.launch(headless=headless)

    # Random fingerprint each session
    viewport = random_viewport()
    user_agent = random.choice(USER_AGENTS)

    self._context = await self._browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/New_York",
    )

    self._page = await self._context.new_page()
```

Update scraping methods:

```python
async def scrape_connections(self) -> list[dict]:
    # Navigate with delays
    await self._navigate_with_delay(self.CONNECTIONS_URL)

    await self._page.wait_for_selector(
        'div[data-view-name="connections-list"]',
        timeout=10000
    )

    # Human-like scroll before extraction
    await self._human_scroll(500, steps=3)
    await random_delay(1.0, 2.0)

    # ... extraction logic
```

---

## Complete Anti-Detection Module

```python
import random
import asyncio


# User agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
]


async def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
    """Add a random delay to simulate human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def random_viewport() -> dict:
    """Generate a random but realistic viewport size."""
    base_widths = [1280, 1366, 1440, 1536, 1920]
    base_heights = [720, 768, 800, 864, 900, 1080]

    width = random.choice(base_widths) + random.randint(-20, 20)
    height = random.choice(base_heights) + random.randint(-20, 20)

    return {"width": width, "height": height}


class LinkedInBrowser:
    async def _human_scroll(self, scroll_amount: int = 300, steps: int = 3) -> None:
        """Scroll the page in a human-like way."""
        step_size = scroll_amount // steps
        for _ in range(steps):
            scroll = step_size + random.randint(-50, 50)
            await self._page.evaluate(f"window.scrollBy(0, {scroll})")
            await random_delay(0.1, 0.4)

    async def _navigate_with_delay(self, url: str) -> None:
        """Navigate to a URL with human-like delays."""
        await random_delay(0.5, 1.5)
        await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await random_delay(1.0, 2.5)
```

---

## Timing Guidelines

| Action | Min Delay | Max Delay |
|--------|-----------|-----------|
| Before navigation | 0.5s | 1.5s |
| After page load | 1.0s | 2.5s |
| Between scroll steps | 0.1s | 0.4s |
| Before data extraction | 0.5s | 1.0s |
| Between pagination scrolls | 1.5s | 3.0s |

---

## Trade-offs

**Pros:**
- Much lower detection risk
- More reliable long-term
- Mimics real user behavior

**Cons:**
- Slower scraping (delays add up)
- More code to maintain
- Not 100% detection-proof

---

## Additional Techniques (Advanced)

For even better stealth:

1. **Mouse movements**: Move mouse before clicking
2. **Keyboard typing**: Type with variable speed
3. **Browser fingerprint**: Use Playwright stealth plugins
4. **IP rotation**: Use proxies (different IP each session)
5. **Session limits**: Max requests per session

---

## Key Takeaways

1. **Randomize everything**: User agent, viewport, delays
2. **Scroll like a human**: In steps, not instant jumps
3. **Add reading time**: Pause after navigation
4. **Test your patterns**: Run multiple times, check for blocks

---

## What's Next

In Part 6, we'll implement pagination:
- Handling infinite scroll
- Detecting when to stop
- Avoiding duplicates

---

*Previous: [Part 4 - Scraping Lists](./04-scraping-lists.md)*
*Next: [Part 6 - Pagination](./06-pagination.md)*
