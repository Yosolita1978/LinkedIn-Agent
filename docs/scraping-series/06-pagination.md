# Web Scraping Series: Part 6 - Pagination

*Handling Infinite Scroll and Large Datasets*

---

## Introduction

LinkedIn uses infinite scroll instead of traditional pagination. When you reach the bottom of a list, more items load automatically. This creates challenges:

- No page numbers to iterate
- Need to detect when loading is complete
- Risk of duplicates
- Performance considerations for large lists

**Goal:** Scrape all items from a list, regardless of size, without missing or duplicating entries.

---

## How Infinite Scroll Works

```
┌─────────────────────────────────┐
│  Visible Viewport               │
│  ┌───────────────────────────┐  │
│  │ Item 1                    │  │
│  │ Item 2                    │  │
│  │ Item 3                    │  │
│  │ Item 4                    │  │
│  │ Item 5                    │  │
│  └───────────────────────────┘  │
│                                 │
│  ─ ─ ─ Loading Trigger ─ ─ ─   │
│                                 │
│  (Items 6-10 load when you     │
│   scroll here)                  │
└─────────────────────────────────┘
```

When the user scrolls near the bottom:
1. JavaScript detects the scroll position
2. An API call fetches the next batch
3. New items are appended to the DOM

---

## The Pagination Strategy

Our approach:

1. **Scroll down** to trigger loading
2. **Wait** for new content
3. **Extract** all visible items
4. **Track** seen items to avoid duplicates
5. **Detect** when no new items appear
6. **Repeat** until done or limit reached

```python
async def scrape_with_pagination(self, max_items: int = 50) -> list[dict]:
    all_items = []
    seen_urls = set()

    while len(all_items) < max_items:
        # Extract current items
        new_items = await self._extract_visible_items(seen_urls)
        all_items.extend(new_items)

        # Scroll to load more
        if not await self._scroll_for_more():
            break  # No more items

    return all_items[:max_items]
```

---

## Implementing Pagination

### Step 1: Track Seen Items

Use a set to track URLs we've already processed:

```python
async def scrape_connections(self, max_items: int = 50) -> list[dict]:
    """Scrape connections with pagination support."""
    await self._navigate_with_delay(self.CONNECTIONS_URL)

    await self._page.wait_for_selector(
        'div[data-view-name="connections-list"]',
        timeout=10000
    )

    connections = []
    seen_urls = set()
    no_new_items_count = 0
    max_scroll_attempts = 20  # Safety limit

    for scroll_attempt in range(max_scroll_attempts):
        # Extract items from current view
        new_connections = await self._extract_connections(seen_urls)

        if new_connections:
            connections.extend(new_connections)
            no_new_items_count = 0

            if len(connections) >= max_items:
                break
        else:
            no_new_items_count += 1
            if no_new_items_count >= 3:
                # No new items after 3 scrolls = we're done
                break

        # Scroll to load more
        await self._human_scroll(500, steps=3)
        await random_delay(1.5, 3.0)

    return connections[:max_items]
```

### Step 2: Extract Without Duplicates

The `seen_urls` set prevents duplicates:

```python
async def _extract_connections(self, seen_urls: set) -> list[dict]:
    """Extract connections not yet seen."""
    figures = await self._page.query_selector_all(
        'figure[aria-label*="profile picture"]'
    )

    new_connections = []

    for figure in figures:
        aria_label = await figure.get_attribute('aria-label')
        if not aria_label:
            continue

        # Extract name from aria-label
        idx = aria_label.find("s profile picture")
        if idx > 0:
            name = aria_label[:idx-1].strip()
        else:
            continue

        # Get profile URL
        parent_link = await figure.evaluate('el => el.closest("a")?.href')

        # Skip if already seen
        if not parent_link or parent_link in seen_urls:
            continue

        seen_urls.add(parent_link)
        new_connections.append({
            "name": name,
            "profile_url": parent_link,
        })

    return new_connections
```

---

## Detecting End of List

Three signals that we've reached the end:

### 1. No New Items After Scrolling

```python
no_new_items_count = 0

# In the loop:
if new_connections:
    no_new_items_count = 0
else:
    no_new_items_count += 1
    if no_new_items_count >= 3:
        break  # Done
```

### 2. "End of List" Element

Some pages show an explicit end marker:

```python
end_marker = await self._page.query_selector(
    'div[data-view-name="end-of-list"]'
)
if end_marker:
    break
```

### 3. Scroll Position Unchanged

If scrolling doesn't change position, we're at the bottom:

```python
async def _is_at_bottom(self) -> bool:
    """Check if we've scrolled to the bottom."""
    result = await self._page.evaluate("""
        () => {
            const scrollTop = window.scrollY;
            const scrollHeight = document.documentElement.scrollHeight;
            const clientHeight = window.innerHeight;
            return scrollTop + clientHeight >= scrollHeight - 100;
        }
    """)
    return result
```

---

## Safety Limits

Always have limits to prevent infinite loops:

```python
# Maximum items to scrape
max_items: int = 50

# Maximum scroll attempts
max_scroll_attempts: int = 20

# Stop after N empty scrolls
max_empty_scrolls: int = 3
```

**Why limits matter:**
- LinkedIn may have 1000+ connections
- Each scroll takes time (delays for anti-detection)
- Memory usage grows with list size
- Reduces detection risk

---

## Complete Pagination Code

```python
async def scrape_connections(self, max_items: int = 50) -> list[dict]:
    """
    Scrape connections with pagination.

    Args:
        max_items: Maximum connections to scrape (default 50)

    Returns:
        List of connection dictionaries with name and profile_url
    """
    logger.info(f"Starting connection scrape (max: {max_items})")

    await self._navigate_with_delay(self.CONNECTIONS_URL)

    await self._page.wait_for_selector(
        'div[data-view-name="connections-list"]',
        timeout=10000
    )

    connections = []
    seen_urls = set()
    no_new_items_count = 0
    max_scroll_attempts = 20

    for scroll_attempt in range(max_scroll_attempts):
        logger.debug(f"Scroll attempt {scroll_attempt + 1}/{max_scroll_attempts}")

        # Extract visible items
        new_connections = await self._extract_connections(seen_urls)

        if new_connections:
            connections.extend(new_connections)
            no_new_items_count = 0
            logger.info(f"Found {len(new_connections)} new, total: {len(connections)}")

            if len(connections) >= max_items:
                logger.info(f"Reached max_items limit ({max_items})")
                break
        else:
            no_new_items_count += 1
            logger.debug(f"No new items ({no_new_items_count}/3)")

            if no_new_items_count >= 3:
                logger.info("No more items to load")
                break

        # Scroll with human-like behavior
        await self._human_scroll(500, steps=3)
        await random_delay(1.5, 3.0)

    result = connections[:max_items]
    logger.info(f"Scrape complete: {len(result)} connections")
    return result
```

---

## Testing Pagination

```python
async def main():
    async with LinkedInBrowser() as browser:
        if not await browser.is_logged_in():
            print("Not logged in")
            return

        # Test with small limit first
        connections = await browser.scrape_connections(max_items=10)
        print(f"Found {len(connections)} connections")

        # Then try larger
        connections = await browser.scrape_connections(max_items=50)
        print(f"Found {len(connections)} connections")
```

---

## Performance Considerations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Anti-detection delays | ~2-3 sec per scroll | Accept slower speed for safety |
| Memory usage | Grows with items | Set reasonable max_items |
| Network requests | LinkedIn may throttle | Add longer delays between sessions |
| Session duration | Long sessions look suspicious | Limit to 50-100 items per run |

**Recommendation:** Scrape in batches across multiple sessions rather than one long session.

---

## Key Takeaways

1. **Track seen items** with a set to avoid duplicates
2. **Detect end of list** by counting empty scroll attempts
3. **Use safety limits** to prevent infinite loops
4. **Add delays** between scroll operations
5. **Log progress** to monitor scraping behavior

---

## What's Next

In Part 7, we'll extract detailed profile information:
- Profile page navigation
- Experience and education extraction
- Handling varying page structures

---

*Previous: [Part 5 - Anti-Detection](./05-anti-detection.md)*
*Next: [Part 7 - Profile Extraction](./07-profile-extraction.md)*
