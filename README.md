# Caduceus 🪬

> *The staff of Hermes — carried between worlds, broker of messages, connector of realms.*

**Caduceus** is a personal integration hub running on a Raspberry Pi 4. It aggregates data from Google (Calendar, Tasks, Gmail), weather services, task managers, and AI tools into a single clean REST API — consumed primarily by [**Huginn**](https://github.com/dreffed/huginn), the Presto desk display, but designed as a general-purpose personal data API.

It also consumes a RabbitMQ queue, allowing external automation tools (IFTTT, Zapier, n8n) to push events and trigger actions — bridging the event-driven world of automations with the request-driven world of your devices.

---

## What it connects

| Service | Type | Capabilities |
|---|---|---|
| Google Calendar | OAuth2 | Today, week, anniversaries |
| Google Tasks | OAuth2 | Read, create, complete |
| Gmail | OAuth2 | Unread summary, flagged messages |
| Open-Meteo | Free / no key | Current weather, 5-day forecast |
| Hexoplan | API Key | Task read/write |
| Ollama | Local | AI queries (runs on same network) |
| Alexa Tasks | (in progress) | Task read |
| IFTTT / Zapier / n8n | RabbitMQ | Event ingestion, trigger actions |

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │           CADUCEUS                   │
                    │         (docker-compose)             │
                    │                                      │
  IFTTT / Zapier ──►│  RabbitMQ   ──►  Hub Core           │
  n8n / webhooks    │  (broker)        (FastAPI)  ──► API  │──► Huginn
                    │                      │               │──► Any client
                    │  Redis  ◄────────────┤               │
                    │  (cache)             │               │
                    │                      ▼               │
                    │              Connectors              │
                    │   Google  │ Weather │ Tasks │ AI     │
                    └─────────────────────────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │  External Services     │
                          │  Google · Open-Meteo   │
                          │  Hexoplan · Ollama      │
                          └───────────────────────┘
```

---

## Getting Started

### Prerequisites

- Raspberry Pi 4 (recommended: with NVMe HAT for storage)
- Docker + docker-compose installed
- Git

### 1. Clone

```bash
git clone https://github.com/dreffed/caduceus.git
cd caduceus
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials (Google OAuth, weather location, etc.). See [Configuration](#configuration) below.

### 3. Google OAuth2 Setup (one-time)

Run this on a machine with a browser, then copy the token to your Pi:

```bash
pip install -r requirements-dev.txt
python scripts/setup_google_auth.py
# Follow browser prompt to grant access
# Token saved to ./data/google_token.json
```

Copy the token to your Pi:
```bash
scp ./data/google_token.json pi@{pi-ip}:/opt/caduceus/data/
```

### 4. Run

```bash
docker-compose up -d
```

The API is available at `http://{pi-ip}:8000`.
RabbitMQ management UI: `http://{pi-ip}:15672` (guest/guest in dev).
API docs (auto-generated): `http://{pi-ip}:8000/docs`

### 5. Verify

```bash
curl http://{pi-ip}:8000/v1/health
```

---

## Project Structure

```
caduceus/
├── docker-compose.yml          ← dev services
├── docker-compose.prod.yml     ← prod overrides (nginx, no exposed RabbitMQ)
├── .env.example                ← config template
├── Dockerfile
├── .github/
│   └── workflows/
│       ├── ci.yml              ← lint + test on PR
│       └── deploy.yml          ← build ARM64 image + deploy to Pi on merge
├── hub/
│   ├── main.py                 ← FastAPI app factory
│   ├── config.py               ← pydantic-settings configuration
│   ├── dependencies.py         ← FastAPI dependency injection
│   ├── routers/                ← one router per domain
│   │   ├── calendar.py
│   │   ├── tasks.py
│   │   ├── email.py
│   │   ├── weather.py
│   │   ├── dashboard.py
│   │   └── health.py
│   ├── connectors/             ← one connector per external service
│   │   ├── base.py             ← BaseConnector ABC
│   │   ├── google_calendar.py
│   │   ├── google_tasks.py
│   │   ├── gmail.py
│   │   ├── hexoplan.py
│   │   ├── weather_open_meteo.py
│   │   ├── ollama.py
│   │   └── alexa_tasks.py
│   ├── consumers/              ← RabbitMQ message consumers
│   │   ├── event_consumer.py
│   │   └── query_consumer.py
│   ├── cache.py                ← Redis abstraction
│   ├── scheduler.py            ← APScheduler background jobs
│   └── models/                 ← Pydantic schemas
├── tests/
├── scripts/
│   ├── setup_google_auth.py    ← one-time OAuth2 token setup
│   └── healthcheck.sh
└── docs/
    ├── api-spec.md             ← full API contract (shared with Huginn)
    ├── connectors.md           ← how to add a new connector
    └── deployment.md           ← Raspberry Pi 4 setup guide
```

---

## Configuration

All config via environment variables in `.env`:

```env
# Hub
HUB_API_KEY=                        # optional — leave blank to disable auth
HUB_DEBUG=false
HUB_LOG_LEVEL=INFO

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Redis
REDIS_URL=redis://redis:6379/0

# Google (OAuth2)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_TOKEN_FILE=/data/google_token.json

# Weather (Open-Meteo — no API key needed)
OPEN_METEO_LATITUDE=49.2827
OPEN_METEO_LONGITUDE=-123.1207
OPEN_METEO_TIMEZONE=America/Vancouver

# Additional named cities (comma-separated label:lat:lon)
WEATHER_CITIES=london:51.5074:-0.1278,toronto:43.6532:-79.3832

# Email (IMAP)
IMAP_HOST=imap.gmail.com
IMAP_USER=
IMAP_PASSWORD=

# Hexoplan
HEXOPLAN_API_KEY=

# Ollama (local AI)
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## API Overview

Full contract in [`docs/api-spec.md`](docs/api-spec.md).

| Endpoint | Description |
|---|---|
| `GET /v1/dashboard` | Composite — all domains in one call (optimised for Huginn) |
| `GET /v1/calendar/today` | Today's events |
| `GET /v1/calendar/week` | This week |
| `GET /v1/calendar/anniversaries` | Upcoming birthdays/anniversaries |
| `GET /v1/weather/local` | Current weather + forecast |
| `GET /v1/weather/{city}` | Named city weather |
| `GET /v1/tasks` | Aggregated tasks (filterable by source, status, due) |
| `PATCH /v1/tasks/{id}/complete` | Mark task complete in source system |
| `POST /v1/tasks` | Create task |
| `GET /v1/email/summary` | Inbox summary |
| `GET /v1/email/messages` | Message list |
| `GET /v1/health` | Hub + connector health status |

Auto-generated interactive docs available at `/docs` when running.

---

## RabbitMQ Events

External tools (IFTTT, Zapier, n8n) can publish to the `presto.events` queue to trigger actions:

```json
{
  "source": "zapier",
  "action": "refresh.calendar",
  "payload": {},
  "correlation_id": "uuid-v4",
  "timestamp": "2026-02-20T08:00:00Z"
}
```

Supported actions: `refresh.calendar`, `refresh.tasks`, `refresh.weather`, `refresh.all`, `create.task`, `query.dashboard`.

---

## CI/CD

Caduceus uses GitHub Actions for automated deployment to the Raspberry Pi 4.

**On Pull Request:** ruff lint → mypy type check → pytest → ARM64 Docker build check
**On merge to `main`:** Build ARM64 image → push to GitHub Container Registry → SSH to Pi → pull + restart → health check

Required GitHub Secrets:

| Secret | Value |
|---|---|
| `PI_HOST` | Pi 4 static IP address |
| `PI_SSH_KEY` | Private SSH key for `pi` user |
| `PI_USER` | `pi` |
| `GHCR_TOKEN` | GitHub PAT with `packages:write` |

---

## Raspberry Pi 4 Setup

See [`docs/deployment.md`](docs/deployment.md) for the full setup guide. Key points:

- 64-bit Raspberry Pi OS Lite (bookworm), headless
- NVMe HAT with Docker data root moved to `/mnt/nvme/docker`
- Static local IP via router DHCP reservation
- Caduceus deployed to `/opt/caduceus/`
- `.env` lives on the Pi only — never in the repo

---

## Adding a Connector

See [`docs/connectors.md`](docs/connectors.md). Every connector implements the `BaseConnector` ABC:

```python
class MyConnector(BaseConnector):
    async def fetch(self, params: dict) -> dict: ...
    async def health_check(self) -> bool: ...
    async def push(self, data: dict) -> bool: ...  # optional
```

---

## Mythological Context

The **Caduceus** is the winged staff carried by Hermes (Mercury) — the god of messages, travellers, and the crossing of boundaries between worlds. He carries it as he moves between the mortal world, the divine realm, and the underworld, brokering communication and passage.

The two intertwined serpents represent streams of information weaving together. The wings represent the speed of delivery.

Caduceus serves [**Huginn**](https://github.com/dreffed/huginn) — Odin's raven of Thought — by moving between the worlds of Google, weather services, and task managers, and returning with intelligence for the raven to display.

---

## Future Enhancements

- Webhook endpoint as RabbitMQ alternative for IFTTT/Zapier
- WebSocket push to Huginn (eliminate polling)
- Notion connector (tasks + pages)
- Home Assistant connector
- Spotify now-playing connector
- Adscens.io governance status connector
- **Muninn** — a companion archiving/memory service

---

## Related Projects

- [**Huginn**](https://github.com/dreffed/huginn) — the Pimoroni Presto display that consumes this API
