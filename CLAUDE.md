# CLAUDE.md — caduceus Project

## Project Identity
**Name:** caduceus  
**Purpose:** Personal integration hub — aggregates calendar, tasks, email, weather, and AI services into a single REST API consumed by the Presto device and other clients.  
**Target Runtime:** Docker (docker-compose) on Raspberry Pi 4 with NVMe storage  
**Language:** Python 3.11+  
**Framework:** FastAPI  
**CI/CD:** GitHub Actions → deploy to Raspberry Pi 4 via SSH

---

## Architecture Summary

```
caduceus/
├── docker-compose.yml         ← all services
├── docker-compose.prod.yml    ← prod overrides (Pi 4)
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml             ← lint + test on PR
│       └── deploy.yml         ← deploy to Pi on merge to main
├── hub/                       ← main FastAPI application
│   ├── main.py                ← app factory, router registration
│   ├── config.py              ← settings via pydantic-settings
│   ├── dependencies.py        ← FastAPI dependency injection
│   ├── routers/               ← one router per domain
│   │   ├── calendar.py
│   │   ├── tasks.py
│   │   ├── email.py
│   │   ├── weather.py
│   │   ├── dashboard.py
│   │   └── health.py
│   ├── connectors/            ← one connector per external service
│   │   ├── base.py            ← BaseConnector ABC
│   │   ├── google_calendar.py
│   │   ├── google_tasks.py
│   │   ├── gmail.py
│   │   ├── hexoplan.py
│   │   ├── weather_open_meteo.py
│   │   ├── ollama.py
│   │   └── alexa_tasks.py
│   ├── consumers/             ← RabbitMQ message consumers
│   │   ├── base_consumer.py
│   │   ├── event_consumer.py  ← handles IFTTT/Zapier events
│   │   └── query_consumer.py  ← handles query requests via queue
│   ├── cache.py               ← Redis abstraction layer
│   ├── scheduler.py           ← APScheduler background refresh jobs
│   └── models/                ← Pydantic models
│       ├── calendar.py
│       ├── tasks.py
│       ├── email.py
│       ├── weather.py
│       └── queue.py
├── tests/
│   ├── conftest.py
│   ├── test_routers/
│   ├── test_connectors/
│   └── test_consumers/
├── scripts/
│   ├── setup_google_auth.py   ← one-time OAuth2 token setup
│   └── healthcheck.sh
└── docs/
    ├── api-spec.md            ← API contract (shared with huginn)
    ├── connectors.md          ← how to add a new connector
    └── deployment.md          ← Pi 4 setup guide
```

---

## Services (docker-compose)

| Service | Image | Port | Purpose |
|---|---|---|---|
| `hub` | custom (./hub) | 8000 | FastAPI application |
| `rabbitmq` | rabbitmq:3-management | 5672, 15672 | Message broker + management UI |
| `redis` | redis:7-alpine | 6379 | Cache layer |
| `nginx` | nginx:alpine | 80, 443 | Reverse proxy (prod only) |

All services communicate on an internal Docker network `presto-net`. Only `nginx` (prod) and `hub` (dev) expose ports to the host.

---

## Key Coding Principles

### Connector Pattern
Every external service integration is a `BaseConnector` subclass:

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseConnector(ABC):
    @abstractmethod
    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod  
    async def health_check(self) -> bool: ...

    # Optional — only connectors that support write implement this
    async def push(self, data: dict[str, Any]) -> bool:
        raise NotImplementedError
```

Connectors are instantiated once at startup and injected via FastAPI's dependency system. They are **not** singletons created globally — use `@lru_cache` on the factory function.

### Caching Strategy
All connector `fetch()` calls go through the cache layer. TTLs are defined per connector:

```python
CACHE_TTL = {
    "weather": 300,        # 5 min
    "calendar_today": 120, # 2 min  
    "calendar_week": 300,  # 5 min
    "tasks": 120,          # 2 min
    "email_summary": 180,  # 3 min
    "dashboard": 60,       # 1 min
}
```

Cache keys follow the pattern: `{domain}:{endpoint}:{user_id_or_hash_of_params}`

### Scheduler Jobs
APScheduler pre-warms the cache on a schedule slightly shorter than the TTL. This ensures the Presto always hits warm cache rather than waiting on upstream APIs.

### Queue Message Routing
The event consumer reads from `presto.events` queue. Messages are routed by `action` field:

| Action | Handler |
|---|---|
| `refresh.calendar` | Invalidate calendar cache, re-fetch |
| `refresh.tasks` | Invalidate tasks cache, re-fetch |
| `notify` | (future) push notification |
| `create.task` | Call task connector `push()` |
| `query.*` | Return data to `reply_to` queue |

---

## Configuration (pydantic-settings)

All config via environment variables (`.env` file in dev, Docker secrets or env in prod):

```
# Hub
HUB_API_KEY=
HUB_DEBUG=false
HUB_LOG_LEVEL=INFO

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Redis
REDIS_URL=redis://redis:6379/0

# Google
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_TOKEN_FILE=/data/google_token.json  # persisted volume

# Weather
OPEN_METEO_LATITUDE=
OPEN_METEO_LONGITUDE=
OPEN_METEO_TIMEZONE=America/Vancouver

# Email
IMAP_HOST=
IMAP_USER=
IMAP_PASSWORD=

# Hexoplan
HEXOPLAN_API_KEY=

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## Google OAuth2 Setup

Google Calendar, Tasks, and Gmail require OAuth2. Tokens are obtained once via the helper script and stored in a Docker volume:

```bash
python scripts/setup_google_auth.py
# Opens browser for consent
# Saves token to /data/google_token.json
```

The connector auto-refreshes the token using `google-auth-oauthlib`. The `/data` path is a named Docker volume persisted on the Pi's NVMe.

---

## API Versioning

All routes are prefixed `/v1/`. When breaking changes are needed, add `/v2/` routers — do not modify existing `/v1/` contracts. The `huginn` project pins to a specific API version.

---

## Error Handling

- All connector failures are caught and logged — they never propagate as 500s unless the router explicitly wants that
- Routers return stale cached data + a `degraded: true` flag when a connector is down
- Health endpoint reports per-connector status
- RabbitMQ consumer failures are logged and the message is nacked (not requeued by default to avoid poison message loops)

---

## Testing Standards

- Use `pytest` + `pytest-asyncio` + `httpx` (async test client)
- Connectors must have mocked tests — no live API calls in CI
- Use `pytest-cov` — aim for 80%+ coverage on routers and connectors
- `tests/conftest.py` provides fixtures for Redis mock, RabbitMQ mock, and FastAPI test client

Run locally:
```bash
docker-compose run --rm hub pytest tests/ -v --cov=hub
```

---

## CI/CD (GitHub Actions)

### On Pull Request (`ci.yml`)
1. `ruff` lint check
2. `mypy` type check  
3. `pytest` full test suite
4. Docker build check (arm64 target)

### On Merge to `main` (`deploy.yml`)
1. Build Docker image for `linux/arm64`
2. Push to GitHub Container Registry (`ghcr.io`)
3. SSH to Pi 4 → `docker-compose pull && docker-compose up -d`
4. Run `healthcheck.sh` — fail deployment if hub doesn't return healthy within 30s

**Pi 4 SSH access:** GitHub Actions secret `PI_SSH_KEY` + `PI_HOST`  
**Registry auth:** `GHCR_TOKEN` GitHub Actions secret

---

## Raspberry Pi 4 Deployment Notes

- OS: Raspberry Pi OS Lite 64-bit (bookworm)
- NVMe via PCIe HAT — Docker data root moved to NVMe (`/mnt/nvme/docker`)
- Static local IP assigned via router DHCP reservation
- Docker and docker-compose installed via official install script
- `deploy.yml` assumes user `pi` with passwordless sudo for `docker` commands
- Watchtower is NOT used — explicit pull-and-restart via CI/CD only

See `docs/deployment.md` for full Pi 4 setup walkthrough.

---

## Adding a New Connector

See `docs/connectors.md`. Short version:
1. Create `hub/connectors/{name}.py` implementing `BaseConnector`
2. Add config fields to `hub/config.py`
3. Register in `hub/dependencies.py`
4. Add router in `hub/routers/{domain}.py`
5. Add cache TTL in `hub/cache.py`
6. Add scheduler job in `hub/scheduler.py`
7. Write tests in `tests/test_connectors/test_{name}.py`
8. Document endpoint in `docs/api-spec.md`

---

## Related Project

See `huginn` — the MicroPython Presto client that consumes this API. The `docs/api-spec.md` in this repo is the contract both projects must honour.
