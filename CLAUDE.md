# CloudDrop

Multi-tenant SaaS file management platform. React 19 frontend, FastAPI backend, PostgreSQL, AWS S3/CloudFront, Docker.

## Project Structure

```
backend/         FastAPI Python backend (uv-managed)
  app/api/       Route handlers (v1/ prefix)
  app/core/      Config, security (JWT/bcrypt), AWS helpers
  app/db/        SQLAlchemy async engine + session
  app/models/    ORM models (User, File, Share)
  app/schemas/   Pydantic request/response schemas
  app/services/  Business logic (FileService, ShareService)
  tests/         pytest async tests (SQLite-backed)
  alembic/       Database migrations
frontend/        React 19 + Vite 6 + TypeScript
  src/api/       Axios client + TanStack Query hooks
  src/components/ UI components (shadcn/ui style) + feature components
  src/pages/     Login, Register, Dashboard, ShareView
  src/stores/    Zustand auth store
```

## Commands

### Backend
```bash
cd backend
uv sync --extra dev          # Install all deps
uv run pytest -v             # Run tests (17 tests, SQLite, no Docker needed)
uv run fastapi dev app/main.py  # Dev server on :8000
uv run alembic upgrade head  # Run migrations (requires PostgreSQL)
```

### Frontend
```bash
cd frontend
npm install                  # Install deps
npm run dev                  # Dev server on :5173
npm run build                # Production build (tsc + vite)
npx tsc -b --noEmit          # Type check only
```

### Docker
```bash
cp .env.example .env         # Configure env vars first
docker compose up --build    # Dev (hot reload)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build  # Prod
```

## Architecture Decisions

- **bcrypt directly** (not passlib) — passlib is unmaintained and incompatible with bcrypt 5.x on Python 3.14
- **SQLAlchemy generic `Uuid` type** with Python-side `default=uuid.uuid4` — keeps models portable across PostgreSQL (prod) and SQLite (tests)
- **Tests use SQLite via aiosqlite** — zero infrastructure, fast, no Docker needed for testing
- **Tailwind CSS v4** — uses `@import "tailwindcss"` in CSS + `@tailwindcss/vite` plugin (NOT PostCSS, NOT `@tailwind` directives)
- **Vite pinned to v6** — v8 not yet supported by `@tailwindcss/vite`
- **Custom shadcn/ui components** — hand-written minimal components in `src/components/ui/`, not installed via CLI
- **JWT stateless auth** — access + refresh tokens via `python-jose`, HS256 algorithm
- **Direct S3 upload** — browser uploads to presigned PUT URLs, backend never handles file bytes
- **CloudFront signed URLs** — all file delivery through CDN with RSA-signed expiring URLs

## Code Conventions

- Backend: SQLAlchemy 2.x `Mapped[]` + `mapped_column()` style, `async_sessionmaker(expire_on_commit=False)`
- Backend: Layered architecture — routes call services, services call DB/AWS, never skip layers
- Backend: All user-scoped queries filter by `owner_id` in the service layer
- Backend: Pydantic v2 with `ConfigDict(from_attributes=True)` for ORM models
- Frontend: `verbatimModuleSyntax` enabled — use `import type { X }` for type-only imports
- Frontend: `@/*` path alias maps to `./src/*`
- Frontend: `cn()` utility from `@/lib/utils` for conditional Tailwind classes

## API Routes (21 total)

All under `/api/v1`:
- Auth: `POST /auth/register`, `/login`, `/refresh`, `/logout`
- Users: `GET /users/me`, `PATCH /users/me`
- Files: `POST /files/upload-url`, `PATCH /files/{id}/confirm`, `GET /files`, `GET /files/{id}`, `DELETE /files/{id}`
- Shares: `POST /shares`, `GET /shares`, `DELETE /shares/{id}`, `GET /shares/{id}/url`
- Public: `GET /public/shares/{id}` (no auth)
- Health: `GET /health`

## Testing

- Mock AWS calls at the **import site** (e.g., `app.api.v1.files.generate_presigned_upload_url`), not the definition site
- `conftest.py` provides `async_client` and `auth_headers` fixtures
- `asyncio_mode = "auto"` in pyproject.toml — no need for `@pytest.mark.asyncio`

## Environment Variables

See `.env.example` for all 14 required vars (PostgreSQL, JWT, AWS S3, CloudFront).
