# Web Scraping Series: Part 7 - Profile Extraction

*Extracting Detailed Information from LinkedIn Profiles*

---

## Introduction

After scraping connection and follower lists, we often need more details about specific people. Profile pages contain:

- Full name and headline
- Current company and location
- About section
- Work experience
- Education history

**Challenge:** Profile pages are complex with varying structures. Not everyone has an "About" section, some have multiple positions, education varies widely.

---

## Profile Page Structure

A LinkedIn profile has distinct sections:

```
┌─────────────────────────────────────────┐
│  Header Section                         │
│  ┌─────────────────────────────────┐   │
│  │ Name                            │   │
│  │ Headline                        │   │
│  │ Location                        │   │
│  │ Current Company                 │   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  About Section (optional)              │
│  "Passionate developer with 10..."     │
├─────────────────────────────────────────┤
│  Experience Section                     │
│  ┌─────────────────────────────────┐   │
│  │ Job 1: Title @ Company          │   │
│  │ Job 2: Title @ Company          │   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  Education Section                      │
│  ┌─────────────────────────────────┐   │
│  │ School 1: Degree                │   │
│  │ School 2: Degree                │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## Selector Strategy

Profile pages use semantic HTML with `section` elements and aria-labels:

```html
<section aria-label="About">
  <div>Passionate developer...</div>
</section>

<section aria-label="Experience">
  <ul>
    <li>...</li>
  </ul>
</section>
```

**Key insight:** Section aria-labels are stable identifiers we can rely on.

---

## Basic Profile Extraction

### Step 1: Navigate to Profile

```python
async def scrape_profile(self, profile_url: str) -> dict:
    """
    Scrape detailed information from a LinkedIn profile.

    Args:
        profile_url: Full URL to the LinkedIn profile

    Returns:
        Dictionary with profile details
    """
    await self._navigate_with_delay(profile_url)

    # Wait for main content to load
    await self._page.wait_for_selector(
        'main.scaffold-layout__main',
        timeout=10000
    )

    # Give dynamic content time to render
    await random_delay(1.0, 2.0)
```

### Step 2: Extract Header Information

The header contains name, headline, location, and company:

```python
async def _extract_profile_header(self) -> dict:
    """Extract basic info from profile header."""
    header = {}

    # Name - usually in h1
    name_el = await self._page.query_selector('h1')
    if name_el:
        header['name'] = (await name_el.inner_text()).strip()

    # Headline - the text under the name
    headline_el = await self._page.query_selector(
        'div.text-body-medium'
    )
    if headline_el:
        header['headline'] = (await headline_el.inner_text()).strip()

    # Location
    location_el = await self._page.query_selector(
        'span.text-body-small.inline'
    )
    if location_el:
        header['location'] = (await location_el.inner_text()).strip()

    return header
```

### Step 3: Extract About Section

The About section is optional:

```python
async def _extract_about(self) -> str:
    """Extract the About section text."""
    about_section = await self._page.query_selector(
        'section[aria-label="About"]'
    )

    if not about_section:
        return ""

    # The about text is usually in a div with specific classes
    about_text_el = await about_section.query_selector(
        'div.display-flex.full-width span[aria-hidden="true"]'
    )

    if about_text_el:
        return (await about_text_el.inner_text()).strip()

    return ""
```

---

## Extracting Experience

Experience is more complex—multiple jobs, each with company, title, duration:

```python
async def _extract_experience(self) -> list[dict]:
    """Extract work experience entries."""
    experience_section = await self._page.query_selector(
        'section[aria-label="Experience"]'
    )

    if not experience_section:
        return []

    experiences = []

    # Find all experience entries
    entries = await experience_section.query_selector_all(
        'li.artdeco-list__item'
    )

    for entry in entries:
        exp = await self._parse_experience_entry(entry)
        if exp:
            experiences.append(exp)

    return experiences


async def _parse_experience_entry(self, entry) -> dict | None:
    """Parse a single experience entry."""
    try:
        # Job title
        title_el = await entry.query_selector(
            'div.display-flex.align-items-center span[aria-hidden="true"]'
        )
        title = (await title_el.inner_text()).strip() if title_el else ""

        # Company name - look for link or span with company
        company_el = await entry.query_selector(
            'span.t-14.t-normal span[aria-hidden="true"]'
        )
        company = (await company_el.inner_text()).strip() if company_el else ""

        # Duration/dates
        duration_el = await entry.query_selector(
            'span.t-14.t-normal.t-black--light span[aria-hidden="true"]'
        )
        duration = (await duration_el.inner_text()).strip() if duration_el else ""

        if not title and not company:
            return None

        return {
            "title": title,
            "company": company,
            "duration": duration,
        }
    except Exception:
        return None
```

---

## Extracting Education

Similar pattern to experience:

```python
async def _extract_education(self) -> list[dict]:
    """Extract education entries."""
    education_section = await self._page.query_selector(
        'section[aria-label="Education"]'
    )

    if not education_section:
        return []

    education = []

    entries = await education_section.query_selector_all(
        'li.artdeco-list__item'
    )

    for entry in entries:
        edu = await self._parse_education_entry(entry)
        if edu:
            education.append(edu)

    return education


async def _parse_education_entry(self, entry) -> dict | None:
    """Parse a single education entry."""
    try:
        # School name
        school_el = await entry.query_selector(
            'div.display-flex.align-items-center span[aria-hidden="true"]'
        )
        school = (await school_el.inner_text()).strip() if school_el else ""

        # Degree/field
        degree_el = await entry.query_selector(
            'span.t-14.t-normal span[aria-hidden="true"]'
        )
        degree = (await degree_el.inner_text()).strip() if degree_el else ""

        if not school:
            return None

        return {
            "school": school,
            "degree": degree,
        }
    except Exception:
        return None
```

---

## Complete Profile Scraper

```python
async def scrape_profile(self, profile_url: str) -> dict:
    """
    Scrape detailed information from a LinkedIn profile.

    Args:
        profile_url: Full URL to the LinkedIn profile

    Returns:
        Dictionary with name, headline, location, about,
        experience, and education
    """
    logger.info(f"Scraping profile: {profile_url}")

    await self._navigate_with_delay(profile_url)

    await self._page.wait_for_selector(
        'main.scaffold-layout__main',
        timeout=10000
    )

    await random_delay(1.0, 2.0)

    # Scroll to load lazy content
    await self._human_scroll(800, steps=4)
    await random_delay(0.5, 1.0)

    # Extract all sections
    profile = {}

    # Header info (name, headline, location)
    header = await self._extract_profile_header()
    profile.update(header)

    # About section
    profile['about'] = await self._extract_about()

    # Experience
    profile['experience'] = await self._extract_experience()

    # Education
    profile['education'] = await self._extract_education()

    logger.info(f"Profile scraped: {profile.get('name', 'Unknown')}")

    return profile
```

---

## Handling Variations

LinkedIn profiles vary significantly. Handle missing data gracefully:

```python
# Always provide defaults
profile = {
    'name': '',
    'headline': '',
    'location': '',
    'about': '',
    'experience': [],
    'education': [],
}

# Update with extracted data
header = await self._extract_profile_header()
profile.update(header)  # Only overwrites what's found
```

### Common Variations

| Variation | How to Handle |
|-----------|---------------|
| No About section | Return empty string |
| Multiple positions at same company | Parse as separate entries |
| No education listed | Return empty list |
| Private profile | Check for "private" indicator |
| Different languages | Selectors still work, text varies |

---

## Testing Profile Extraction

```python
async def main():
    async with LinkedInBrowser() as browser:
        if not await browser.is_logged_in():
            print("Not logged in")
            return

        # First get some connections
        connections = await browser.scrape_connections(max_items=5)

        # Then scrape first profile
        if connections:
            profile = await browser.scrape_profile(
                connections[0]['profile_url']
            )

            print(f"Name: {profile['name']}")
            print(f"Headline: {profile['headline']}")
            print(f"Location: {profile['location']}")
            print(f"About: {profile['about'][:100]}...")

            print("\nExperience:")
            for exp in profile['experience'][:3]:
                print(f"  - {exp['title']} @ {exp['company']}")

            print("\nEducation:")
            for edu in profile['education']:
                print(f"  - {edu['school']}: {edu['degree']}")
```

Sample output:

```
Name: John Doe
Headline: Senior Software Engineer at TechCorp
Location: San Francisco Bay Area

About: Passionate software engineer with 10+ years of experience...

Experience:
  - Senior Software Engineer @ TechCorp
  - Software Engineer @ StartupXYZ
  - Junior Developer @ FirstJob Inc

Education:
  - Stanford University: MS Computer Science
  - UC Berkeley: BS Computer Science
```

---

## Rate Limiting

Profile pages are heavier requests. Add extra delays:

```python
async def scrape_multiple_profiles(
    self,
    profile_urls: list[str],
    delay_between: float = 5.0
) -> list[dict]:
    """Scrape multiple profiles with rate limiting."""
    profiles = []

    for i, url in enumerate(profile_urls):
        logger.info(f"Scraping profile {i+1}/{len(profile_urls)}")

        profile = await self.scrape_profile(url)
        profiles.append(profile)

        # Longer delay between profiles
        if i < len(profile_urls) - 1:
            await random_delay(delay_between, delay_between + 2.0)

    return profiles
```

---

## Error Handling

Profiles can fail for various reasons:

```python
@async_retry(max_attempts=2, base_delay=2.0)
async def scrape_profile(self, profile_url: str) -> dict:
    """Scrape profile with retry on failure."""
    try:
        await self._navigate_with_delay(profile_url)

        # Check for error states
        not_found = await self._page.query_selector(
            'h1:text("Page not found")'
        )
        if not_found:
            raise ScrapingError(f"Profile not found: {profile_url}")

        # ... extraction logic

    except PlaywrightTimeout:
        raise ScrapingError(f"Timeout loading profile: {profile_url}")
```

---

## Key Takeaways

1. **Use aria-labels** to find sections reliably
2. **Handle missing sections** with defaults
3. **Scroll before extracting** to load lazy content
4. **Add delays between profiles** to avoid rate limits
5. **Return structured data** even when fields are empty

---

## Series Conclusion

Over this series, we've built a complete LinkedIn scraper with:

- **Cookie-based authentication** (Part 3)
- **Stable selectors** using aria-labels (Part 4)
- **Anti-detection measures** (Part 5)
- **Pagination handling** (Part 6)
- **Profile extraction** (Part 7)

The techniques here apply to any modern web scraping project. The key principles:

1. **Respect the site** - add delays, limit requests
2. **Build resilient selectors** - use stable attributes
3. **Handle failures gracefully** - retry, log, continue
4. **Structure your code** - classes, methods, types

Happy scraping!

---

*Previous: [Part 6 - Pagination](./06-pagination.md)*
*Back to: [Series Index](./README.md)*
