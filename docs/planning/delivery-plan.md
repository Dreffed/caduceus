# Caduceus Delivery Plan

> Generated: 2026-03-01
> Status: Draft — pending review

---

## Approach

The build is split into **6 phases**, each delivering a working increment that can be tested end-to-end. Dependencies flow top-down — each phase builds on the previous one. Within each phase, work items are ordered by dependency.

Production deployment is brought forward to Phase 3 so that every subsequent phase deploys and validates on real Pi 4 hardware. This means Phases 4-6 develop against the live environment rather than discovering deployment issues at the end.

---

## Phase 1 — Skeleton & Infrastructure

**Goal:** Runnable FastAPI app with Docker Compose, Redis, RabbitMQ, health endpoint, and CI pipeline. No connectors yet.

| # | Work Item | Files Created/Modified |
|---|---|---|
| 1.1 | Project scaffolding — `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `Dockerfile`, `.dockerignore` | root |
| 1.2 | `hub/config.py` — pydantic-settings `Settings` class with all env vars from spec | `hub/config.py` |
| 1.3 | `hub/main.py` — app factory, lifespan handler, CORS, API key middleware | `hub/main.py` |
| 1.4 | `hub/cache.py` — Redis abstraction (`get`, `set` with TTL, `invalidate`, `health_check`). Accepts `REDIS_URL` from config | `hub/cache.py` |
| 1.5 | `hub/connectors/base.py` — `BaseConnector` ABC (`fetch`, `health_check`, optional `push`) | `hub/connectors/base.py`, `hub/connectors/__init__.py` |
| 1.6 | `hub/dependencies.py` — FastAPI dependency factories for cache, settings, and future connectors | `hub/dependencies.py` |
| 1.7 | `hub/models/common.py` — shared Pydantic models (`DegradedResponse` mixin, `HealthStatus`) | `hub/models/common.py`, `hub/models/__init__.py` |
| 1.8 | `hub/routers/health.py` — `GET /v1/health` returning hub + cache + queue status | `hub/routers/health.py`, `hub/routers/__init__.py` |
| 1.9 | `docker-compose.yml` — hub, redis, rabbitmq services on `presto-net` | `docker-compose.yml` |
| 1.10 | `.env.example` with all config keys | `.env.example` |
| 1.11 | `tests/conftest.py` — fixtures for async test client, Redis mock, settings override | `tests/conftest.py` |
| 1.12 | `tests/test_routers/test_health.py` — health endpoint tests | `tests/test_routers/test_health.py` |
| 1.13 | `.github/workflows/ci.yml` — ruff, mypy, pytest, ARM64 docker build check | `.github/workflows/ci.yml` |
| 1.14 | `ruff.toml` and `mypy.ini` / `pyproject.toml` config sections | root config |

**Exit criteria:** `docker-compose up` starts all 3 services. `GET /v1/health` returns `{"status": "ok"}`. CI pipeline passes on a PR.

---

## Phase 2 — Weather Connector (first end-to-end slice)

**Goal:** First working connector proving the full pattern: connector -> cache -> router -> API response.

| # | Work Item | Files |
|---|---|---|
| 2.1 | `hub/models/weather.py` — Pydantic models for weather responses per spec | `hub/models/weather.py` |
| 2.2 | `hub/connectors/weather_open_meteo.py` — Open-Meteo API connector (no auth, free API). Implements `fetch` and `health_check` | `hub/connectors/weather_open_meteo.py` |
| 2.3 | Register weather connector in `hub/dependencies.py` | `hub/dependencies.py` |
| 2.4 | `hub/routers/weather.py` — `GET /v1/weather/local` and `GET /v1/weather/{city}`. Cache-first reads with `degraded` flag on upstream failure | `hub/routers/weather.py` |
| 2.5 | `hub/scheduler.py` — APScheduler setup, first job: weather cache pre-warm every 4 min | `hub/scheduler.py` |
| 2.6 | Wire scheduler into app lifespan in `hub/main.py` | `hub/main.py` |
| 2.7 | Update health endpoint to report weather connector status | `hub/routers/health.py` |
| 2.8 | `tests/test_connectors/test_weather.py` — mocked Open-Meteo responses | `tests/test_connectors/` |
| 2.9 | `tests/test_routers/test_weather.py` — endpoint tests (warm cache, cold cache, degraded) | `tests/test_routers/` |

**Exit criteria:** `GET /v1/weather/local` returns live weather data. Cache pre-warms on schedule. Stale cache served when Open-Meteo is unreachable. Tests pass.

---

## Phase 3 — Production Deployment

**Goal:** Deploy the working skeleton + weather connector to the Pi 4 with full CI/CD. Every subsequent phase merges and deploys to real hardware.

| # | Work Item | Files |
|---|---|---|
| 3.1 | `docker-compose.prod.yml` — nginx reverse proxy, no exposed RabbitMQ management port, production env settings | `docker-compose.prod.yml` |
| 3.2 | nginx config — reverse proxy to hub:8000, optional TLS | `nginx/default.conf` |
| 3.3 | `scripts/healthcheck.sh` — curl `/v1/health`, exit non-zero if not ok | `scripts/healthcheck.sh` |
| 3.4 | `.github/workflows/deploy.yml` — build ARM64 image, push to GHCR, SSH deploy to Pi, health check | `.github/workflows/deploy.yml` |
| 3.5 | `docs/deployment.md` — full Pi 4 setup guide (NVMe, Docker data root, static IP, env setup) | `docs/deployment.md` |
| 3.6 | Pi 4 environment setup — `.env` on Pi, Docker volumes, SSH key from GitHub Actions | on-device |
| 3.7 | Validate end-to-end: merge to `main` triggers build + deploy, health + weather endpoints respond from Pi IP | — |

**Exit criteria:** Merge to `main` auto-deploys to Pi 4. `GET /v1/health` and `GET /v1/weather/local` respond from Pi IP. Health check in deploy pipeline passes.

---

## Phase 4 — Google Connectors (Calendar, Tasks, Gmail)

**Goal:** OAuth2-authenticated Google connectors. Highest-complexity phase — deploys to Pi on merge.

### 4A — Google Auth Foundation

| # | Work Item | Files |
|---|---|---|
| 4A.1 | `scripts/setup_google_auth.py` — interactive OAuth2 consent flow, saves token to `/data/google_token.json` | `scripts/setup_google_auth.py` |
| 4A.2 | Shared Google auth helper — token loading, auto-refresh, error handling. Used by all Google connectors | `hub/connectors/google_auth.py` |
| 4A.3 | Run OAuth setup locally, copy token to Pi volume | on-device |

### 4B — Calendar

| # | Work Item | Files |
|---|---|---|
| 4B.1 | `hub/models/calendar.py` — event, day, week, anniversary models | `hub/models/calendar.py` |
| 4B.2 | `hub/connectors/google_calendar.py` — fetch today, week, anniversaries | `hub/connectors/google_calendar.py` |
| 4B.3 | `hub/routers/calendar.py` — 3 endpoints per spec | `hub/routers/calendar.py` |
| 4B.4 | Register in dependencies, add cache TTLs (today=2min, week=5min), add scheduler jobs | various |
| 4B.5 | Tests — connector (mocked Google API), router | `tests/` |

### 4C — Tasks

| # | Work Item | Files |
|---|---|---|
| 4C.1 | `hub/models/tasks.py` — task model with `source` prefix on IDs | `hub/models/tasks.py` |
| 4C.2 | `hub/connectors/google_tasks.py` — read, create, complete | `hub/connectors/google_tasks.py` |
| 4C.3 | `hub/routers/tasks.py` — GET (with filters), POST, PATCH complete. Initially only `google` source | `hub/routers/tasks.py` |
| 4C.4 | Tests | `tests/` |

### 4D — Gmail

| # | Work Item | Files |
|---|---|---|
| 4D.1 | `hub/models/email.py` — message summary, inbox summary | `hub/models/email.py` |
| 4D.2 | `hub/connectors/gmail.py` — IMAP-based inbox read (unread count, recent messages, flagged) | `hub/connectors/gmail.py` |
| 4D.3 | `hub/routers/email.py` — summary + messages list with pagination | `hub/routers/email.py` |
| 4D.4 | Tests | `tests/` |

**Exit criteria:** All 3 Google services return data via API on the Pi. Token auto-refreshes. Calendar, tasks, and email endpoints match spec contracts. Deploy pipeline passes.

---

## Phase 5 — Remaining Connectors & Dashboard

**Goal:** Hexoplan, Ollama connectors + the composite dashboard endpoint.

| # | Work Item | Files |
|---|---|---|
| 5.1 | `hub/connectors/hexoplan.py` — API-key-based task connector | `hub/connectors/hexoplan.py` |
| 5.2 | Update tasks router to aggregate Google Tasks + Hexoplan, with `source` filter | `hub/routers/tasks.py` |
| 5.3 | `hub/connectors/ollama.py` — local Ollama connector for AI queries | `hub/connectors/ollama.py` |
| 5.4 | `hub/models/dashboard.py` — composite dashboard response model | `hub/models/dashboard.py` |
| 5.5 | `hub/routers/dashboard.py` — `GET /v1/dashboard` composing all domains, reporting `degraded_sources` | `hub/routers/dashboard.py` |
| 5.6 | Update health endpoint to report all connector statuses | `hub/routers/health.py` |
| 5.7 | `docs/api-spec.md` — finalized API contract document (shared with huginn) | `docs/api-spec.md` |
| 5.8 | `docs/connectors.md` — how to add a new connector | `docs/connectors.md` |
| 5.9 | Tests for all new items | `tests/` |

**Note:** `alexa_tasks` is deferred — marked as high complexity in the spec with investigation needed. Add as a follow-on when auth approach is determined.

**Exit criteria:** `GET /v1/dashboard` returns the full composite payload from Pi. Tasks endpoint aggregates multiple sources. API contract docs finalized.

---

## Phase 6 — RabbitMQ Consumers

**Goal:** Event-driven ingestion and query handling via RabbitMQ.

| # | Work Item | Files |
|---|---|---|
| 6.1 | `hub/models/queue.py` — message envelope model (`source`, `action`, `payload`, `reply_to`, `correlation_id`) | `hub/models/queue.py` |
| 6.2 | `hub/consumers/base_consumer.py` — base class: connection management, channel setup, graceful shutdown | `hub/consumers/base_consumer.py` |
| 6.3 | `hub/consumers/event_consumer.py` — listens on `presto.events`, dispatches by `action` field: `refresh.*` invalidates cache, `create.task` calls connector push | `hub/consumers/event_consumer.py` |
| 6.4 | `hub/consumers/query_consumer.py` — listens on `presto.requests`, handles `query.*` actions, publishes response to `reply_to` queue | `hub/consumers/query_consumer.py` |
| 6.5 | RabbitMQ exchange/queue setup — `presto` topic exchange, 3 queues with routing keys per spec | `hub/consumers/` or app startup |
| 6.6 | Wire consumers into app lifespan (start as background tasks, graceful shutdown) | `hub/main.py` |
| 6.7 | Update health endpoint to report queue connectivity | `hub/routers/health.py` |
| 6.8 | Tests — mocked RabbitMQ, message routing, nack on failure | `tests/test_consumers/` |

**Exit criteria:** Publishing a `refresh.calendar` message to `presto.events` on Pi invalidates the cache and triggers re-fetch. `query.dashboard` returns dashboard JSON to reply queue. Full system operational on Pi.

---

## Dependency Graph

```
Phase 1 (Skeleton)
    │
    ▼
Phase 2 (Weather) ─── proves the full connector pattern
    │
    ▼
Phase 3 (Production) ── deploy to Pi early, validate on real hardware
    │
    ▼
Phase 4 (Google) ──── highest complexity, deployed to Pi on merge
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 5 (Dashboard)   Phase 6 (RabbitMQ)
    └──────────┬───────────┘
               ▼
           MVP Complete
```

Phases 5 and 6 are independent of each other and can be parallelized. Both deploy to Pi via the pipeline established in Phase 3.

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Async framework | FastAPI + uvicorn | Spec requirement. Natural fit for IO-bound connector calls |
| HTTP client | `httpx` (async) | Async-native, used for connectors calling external APIs |
| Google API | `google-api-python-client` + `google-auth-oauthlib` | Official SDK, handles token refresh |
| Gmail | IMAP via `aioimaplib` | Spec calls for IMAP, avoids Gmail API quota limits |
| RabbitMQ client | `aio-pika` | Async RabbitMQ client, well-maintained |
| Redis client | `redis[hiredis]` (async) | Official async Redis client with hiredis parser for speed |
| Scheduler | `APScheduler` 3.x | Spec requirement. Lightweight, in-process |
| Testing | `pytest` + `pytest-asyncio` + `httpx` | Spec requirement. `httpx.AsyncClient` for testing FastAPI |
| Linting | `ruff` | Fast, replaces flake8/isort/black. Spec requirement |
| Type checking | `mypy` (strict mode) | Spec requirement |
| Serialization | Pydantic v2 | Already bundled with FastAPI. Models double as API docs |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Google OAuth token expires and auto-refresh fails | Calendar/Tasks/Gmail all go down | Medium | Health endpoint flags it. `degraded` flag on responses. Alert via deploy health check |
| Open-Meteo API changes or goes down | Weather data unavailable | Low | Return stale cache. Service is free/stable |
| Alexa Tasks auth is infeasible | One task source missing | Medium | Deferred to post-MVP. Tasks still aggregates Google + Hexoplan |
| ARM64 Docker build breaks for a dependency | Can't deploy to Pi | Low | CI validates ARM64 build on every PR |
| RabbitMQ message poison loop | Consumer crashes repeatedly | Medium | Nack without requeue. Dead-letter queue (DLQ) for inspection |
| Redis memory pressure on Pi 4 | Cache evictions, slow responses | Low | Small dataset (personal data). Set `maxmemory` with `allkeys-lru` policy |

---

## Deferred Items (Post-MVP)

These are from the spec's "Open Questions / Future Enhancements" section and are explicitly out of scope for the initial delivery:

- Webhook endpoint (`POST /v1/webhook/{source}`) as RabbitMQ alternative
- WebSocket push to Presto
- Notion connector
- Home Assistant connector
- Spotify now-playing connector
- Adscens.io status connector
- Multi-location weather (partially addressed — `GET /v1/weather/{city}` supports named cities)
- SMS/WhatsApp summary via Twilio
- Alexa Tasks connector (pending auth investigation)
- n8n orchestration layer
- Watchtower

---

## File Inventory (Full Build)

For reference — the complete set of files that will exist after all 6 phases:

```
caduceus/
├── .env.example
├── .github/workflows/ci.yml
├── .github/workflows/deploy.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── ruff.toml
├── hub/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── cache.py
│   ├── dependencies.py
│   ├── scheduler.py
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── google_auth.py
│   │   ├── google_calendar.py
│   │   ├── google_tasks.py
│   │   ├── gmail.py
│   │   ├── hexoplan.py
│   │   ├── weather_open_meteo.py
│   │   └── ollama.py
│   ├── consumers/
│   │   ├── __init__.py
│   │   ├── base_consumer.py
│   │   ├── event_consumer.py
│   │   └── query_consumer.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── calendar.py
│   │   ├── tasks.py
│   │   ├── email.py
│   │   ├── weather.py
│   │   ├── dashboard.py
│   │   └── queue.py
│   └── routers/
│       ├── __init__.py
│       ├── health.py
│       ├── weather.py
│       ├── calendar.py
│       ├── tasks.py
│       ├── email.py
│       └── dashboard.py
├── tests/
│   ├── conftest.py
│   ├── test_routers/
│   │   ├── test_health.py
│   │   ├── test_weather.py
│   │   ├── test_calendar.py
│   │   ├── test_tasks.py
│   │   ├── test_email.py
│   │   └── test_dashboard.py
│   ├── test_connectors/
│   │   ├── test_weather.py
│   │   ├── test_google_calendar.py
│   │   ├── test_google_tasks.py
│   │   ├── test_gmail.py
│   │   ├── test_hexoplan.py
│   │   └── test_ollama.py
│   └── test_consumers/
│       ├── test_event_consumer.py
│       └── test_query_consumer.py
├── scripts/
│   ├── setup_google_auth.py
│   └── healthcheck.sh
├── nginx/
│   └── default.conf
└── docs/
    ├── api-spec.md
    ├── connectors.md
    ├── deployment.md
    └── planning/
        └── delivery-plan.md   ← this file
```
