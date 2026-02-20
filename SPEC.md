# Project Spec — caduceus

## Overview

A Dockerised personal integration hub running on a Raspberry Pi 4 with NVMe storage. It aggregates data from Google (Calendar, Tasks, Gmail), weather services, task management apps (Hexoplan, Alexa), and AI tools (Ollama), exposing a simple REST API and consuming a RabbitMQ event queue. The primary consumer is the Presto device, but the hub is designed as a general-purpose personal data API.

---

## Goals

- Single REST API for all personal data needs (calendar, tasks, email, weather)
- Decouple external OAuth2/API complexity from consuming devices
- Event-driven ingestion via RabbitMQ (IFTTT, Zapier, n8n can push events)
- Redis caching for fast responses and resilience during upstream outages
- Proactive background refresh — data is warm before it's requested
- CI/CD pipeline — push to `main` auto-deploys to Raspberry Pi 4
- ARM64-compatible Docker images throughout

---

## Non-Goals

- Not a general-purpose automation engine (use n8n/Zapier for that)
- Not a notification push system (for now — future enhancement)
- Not multi-user (single-person personal hub)
- No frontend UI (API only; RabbitMQ management UI via port 15672 is the only web UI)

---

## API Specification

### Base

```
Base URL:  http://{pi-ip}:8000
Version:   /v1/
Auth:      X-API-Key header (optional, controlled by HUB_API_KEY env var)
Format:    application/json throughout
```

---

### Calendar

#### GET /v1/calendar/today
Returns today's events.

```json
{
  "date": "2026-02-20",
  "day_name": "Friday",
  "events": [
    {
      "id": "abc123",
      "time": "09:00",
      "end_time": "09:30",
      "title": "Team standup",
      "location": "Zoom",
      "calendar": "Work",
      "all_day": false
    }
  ],
  "cached_at": "2026-02-20T08:55:00Z",
  "degraded": false
}
```

#### GET /v1/calendar/week
Returns the current week (Mon–Sun).

```json
{
  "week_start": "2026-02-16",
  "days": [
    {
      "date": "2026-02-16",
      "day_name": "Monday",
      "events": [...]
    }
  ],
  "cached_at": "...",
  "degraded": false
}
```

#### GET /v1/calendar/anniversaries
Returns recurring annual events (birthdays, anniversaries) within the next 30 days.

```json
{
  "anniversaries": [
    {
      "date": "2026-02-25",
      "days_away": 5,
      "title": "Sarah's Birthday",
      "type": "birthday"
    }
  ]
}
```

---

### Tasks

#### GET /v1/tasks
Returns all tasks aggregated from all connected sources.

Query params:
- `status` — `all` (default) | `pending` | `completed`
- `source` — `all` (default) | `google` | `hexoplan` | `alexa`
- `due` — `all` (default) | `today` | `overdue` | `this_week`

```json
{
  "tasks": [
    {
      "id": "gt:abc123",
      "source": "google",
      "title": "Review architecture document",
      "due": "2026-02-20",
      "done": false,
      "overdue": false,
      "notes": "Focus on section 3"
    }
  ],
  "counts": {
    "total": 12,
    "pending": 9,
    "overdue": 2
  },
  "cached_at": "...",
  "degraded": false
}
```

#### PATCH /v1/tasks/{id}/complete
Marks a task complete in its source system. `id` format: `{source}:{native_id}`.

```json
{ "done": true, "completed_at": "2026-02-20T14:30:00Z" }
```

#### POST /v1/tasks
Creates a task in the specified source system.

```json
{
  "title": "Write blog post",
  "due": "2026-02-25",
  "source": "google",
  "notes": "Optional"
}
```

---

### Weather

#### GET /v1/weather/local
Returns current weather for the configured home location.

```json
{
  "location": "Vancouver, BC",
  "current": {
    "temp_c": 8.2,
    "feels_like_c": 5.1,
    "condition": "Partly cloudy",
    "condition_code": "partly_cloudy",
    "humidity_pct": 76,
    "wind_kmh": 14,
    "wind_direction": "SW",
    "uv_index": 2
  },
  "forecast": [
    {
      "date": "2026-02-21",
      "day_name": "Saturday",
      "high_c": 10,
      "low_c": 4,
      "condition": "Rain",
      "condition_code": "rain",
      "precip_mm": 8.2
    }
  ],
  "cached_at": "...",
  "degraded": false
}
```

#### GET /v1/weather/{city}
Same shape as above but for a named city. Supported cities configured in hub config. Examples: `london`, `vancouver`, `toronto`.

---

### Email

#### GET /v1/email/summary
Returns inbox summary.

```json
{
  "unread_count": 4,
  "flagged_count": 1,
  "recent": [
    {
      "id": "msg:abc",
      "from_name": "David A.",
      "from_email": "david@example.com",
      "subject": "Re: Architecture Review",
      "preview": "Looks good, just one comment on...",
      "received_at": "2026-02-20T11:22:00Z",
      "read": false,
      "flagged": true
    }
  ],
  "cached_at": "...",
  "degraded": false
}
```

#### GET /v1/email/messages
Full message list with pagination. Query params: `limit` (default 20), `offset`, `filter` (all|unread|flagged).

---

### Dashboard

#### GET /v1/dashboard
Composite endpoint — returns all domains in a single call. Optimised for the Presto device's home screen.

```json
{
  "calendar": {
    "today": { ... },         // same as /calendar/today
    "next_event": { ... }     // first upcoming event today
  },
  "weather": {
    "current": { ... },       // same as /weather/local current block
    "tomorrow": { ... }       // tomorrow's forecast day
  },
  "tasks": {
    "pending_count": 9,
    "overdue_count": 2,
    "next_due": { ... }       // soonest due task
  },
  "email": {
    "unread_count": 4,
    "flagged_count": 1
  },
  "generated_at": "2026-02-20T14:00:00Z",
  "degraded_sources": []      // list any sources with errors
}
```

---

### Health

#### GET /v1/health
Returns hub and connector health status.

```json
{
  "status": "ok",             // ok | degraded | error
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "connectors": {
    "google_calendar": "ok",
    "google_tasks": "ok",
    "gmail": "ok",
    "weather": "ok",
    "hexoplan": "error",
    "alexa_tasks": "ok",
    "ollama": "ok"
  },
  "cache": "ok",
  "queue": "ok"
}
```

---

## RabbitMQ Queue Design

### Exchange: `presto`
Type: `topic`

### Queues

| Queue | Routing Key | Publisher | Consumer |
|---|---|---|---|
| `presto.events` | `event.*` | IFTTT, Zapier, n8n | Hub event consumer |
| `presto.requests` | `request.*` | Any client | Hub query consumer |
| `presto.responses` | `response.*` | Hub | Requesting client |

### Message Envelope

```json
{
  "source": "zapier",
  "action": "refresh.calendar",
  "payload": {},
  "reply_to": "presto.responses",
  "correlation_id": "uuid-v4",
  "timestamp": "ISO8601"
}
```

### Supported Actions

| Action | Payload | Effect |
|---|---|---|
| `refresh.calendar` | `{}` | Invalidate + re-fetch calendar cache |
| `refresh.tasks` | `{}` | Invalidate + re-fetch tasks cache |
| `refresh.weather` | `{}` | Invalidate + re-fetch weather cache |
| `refresh.all` | `{}` | Invalidate all caches |
| `create.task` | `{title, due, source}` | Create task via connector |
| `notify` | `{message, priority}` | (future) Push notification to Presto |
| `query.dashboard` | `{}` | Return dashboard JSON to `reply_to` |

---

## Docker Services Detail

### hub (FastAPI app)
```yaml
build: ./hub
image: ghcr.io/{user}/caduceus:latest
platform: linux/arm64
restart: unless-stopped
ports:
  - "8000:8000"
volumes:
  - hub_data:/data          # Google OAuth tokens, persistent data
environment:
  - (from .env)
depends_on:
  - rabbitmq
  - redis
```

### rabbitmq
```yaml
image: rabbitmq:3-management
platform: linux/arm64
restart: unless-stopped
ports:
  - "5672:5672"
  - "15672:15672"   # management UI — internal network only in prod
volumes:
  - rabbitmq_data:/var/lib/rabbitmq
```

### redis
```yaml
image: redis:7-alpine
platform: linux/arm64
restart: unless-stopped
volumes:
  - redis_data:/data
command: redis-server --appendonly yes    # persistence
```

---

## CI/CD Pipeline

### `ci.yml` — runs on every PR

```
Trigger: pull_request → main

Steps:
1. Checkout
2. Set up Python 3.11
3. pip install -r requirements-dev.txt
4. ruff check hub/
5. mypy hub/
6. pytest tests/ --cov=hub --cov-report=xml
7. docker buildx build --platform linux/arm64 -t test-build .
   (build only, no push — validates Dockerfile for ARM64)
```

### `deploy.yml` — runs on merge to main

```
Trigger: push → main

Steps:
1. Checkout
2. Log in to GitHub Container Registry
3. docker buildx build --platform linux/arm64 
   --push -t ghcr.io/{user}/caduceus:latest .
4. SSH to Pi 4:
   a. cd /opt/caduceus
   b. docker-compose pull
   c. docker-compose up -d
   d. sleep 15
   e. bash scripts/healthcheck.sh  (curl /v1/health, fail if not ok)
5. On failure: notify (email or GitHub issue)
```

**Required GitHub Secrets:**
- `PI_HOST` — Pi 4 static IP
- `PI_SSH_KEY` — private key for `pi` user
- `PI_USER` — typically `pi`
- `GHCR_TOKEN` — GitHub PAT with `packages:write`

---

## Raspberry Pi 4 Setup Checklist

See `docs/deployment.md` for full guide. Summary:

- [ ] Pi OS Lite 64-bit (bookworm) — headless install
- [ ] NVMe PCIe HAT installed, NVMe formatted as ext4 at `/mnt/nvme`
- [ ] Docker data root set to `/mnt/nvme/docker` in `/etc/docker/daemon.json`
- [ ] Docker + docker-compose installed (official script)
- [ ] Static IP via router DHCP reservation (or set in `/etc/dhcpcd.conf`)
- [ ] SSH key from GitHub Actions added to `~/.ssh/authorized_keys`
- [ ] `/opt/caduceus` directory created, owned by `pi`
- [ ] `.env` file created at `/opt/caduceus/.env` (never in repo)
- [ ] `docker-compose.prod.yml` deployed with nginx and no exposed RabbitMQ port
- [ ] Google OAuth2 setup: `python scripts/setup_google_auth.py` run once locally, token copied to Pi volume

---

## Connectors — Implementation Priority

| Priority | Connector | Auth Type | Complexity |
|---|---|---|---|
| 1 | `weather_open_meteo` | None (free, no key) | Low |
| 2 | `google_calendar` | OAuth2 | Medium |
| 3 | `google_tasks` | OAuth2 (reuses calendar token) | Low |
| 4 | `gmail` | OAuth2 (reuses token) | Medium |
| 5 | `hexoplan` | API Key | Low |
| 6 | `ollama` | None (local) | Low |
| 7 | `alexa_tasks` | (investigate — may need workaround) | High |

---

## Open Questions / Future Enhancements

- [ ] Webhook endpoint (POST `/v1/webhook/{source}`) as alternative to RabbitMQ for IFTTT/Zapier
- [ ] WebSocket endpoint for push to Presto (avoid polling)
- [ ] Notion connector (David uses Notion extensively — surface tasks/pages)
- [ ] Home Assistant connector
- [ ] Spotify now-playing connector
- [ ] Adscens.io status connector
- [ ] Multi-location weather (Vancouver + London)
- [ ] SMS/WhatsApp summary via Twilio connector
- [ ] n8n as an additional orchestration layer (runs in Docker alongside hub)
- [ ] Watchtower for automatic image updates (lower priority — prefer explicit CI/CD)
