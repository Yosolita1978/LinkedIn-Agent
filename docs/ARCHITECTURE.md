# Architecture

This document describes the system architecture of the LinkedIn Outreach Agent.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        LinkedIn Outreach Agent                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Frontend   │────▶│   Backend    │────▶│   LinkedIn   │    │
│  │   (React)    │     │  (FastAPI)   │     │  (Playwright)│    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │                    │                    │             │
│         │                    ▼                    │             │
│         │            ┌──────────────┐             │             │
│         │            │   Database   │             │             │
│         │            │  (Supabase)  │             │             │
│         │            └──────────────┘             │             │
│         │                    │                    │             │
│         │                    ▼                    │             │
│         │            ┌──────────────┐             │             │
│         └───────────▶│   Claude AI  │◀────────────┘             │
│                      │  (Anthropic) │                           │
│                      └──────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend (React + TypeScript)

**Location**: `/frontend/`

**Purpose**: User interface for managing outreach campaigns.

**Status**: Basic setup, not yet functional.

**Key Files**:
- `src/App.tsx` - Main application component
- `src/main.tsx` - React entry point
- `vite.config.ts` - Vite configuration

**Future Features**:
- Dashboard showing connections/followers
- Campaign management UI
- Message template editor
- Analytics and reporting

---

### 2. Backend (FastAPI)

**Location**: `/backend/app/`

**Purpose**: API server and business logic.

**Status**: Basic setup with health check endpoint.

**Key Files**:
- `main.py` - FastAPI application with CORS
- `config.py` - Environment configuration (Pydantic Settings)

**Current Endpoints**:
```
GET /        - Root endpoint
GET /health  - Health check
```

**Future Endpoints**:
```
GET  /connections     - List scraped connections
GET  /followers       - List scraped followers
GET  /profiles/{id}   - Get profile details
POST /campaigns       - Create outreach campaign
POST /messages        - Generate AI message
```

---

### 3. LinkedIn Browser (Playwright)

**Location**: `/backend/app/services/linkedin_browser.py`

**Purpose**: Browser automation for LinkedIn scraping.

**Status**: Fully functional.

**Class**: `LinkedInBrowser`

#### Key Methods

| Method | Purpose |
|--------|---------|
| `start()` | Launch browser with anti-detection settings |
| `stop()` | Close browser and cleanup |
| `is_logged_in()` | Check if session is valid |
| `manual_login()` | Interactive login flow |
| `scrape_connections(max_items)` | Scrape connection list |
| `scrape_followers(max_items)` | Scrape follower list |
| `scrape_profile(url)` | Scrape individual profile |

#### Anti-Detection Features

1. **User Agent Rotation**: Random selection from 5 Chrome user agents
2. **Viewport Randomization**: Varies screen size each session
3. **Random Delays**: Variable wait times between actions
4. **Human-like Scrolling**: Scroll in steps with random pauses
5. **Locale/Timezone**: Set to common US values

#### Data Flow

```
1. Start browser with random fingerprint
2. Load saved cookies (if exist)
3. Navigate to target page
4. Wait for content + random delay
5. Scroll to load lazy content
6. Extract data from DOM
7. Return structured data
```

---

### 4. Database (Supabase)

**Status**: Configured but not implemented.

**Future Schema**:

```sql
-- Contacts table
contacts (
  id UUID PRIMARY KEY,
  linkedin_url TEXT UNIQUE,
  name TEXT,
  headline TEXT,
  location TEXT,
  company TEXT,
  scraped_at TIMESTAMP
)

-- Campaigns table
campaigns (
  id UUID PRIMARY KEY,
  name TEXT,
  template TEXT,
  status TEXT,
  created_at TIMESTAMP
)

-- Messages table
messages (
  id UUID PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns,
  contact_id UUID REFERENCES contacts,
  content TEXT,
  status TEXT,
  sent_at TIMESTAMP
)
```

---

### 5. AI Integration (Claude)

**Status**: Configured but not implemented.

**Purpose**: Generate personalized outreach messages.

**Future Flow**:
```
1. Get contact profile data
2. Get campaign template
3. Send to Claude API with context
4. Receive personalized message
5. Store for review/sending
```

---

## File Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── services/
│   │   ├── __init__.py
│   │   └── linkedin_browser.py # Playwright scraper (580+ lines)
│   ├── models/                 # SQLAlchemy models (future)
│   ├── routes/                 # API routes (future)
│   └── utils/                  # Helpers (future)
├── playwright-data/
│   └── cookies.json            # Session cookies (gitignored)
├── test_auth.py                # Test script
└── pyproject.toml              # Dependencies
```

---

## Data Models

### Connection

```python
{
    "name": str,           # "John Doe"
    "headline": str,       # "" (not extracted from list)
    "profile_url": str     # "https://linkedin.com/in/johndoe/"
}
```

### Follower

```python
{
    "name": str,           # "Jane Smith"
    "headline": str,       # "Software Engineer at Google"
    "profile_url": str     # "https://linkedin.com/in/janesmith/"
}
```

### Profile (Full)

```python
{
    "name": str,           # "John Doe"
    "headline": str,       # "Senior Developer | Python Expert"
    "location": str,       # "San Francisco, CA"
    "company": str,        # "TechCorp"
    "about": str,          # "I build things..." (max 500 chars)
    "experience": [        # Up to 5 entries
        {"title": str, "company": str}
    ],
    "education": [         # Up to 3 entries
        {"school": str, "degree": str}
    ],
    "profile_url": str
}
```

---

## Configuration

### Environment Variables

```bash
# App
APP_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://...

# AI
ANTHROPIC_API_KEY=sk-ant-...

# Rate Limits
RATE_LIMIT_MESSAGES_PER_DAY=50
RATE_LIMIT_PROFILES_PER_DAY=100
```

---

## Security Considerations

1. **No credential storage**: Uses cookie-based auth only
2. **Cookies are gitignored**: Session data stays local
3. **Rate limiting**: Built-in delays to avoid detection
4. **No automated messaging**: Human review required (future)

---

## Future Roadmap

1. **Phase 3**: Database integration (store scraped data)
2. **Phase 4**: API endpoints (expose data to frontend)
3. **Phase 5**: Frontend dashboard
4. **Phase 6**: AI message generation
5. **Phase 7**: Campaign management
