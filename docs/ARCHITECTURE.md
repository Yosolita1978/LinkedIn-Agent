# Architecture

This document describes the system architecture of the LinkedIn Intelligence & Outreach Agent.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                LinkedIn Intelligence & Outreach Agent        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LinkedIn Export (CSV)                                       │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐  │
│  │ Export Parser│────▶│   Supabase   │◀────│  Segmenter  │  │
│  └──────────────┘     │  PostgreSQL  │     └─────────────┘  │
│                       └──────────────┘                       │
│                              │                               │
│         ┌────────────────────┼────────────────────┐         │
│         ▼                    ▼                    ▼         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Warmth    │     │Resurrection │     │  Claude AI  │   │
│  │   Scorer    │     │   Scanner   │     │  Generator  │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│         │                    │                    │         │
│         └────────────────────┼────────────────────┘         │
│                              ▼                               │
│                       ┌─────────────┐                       │
│                       │ FastAPI API │                       │
│                       └─────────────┘                       │
│                              │                               │
│                              ▼                               │
│                       ┌─────────────┐                       │
│                       │  Frontend   │                       │
│                       │   (React)   │                       │
│                       └─────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Backend (FastAPI + SQLAlchemy Async)

**Location**: `/backend/app/`

**Status**: Core functionality complete.

#### Services

| Service | File | Purpose |
|---------|------|---------|
| Export Parser | `services/export_parser.py` | Parse LinkedIn CSV exports |
| Warmth Scorer | `services/warmth_scorer.py` | Calculate relationship warmth (0-100) |
| Segmenter | `services/segmenter.py` | Auto-tag contacts into audience segments |
| Resurrection Scanner | `services/resurrection_scanner.py` | Detect outreach opportunities |
| Message Generator | `services/message_generator.py` | Generate messages via Claude API |
| LinkedIn Browser | `services/linkedin_browser.py` | Playwright scraper (optional) |

#### API Routes

| Router | Prefix | Purpose |
|--------|--------|---------|
| upload | `/api/upload` | CSV file uploads |
| contacts | `/api/contacts` | Contact CRUD + filtering |
| target_companies | `/api/target-companies` | Job search targets |
| resurrection | `/api/resurrection` | Opportunity detection |
| generate | `/api/generate` | Message generation |

---

### 2. Database (Supabase PostgreSQL)

**Status**: 6 tables implemented.

#### Schema

```sql
-- Core contact data
contacts (
  id UUID PRIMARY KEY,
  linkedin_url TEXT UNIQUE,
  name TEXT NOT NULL,
  headline TEXT,
  location TEXT,
  company TEXT,
  position TEXT,
  about TEXT,
  email TEXT,
  experience JSONB,
  education JSONB,
  connection_date DATE,
  scraped_at TIMESTAMP,

  -- Warmth scoring
  warmth_score INTEGER DEFAULT 0,
  warmth_breakdown JSONB,
  warmth_calculated_at TIMESTAMP,

  -- Segmentation
  segment_tags TEXT[],
  manual_tags TEXT[],

  -- Message stats
  total_messages INTEGER DEFAULT 0,
  last_message_date DATE,
  last_message_direction TEXT,

  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- Message history
messages (
  id UUID PRIMARY KEY,
  contact_id UUID REFERENCES contacts,
  direction TEXT NOT NULL,  -- 'sent' or 'received'
  date TIMESTAMP NOT NULL,
  subject TEXT,
  content TEXT,
  content_length INTEGER,
  is_substantive BOOLEAN,
  conversation_id TEXT,
  created_at TIMESTAMP
)

-- Outreach opportunities
resurrection_opportunities (
  id UUID PRIMARY KEY,
  contact_id UUID REFERENCES contacts,
  hook_type TEXT NOT NULL,  -- dormant, promise_made, question_unanswered, they_waiting
  hook_detail TEXT,
  source_message_id UUID REFERENCES messages,
  detected_at TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  UNIQUE(contact_id, hook_type)
)

-- Job search targets
target_companies (
  id UUID PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  notes TEXT,
  created_at TIMESTAMP
)

-- Message queue
outreach_queue_items (
  id UUID PRIMARY KEY,
  contact_id UUID REFERENCES contacts,
  status TEXT DEFAULT 'draft',  -- draft, approved, sent, responded
  generated_message TEXT,
  segment TEXT,
  purpose TEXT,
  created_at TIMESTAMP,
  sent_at TIMESTAMP
)

-- Upload tracking
data_uploads (
  id UUID PRIMARY KEY,
  file_type TEXT NOT NULL,  -- connections, messages
  filename TEXT,
  records_processed INTEGER DEFAULT 0,
  uploaded_at TIMESTAMP
)
```

---

### 3. Warmth Scoring Algorithm

Calculates relationship "warmth" (0-100) based on message patterns:

| Factor | Points | Logic |
|--------|--------|-------|
| Recency | 0-30 | Days since last message (30 if <7d, 0 if >180d) |
| Frequency | 0-20 | Total messages (20 if 20+ messages) |
| Depth | 0-25 | Avg length + substantive ratio |
| Responsiveness | 0-15 | Balance of sent/received (15 if balanced) |
| Initiation | 0-10 | Do they initiate conversations? |

**Substantive message**: 100+ characters, excludes shallow patterns ("thanks", "congrats", emoji-only).

---

### 4. Audience Segments

Three predefined segments based on use cases:

#### MujerTech
- **Target**: Women entrepreneurs in Latin America
- **Detection**: LATAM locations (50+ cities/countries) + entrepreneur keywords
- **Tone**: Warm, supportive, Spanish phrases OK

#### Cascadia AI
- **Target**: AI/ML professionals in Pacific Northwest
- **Detection**: PNW locations + AI/ML keywords in headline/position
- **Tone**: Professional, tech-savvy, local community focus

#### Job Target
- **Target**: People at companies you want to work for
- **Detection**: Company matches target_companies table
- **Tone**: Curious about their work, not asking for referrals

---

### 5. Resurrection Hooks

Detects reasons to reach out:

| Hook Type | Detection Logic |
|-----------|-----------------|
| `dormant` | Warmth ≥40 AND no messages in 60+ days |
| `promise_made` | Your message contains "I'll", "let me", etc. with no follow-up |
| `question_unanswered` | They asked "?" and you never replied |
| `they_waiting` | Last message was from them |

---

### 6. Message Generation

Uses Claude API (claude-sonnet-4-20250514) to generate personalized messages.

**Inputs:**
- Contact profile data
- Recent message history (last 5)
- Segment context
- Resurrection hooks
- Purpose (reconnect, introduce, etc.)

**Output:**
- 1-3 message variations
- Token usage tracking

---

### 7. Frontend (React + TypeScript)

**Location**: `/frontend/`

**Status**: Basic setup, not yet functional.

**Planned Features:**
- Dashboard with warmth heatmap
- Contact list with filters (segment, warmth, has messages)
- Opportunity cards (resurrection hooks)
- Message generation UI
- Outreach queue management

---

## File Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + routers
│   ├── config.py                  # Pydantic settings
│   ├── database.py                # SQLAlchemy async setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── contact.py             # Contact model
│   │   ├── message.py             # Message model
│   │   ├── resurrection.py        # ResurrectionOpportunity model
│   │   ├── target_company.py      # TargetCompany model
│   │   ├── queue.py               # OutreachQueueItem model
│   │   └── upload.py              # DataUpload model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py              # CSV upload endpoints
│   │   ├── contacts.py            # Contact CRUD
│   │   ├── target_companies.py    # Target company CRUD
│   │   ├── resurrection.py        # Opportunity endpoints
│   │   └── generate.py            # Message generation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── export_parser.py       # LinkedIn CSV parser
│   │   ├── warmth_scorer.py       # Warmth calculation
│   │   ├── segmenter.py           # Audience segmentation
│   │   ├── resurrection_scanner.py # Opportunity detection
│   │   ├── message_generator.py   # Claude API integration
│   │   └── linkedin_browser.py    # Playwright scraper
│   └── schemas/
│       └── contact.py             # Pydantic schemas
├── playwright-data/
│   └── cookies.json               # Session cookies (gitignored)
├── .env                           # Environment variables (gitignored)
└── pyproject.toml                 # Dependencies

frontend/
├── src/
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts

docs/
├── README.md
├── ARCHITECTURE.md                # This file
├── PROGRESS.md                    # Implementation progress
├── DECISIONS.md                   # Design decisions
└── CHANGELOG.md
```

---

## Configuration

### Environment Variables

```bash
# backend/.env

# App
APP_ENV=development
SECRET_KEY=your-secret-key

# Database (Supabase)
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres

# AI (Anthropic)
ANTHROPIC_API_KEY=sk-ant-api03-...

# LinkedIn (optional, for scraper)
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=your-password

# Rate Limits
RATE_LIMIT_MESSAGES_PER_DAY=50
RATE_LIMIT_PROFILES_PER_DAY=100
```

---

## API Reference

### Upload

```bash
# Upload connections
POST /api/upload/connections
Content-Type: multipart/form-data
file: Connections.csv

# Upload messages
POST /api/upload/messages
Content-Type: multipart/form-data
file: messages.csv

# Get upload stats
GET /api/upload/status
```

### Contacts

```bash
# List contacts (with filters)
GET /api/contacts?page=1&page_size=50&search=john&warmth_min=40&segment=cascadia

# Get contact detail
GET /api/contacts/{id}

# Get top warmth contacts
GET /api/contacts/top-warmth?limit=20

# Get stats
GET /api/contacts/stats

# Recalculate warmth scores
POST /api/contacts/recalculate-warmth

# Run segmentation
POST /api/contacts/segment?all_contacts=true
```

### Target Companies

```bash
# List all
GET /api/target-companies

# Add one
POST /api/target-companies
{"name": "Google", "notes": "Dream company"}

# Add bulk
POST /api/target-companies/bulk
[{"name": "Google"}, {"name": "Microsoft"}]

# Delete
DELETE /api/target-companies/{id}
```

### Resurrection

```bash
# Run full scan
POST /api/resurrection/scan

# Run specific scan
POST /api/resurrection/scan/dormant

# Get opportunities
GET /api/resurrection/opportunities?hook_type=they_waiting&limit=50

# Dismiss opportunity
POST /api/resurrection/opportunities/{id}/dismiss
```

### Generate

```bash
# Generate message
POST /api/generate/message
{
  "contact_id": "uuid",
  "purpose": "reconnect",
  "segment": "cascadia",
  "custom_context": "They just got promoted",
  "num_variations": 2
}

# Batch generate
POST /api/generate/batch
{
  "contact_ids": ["uuid1", "uuid2"],
  "purpose": "reconnect"
}

# List purposes
GET /api/generate/purposes
```

---

## Security Considerations

1. **No credential storage**: Uses cookie-based auth for LinkedIn scraper
2. **Cookies are gitignored**: Session data stays local
3. **Rate limiting**: Built-in delays to avoid LinkedIn detection
4. **Human review required**: All messages need manual approval before sending
5. **API keys in .env**: Never committed to repository
