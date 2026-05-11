<p align="center">
  <h1 align="center">🏠 Aqar.ai</h1>
  <p align="center">
    <strong>AI-Driven Cross-Platform Real Estate Aggregator</strong>
  </p>
  <p align="center">
    Automated extraction and semantic mapping of real estate listings<br/>
    from unstructured social media video content.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-15+-black?logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/PostgreSQL-16+-blue?logo=postgresql" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

---

## 🎯 What is Aqar.ai?

In Morocco's Tangier-Tetouan region, real estate commerce lives on social media. Independent agents post raw video tours on YouTube where critical property data — price, area, legal status, location — is locked within spoken **Arabic/Darija** dialogue.

**Aqar.ai** is an end-to-end AI pipeline that:

1. **Discovers** real estate videos from YouTube channels
2. **Transcribes** spoken Arabic/Darija using Whisper
3. **Extracts** structured property data using LLMs (Claude)
4. **Geocodes** properties to precise map locations
5. **Serves** a searchable web & mobile portal

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Aqar.ai Pipeline                    │
│                                                          │
│  [YouTube] → [Audio] → [Whisper] → [LLM] → [Geocode]  │
│      ↓          ↓          ↓          ↓         ↓       │
│   Discover   Extract   Transcribe  Extract    Map       │
│   Videos     Audio     Darija      Data      Location   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              PostgreSQL + PostGIS                  │   │
│  │              Meilisearch (Search)                  │   │
│  │              Redis (Queue + Cache)                 │   │
│  └──────────────────────────────────────────────────┘   │
│                          ↓                               │
│           ┌──────────────┼──────────────┐               │
│           │              │              │               │
│      [FastAPI]     [Next.js Web]  [React Native]       │
│       REST API      Portal         Mobile App           │
└─────────────────────────────────────────────────────────┘
```

## 📂 Monorepo Structure

```
aqar-ai/
├── apps/
│   ├── api/              # FastAPI backend
│   ├── web/              # Next.js web portal
│   └── mobile/           # React Native / Expo app
├── packages/
│   ├── pipeline/         # Core AI pipeline (Python)
│   ├── shared/           # Shared types & constants
│   └── db/               # Database models & migrations
├── infra/
│   ├── docker/           # Dockerfiles per service
│   └── scripts/          # Utility scripts
├── prompts/              # LLM prompt templates (version-controlled)
├── .github/              # CI/CD workflows
├── docker-compose.yml    # Local development stack
├── Makefile              # Developer commands
└── pyproject.toml        # Python monorepo config
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 20+**
- **Docker & Docker Compose**
- **Make** (optional but recommended)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/aqar-ai.git
cd aqar-ai

# 2. Copy environment files
cp .env.example .env

# 3. Start all services
make dev

# 4. Verify everything is running
make health
```

### Available Commands

```bash
make dev          # Start all services (Docker Compose)
make stop         # Stop all services
make test         # Run all tests
make test-unit    # Run unit tests only
make test-int     # Run integration tests only
make lint         # Run all linters
make format       # Auto-format all code
make migrate      # Run database migrations
make seed         # Seed database with sample data
make health       # Check service health
make logs         # Tail all service logs
make clean        # Remove containers, volumes, caches
make build        # Build all Docker images
```

## 🔧 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI/ML Pipeline | Python 3.12+ | Whisper, LLM extraction, NLP |
| Backend API | FastAPI | Async REST API with auto-docs |
| Web Frontend | Next.js 15 | SSR portal with search & maps |
| Mobile App | React Native / Expo | Cross-platform iOS/Android |
| Database | PostgreSQL 16 + PostGIS | Geospatial property storage |
| Search | Meilisearch | Full-text search with Arabic support |
| Queue | Redis + Celery | Async video processing pipeline |
| Speech-to-Text | OpenAI Whisper (large-v3) | Arabic/Darija transcription |
| LLM | Claude API (Sonnet) | Structured data extraction |
| CI/CD | GitHub Actions | Automated testing & deployment |

## 📋 Environment Variables

See `.env.example` for all configuration options. Key variables:

| Variable | Description | Required |
|----------|------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `ANTHROPIC_API_KEY` | Claude API key for extraction | Yes |
| `MEILISEARCH_URL` | Meilisearch endpoint | Yes |
| `MEILISEARCH_API_KEY` | Meilisearch master key | Yes |

## 🧪 Testing

```bash
# All tests
make test

# With coverage report
make test-coverage

# ML quality tests (against golden dataset)
make test-ml
```

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ for the Moroccan real estate market
</p>
