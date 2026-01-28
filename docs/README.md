# LinkedIn Outreach Agent

A LinkedIn automation tool built with Python, Playwright, and FastAPI. This project demonstrates professional web scraping techniques with anti-detection measures, designed for educational purposes.

## What It Does

- **Authentication**: Cookie-based LinkedIn login (no credential storage)
- **Connection Scraping**: Extract your LinkedIn connections with pagination
- **Follower Scraping**: Extract your LinkedIn followers with pagination
- **Profile Extraction**: Get detailed profile information (name, headline, experience, education)
- **Anti-Detection**: Random delays, viewport randomization, human-like scrolling

## Project Status

| Component | Status |
|-----------|--------|
| Backend (FastAPI) | Basic setup |
| Playwright Browser | Fully functional |
| Cookie Authentication | Working |
| Connection Scraper | Working (with pagination) |
| Follower Scraper | Working (with pagination) |
| Profile Scraper | Working |
| Anti-Detection | Implemented |
| Frontend (React) | Basic setup |
| Database (Supabase) | Configured, not implemented |
| AI Integration (Claude) | Configured, not implemented |

## Tech Stack

### Backend
- **Python 3.12+**
- **FastAPI** - API framework
- **Playwright** - Browser automation
- **SQLAlchemy** - Database ORM (future)
- **Pydantic** - Data validation

### Frontend
- **React 19** with TypeScript
- **Vite** - Build tool
- **Tailwind CSS** - Styling

### Infrastructure
- **Supabase** - PostgreSQL database (future)
- **Anthropic Claude** - AI for message generation (future)

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

### Backend Setup

```bash
cd backend

# Create virtual environment and install dependencies
uv venv
uv sync

# Install Playwright browsers
uv run playwright install chromium

# Copy environment template
cp .env.example .env
```

### First Run: Manual Login

The first time you run the scraper, you need to authenticate manually:

```python
import asyncio
from app.services.linkedin_browser import LinkedInBrowser

async def login():
    async with LinkedInBrowser() as browser:
        await browser.manual_login()

asyncio.run(login())
```

This opens a browser window where you log in to LinkedIn. Your session cookies are saved to `playwright-data/cookies.json` for future runs.

### Running the Scraper

```bash
cd backend
uv run python test_auth.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Usage Examples

### Scrape Connections

```python
async with LinkedInBrowser() as browser:
    if await browser.is_logged_in():
        connections = await browser.scrape_connections(max_items=50)
        for c in connections:
            print(f"{c['name']} - {c['profile_url']}")
```

### Scrape Followers

```python
async with LinkedInBrowser() as browser:
    if await browser.is_logged_in():
        followers = await browser.scrape_followers(max_items=50)
        for f in followers:
            print(f"{f['name']} - {f['headline']}")
```

### Scrape Profile Details

```python
async with LinkedInBrowser() as browser:
    if await browser.is_logged_in():
        profile = await browser.scrape_profile("https://linkedin.com/in/username/")
        print(f"Name: {profile['name']}")
        print(f"Headline: {profile['headline']}")
        print(f"Location: {profile['location']}")
        print(f"Experience: {profile['experience']}")
```

## Project Structure

```
linkedin-outreach-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Environment configuration
│   │   ├── services/
│   │   │   └── linkedin_browser.py  # Playwright scraper
│   │   ├── models/              # Database models (future)
│   │   ├── routes/              # API endpoints (future)
│   │   └── utils/               # Helper functions
│   ├── playwright-data/
│   │   └── cookies.json         # Saved session cookies
│   ├── test_auth.py             # Test script
│   └── pyproject.toml           # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React component
│   │   └── main.tsx             # Entry point
│   ├── package.json
│   └── vite.config.ts
├── docs/                        # Documentation
│   ├── README.md                # This file
│   ├── ARCHITECTURE.md          # System design
│   ├── DECISIONS.md             # Decision log
│   ├── CHANGELOG.md             # Version history
│   └── scraping-series/         # Blog post drafts
└── CLAUDE.md                    # AI pair programming instructions
```

## Documentation

- [Architecture](./ARCHITECTURE.md) - System design and components
- [Decisions](./DECISIONS.md) - Technical decision log
- [Changelog](./CHANGELOG.md) - What changed and when
- [Scraping Series](./scraping-series/) - Educational blog posts

## Disclaimer

This project is for educational purposes only. Web scraping may violate LinkedIn's Terms of Service. Use responsibly and at your own risk. Always respect rate limits and avoid aggressive scraping that could impact LinkedIn's services.

## License

MIT
