# Web Scraping Series: Part 4 - Scraping Lists

*Extracting Connections and Followers from LinkedIn*

---

## Introduction

Now that we can authenticate, let's scrape actual data. We'll extract:
- Your LinkedIn connections
- Your LinkedIn followers

**Challenges we'll solve:**
- Finding stable selectors (LinkedIn uses hashed CSS classes)
- Handling lazy-loaded content
- Extracting structured data from messy DOM

---

## The Selector Problem

LinkedIn's HTML looks like this:

```html
<a class="f89e0a9a _6abfa7e5 cbbed14b" href="/in/johndoe/">
  John Doe
</a>
```

Those class names (`f89e0a9a`) are hashed and change on every LinkedIn deploy. If we use them as selectors, our scraper breaks constantly.

**Solution:** Find stable attributes:
- `data-*` attributes (e.g., `data-view-name`)
- `aria-*` attributes (for accessibility)
- Semantic structure (e.g., "link inside figure")
- URL patterns (`href*="/in/"`)

---

## Finding Stable Selectors

### Technique 1: Data Attributes

LinkedIn uses `data-view-name` for tracking:

```html
<div data-view-name="connections-list">
  <a data-view-name="connections-profile" href="/in/johndoe/">
```

These are stable because they're used for analytics.

### Technique 2: Accessibility Attributes

Profile pictures have aria-labels:

```html
<figure aria-label="John Doe's profile picture">
  <img src="...">
</figure>
```

This is **gold** for scraping—accessibility attributes rarely change.

### Technique 3: URL Patterns

Profile links always contain `/in/`:

```python
await page.query_selector_all('a[href*="/in/"]')
```

---

## Scraping Connections

### Step 1: Navigate and Wait

```python
CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"

async def scrape_connections(self) -> list[dict]:
    await self._page.goto(self.CONNECTIONS_URL, wait_until="domcontentloaded")

    # Wait for the list container
    await self._page.wait_for_selector(
        'div[data-view-name="connections-list"]',
        timeout=10000
    )
```

### Step 2: Extract Using aria-label

After trying multiple approaches, we found that the most reliable selector is the `<figure>` element's `aria-label`:

```python
figures = await self._page.query_selector_all(
    'figure[aria-label*="profile picture"]'
)

connections = []
for figure in figures:
    aria_label = await figure.get_attribute('aria-label')
    # "John Doe's profile picture" -> "John Doe"

    # Find "s profile picture" and extract name before it
    idx = aria_label.find("s profile picture")
    if idx > 0:
        name = aria_label[:idx-1].strip()

    # Get the profile URL from parent link
    parent_link = await figure.evaluate('el => el.closest("a")?.href')

    connections.append({
        "name": name,
        "profile_url": parent_link,
    })
```

### The Apostrophe Gotcha

LinkedIn uses curly apostrophes (`'`) not straight ones (`'`):

```
"John Doe's profile picture"  # Curly apostrophe (U+2019)
```

Our solution handles any apostrophe by finding the pattern position:

```python
idx = aria_label.find("s profile picture")
name = aria_label[:idx-1].strip()  # Works with any apostrophe
```

---

## Scraping Followers

Followers use a different page structure:

```python
FOLLOWERS_URL = "https://www.linkedin.com/mynetwork/network-manager/people-follow/followers/"

async def scrape_followers(self) -> list[dict]:
    await self._page.goto(self.FOLLOWERS_URL, wait_until="domcontentloaded")

    cards = await self._page.query_selector_all(
        'div[data-view-name="search-entity-result-universal-template"]'
    )

    followers = []
    for card in cards:
        follower = await self._extract_follower_card(card)
        if follower:
            followers.append(follower)

    return followers
```

### Extracting Follower Data

```python
async def _extract_follower_card(self, card) -> dict | None:
    # Find profile links
    link_els = await card.query_selector_all('a[href*="/in/"]')

    profile_url = None
    name = ""

    # There are usually two links: image and name
    for link_el in link_els:
        href = await link_el.get_attribute("href")
        if href and "/in/" in href:
            if not profile_url:
                profile_url = href

            # Get text content
            text = (await link_el.inner_text()).strip()

            # Skip status badges like "Status is reachable"
            if text and "Status is" not in text and len(text) > 1:
                name = text
                break

    # Get headline
    headline = ""
    headline_el = await card.query_selector('div.t-14.t-black.t-normal')
    if headline_el:
        headline = (await headline_el.inner_text()).strip()

    if not profile_url or not name:
        return None

    return {
        "name": name,
        "headline": headline,
        "profile_url": profile_url,
    }
```

---

## Dealing with Noise

LinkedIn cards contain extra text we don't want:

```html
<a href="/in/johndoe/">
  <span class="visually-hidden">Status is reachable</span>
  John Doe
</a>
```

The `inner_text()` method returns ALL text, including hidden elements. We filter it:

```python
text = (await link_el.inner_text()).strip()

# Skip known noise patterns
if "Status is" in text:
    continue
```

---

## Complete Scraping Code

```python
async def scrape_connections(self) -> list[dict]:
    """Scrape the connections list page."""
    await self._page.goto(self.CONNECTIONS_URL, wait_until="domcontentloaded")

    await self._page.wait_for_selector(
        'div[data-view-name="connections-list"]',
        timeout=10000
    )

    figures = await self._page.query_selector_all(
        'figure[aria-label*="profile picture"]'
    )

    connections = []
    seen_urls = set()

    for figure in figures:
        aria_label = await figure.get_attribute('aria-label')
        if not aria_label or "profile picture" not in aria_label:
            continue

        idx = aria_label.find("s profile picture")
        if idx > 0:
            name = aria_label[:idx-1].strip()
        else:
            name = aria_label.replace("profile picture", "").strip()

        parent_link = await figure.evaluate('el => el.closest("a")?.href')
        if not parent_link or parent_link in seen_urls:
            continue

        seen_urls.add(parent_link)
        connections.append({
            "name": name,
            "headline": "",
            "profile_url": parent_link,
        })

    return connections
```

---

## Testing

```python
async def main():
    async with LinkedInBrowser() as browser:
        if await browser.is_logged_in():
            connections = await browser.scrape_connections()
            print(f"Found {len(connections)} connections")

            for c in connections[:5]:
                print(f"  {c['name']}: {c['profile_url']}")
```

Output:
```
Found 10 connections
  John Doe: https://www.linkedin.com/in/johndoe/
  Jane Smith: https://www.linkedin.com/in/janesmith/
  ...
```

---

## Key Takeaways

1. **Avoid hashed classes**: Use `data-*`, `aria-*`, or URL patterns
2. **aria-label is your friend**: Accessibility attributes are stable
3. **Handle edge cases**: Apostrophes, hidden text, empty elements
4. **Use sets for deduplication**: `seen_urls = set()`

---

## What's Next

In Part 5, we'll add anti-detection measures:
- Random delays
- Viewport randomization
- Human-like scrolling

---

*Previous: [Part 3 - Cookie Authentication](./03-cookie-authentication.md)*
*Next: [Part 5 - Anti-Detection](./05-anti-detection.md)*
