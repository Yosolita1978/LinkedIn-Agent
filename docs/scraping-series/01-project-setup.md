# Web Scraping Series: Part 1 - Project Setup

*Building a Professional LinkedIn Scraper with Python and Playwright*

---

## Introduction

In this series, we'll build a production-quality web scraper for LinkedIn. Not a quick script that breaks tomorrow, but a robust system with:

- Anti-detection measures
- Error handling and retry logic
- Pagination for large datasets
- Structured logging
- Clean architecture

By the end, you'll understand the techniques used in real-world scraping projects.

**What we'll build:**
- A LinkedIn connection/follower scraper
- Profile detail extractor
- Cookie-based authentication system

**Tech stack:**
- Python 3.12+
- Playwright (browser automation)
- FastAPI (API layer)
- asyncio (async/await)

---

## Part 1: Project Setup

### Why Playwright?

Before we write code, let's discuss why Playwright over alternatives:

| Feature | Playwright | Selenium | Puppeteer |
|---------|-----------|----------|-----------|
| Async support | Native | Needs wrapper | Native |
| Auto-wait | Built-in | Manual | Manual |
| Python support | First-class | First-class | Limited |
| Browser install | One command | Manual | Manual |
| Modern sites | Excellent | Good | Excellent |

Playwright's async-first design makes it perfect for scraping where we're constantly waiting for pages to load.

---

### Project Structure

```
linkedin-scraper/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   └── services/
│   │       ├── __init__.py
│   │       └── linkedin_browser.py  # Our scraper
│   ├── playwright-data/         # Cookies, debug files
│   ├── pyproject.toml           # Dependencies
│   └── test_auth.py             # Test script
└── docs/
```

We're using FastAPI even though we're focused on scraping because:
1. We'll eventually expose the data via API
2. It gives us a health check endpoint
3. Pydantic settings integrate nicely

---

### Step 1: Initialize the Project

```bash
mkdir linkedin-scraper
cd linkedin-scraper
mkdir -p backend/app/services
mkdir -p backend/playwright-data
```

### Step 2: Create pyproject.toml

```toml
[project]
name = "linkedin-scraper"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.128.0",
    "playwright>=1.57.0",
    "pydantic>=2.12.0",
    "pydantic-settings>=2.12.0",
    "uvicorn[standard]>=0.40.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
]
```

### Step 3: Install Dependencies

We'll use `uv` for fast, reliable Python package management:

```bash
cd backend

# Create virtual environment
uv venv

# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

---

### Step 4: Configuration

Create `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change-this-in-production"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

This uses Pydantic Settings which:
- Loads from environment variables
- Falls back to `.env` file
- Provides type validation
- Caches the settings instance

---

### Step 5: Basic FastAPI App

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="LinkedIn Scraper",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "env": settings.app_env}
```

---

### Step 6: Verify Setup

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health`. You should see:

```json
{"status": "healthy", "env": "development"}
```

---

## What's Next

In Part 2, we'll:
- Set up the Playwright browser class
- Implement the async context manager pattern
- Add cookie persistence for authentication

---

## Key Takeaways

1. **Use modern tools**: Playwright + uv + Pydantic Settings
2. **Structure for growth**: Even a scraper benefits from clean architecture
3. **Async from the start**: Makes Playwright integration natural
4. **Configuration management**: Environment-based settings

---

## Code So Far

The complete code for this part is available in the repository under the `part-1-setup` tag.

```bash
git checkout part-1-setup
```

---

*Next: [Part 2 - Playwright Basics](./02-playwright-basics.md)*
