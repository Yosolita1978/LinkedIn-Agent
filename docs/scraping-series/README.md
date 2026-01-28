# Web Scraping Series

*Building a Professional LinkedIn Scraper with Python and Playwright*

---

## Overview

This 7-part series walks through building a production-quality web scraper. We cover everything from project setup to advanced anti-detection techniques.

**What you'll learn:**
- Browser automation with Playwright
- Cookie-based authentication
- Finding stable selectors in dynamic sites
- Anti-detection measures
- Handling infinite scroll pagination
- Extracting structured data from complex pages

---

## The Series

| Part | Topic | Key Concepts |
|------|-------|--------------|
| [Part 1](./01-project-setup.md) | Project Setup | Python tooling, FastAPI, project structure |
| [Part 2](./02-playwright-basics.md) | Playwright Basics | Async API, context managers, browser lifecycle |
| [Part 3](./03-cookie-authentication.md) | Cookie Authentication | Session persistence, manual login flow |
| [Part 4](./04-scraping-lists.md) | Scraping Lists | Stable selectors, aria-labels, data extraction |
| [Part 5](./05-anti-detection.md) | Anti-Detection | User agent rotation, delays, human-like behavior |
| [Part 6](./06-pagination.md) | Pagination | Infinite scroll, duplicate detection, limits |
| [Part 7](./07-profile-extraction.md) | Profile Extraction | Complex pages, structured data, error handling |

---

## Prerequisites

- Python 3.12+
- Basic async/await understanding
- Familiarity with HTML/CSS selectors

---

## Tech Stack

- **Python 3.12** - Modern Python with type hints
- **Playwright** - Browser automation
- **FastAPI** - API layer
- **uv** - Fast Python package manager
- **Pydantic** - Data validation and settings

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/your-repo/linkedin-scraper.git
cd linkedin-scraper/backend

# Install dependencies
uv venv
uv sync
uv run playwright install chromium

# Run the test script
uv run python test_auth.py
```

---

## Code Repository

Each part has a corresponding git tag:

```bash
git checkout part-1-setup
git checkout part-2-playwright
git checkout part-3-auth
# ... etc
```

---

## Who This Is For

- Developers learning web scraping
- Engineers building data collection tools
- Anyone interested in browser automation

---

## Disclaimer

This series is for educational purposes. Always:
- Respect robots.txt and terms of service
- Add reasonable delays between requests
- Don't scrape personal data without consent
- Consider API alternatives when available

---

*Start with [Part 1: Project Setup](./01-project-setup.md)*
