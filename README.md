# CloudDrop

A production-grade SaaS file management platform with direct-to-S3 uploads and CloudFront CDN delivery. Built with React 19, FastAPI, PostgreSQL, and Docker.

## Features

- **Direct Browser-to-S3 Uploads** — Files upload directly from the browser to S3 via presigned PUT URLs. The backend never touches file bytes, enabling uploads of any size with zero server bandwidth cost.
- **CloudFront CDN Delivery** — All file downloads go through CloudFront signed URLs with configurable expiry (1h, 24h, 7d). The S3 bucket is fully private — no public access.
- **Secure Sharing** — Generate time-limited share links for any file. Links can be revoked instantly. Access counts are tracked per share.
- **Multi-Tenant Isolation** — Every query is scoped to the authenticated user's `owner_id` at the service layer. No data leaks between accounts.
- **Storage Quotas** — Per-user storage limits (default 5 GB) enforced at upload time with real-time usage tracking.
- **JWT Authentication** — Stateless access + refresh token flow with automatic token refresh on the frontend. No session storage needed.
- **Drag-and-Drop UI** — Dashboard with drag-and-drop file uploads, real-time progress bars, file management, and responsive grid layout.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                        Browser                            │
│               React 19 SPA (Vite :5173)                   │
└──────────────┬───────────────────────────────────────────┘
               │ /api/* (proxied)
               ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Backend (:8000)                       │
│   Auth · File Metadata · Presigned URL Gen · Shares       │
└────────┬─────────────────────────┬────────────────────────┘
         │ SQL (asyncpg)           │ boto3
         ▼                         ▼
┌────────────────┐       ┌─────────────────────────────────┐
│  PostgreSQL 16  │       │           AWS S3 Bucket          │
│  (metadata,     │       │  (private, OAC, no public URLs)  │
│   users,        │       └──────────────┬──────────────────┘
│   shares)       │                      │ Origin (OAC only)
└────────────────┘                      ▼
                            ┌───────────────────────┐
                            │    AWS CloudFront      │
                            │  (Signed URLs, HTTPS,  │
                            │   global edge cache)   │
                            └───────────────────────┘
```

### Upload Flow

```
1. Browser  →  POST /api/v1/files/upload-url  →  FastAPI
               { filename, size, mime_type }

2. FastAPI  →  generates presigned PUT URL via boto3
               creates file record (status="pending")
               returns { upload_url, file_id }

3. Browser  →  PUT {upload_url}  →  S3 directly
               (no file bytes pass through the backend)

4. Browser  →  PATCH /api/v1/files/{file_id}/confirm  →  FastAPI
               updates status="active", increments storage_used
```

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + TypeScript + Vite | React 19, Vite 6 |
| UI | Custom shadcn/ui components + Tailwind CSS | Tailwind v4 |
| State / Data | TanStack Query | v5 |
| Auth State | Zustand | v5 |
| Routing | React Router DOM | v7 |
| HTTP Client | Axios (with JWT interceptors) | v1 |
| Backend | FastAPI + Pydantic v2 | FastAPI 0.135 |
| ORM | SQLAlchemy 2 (async) + asyncpg | SQLAlchemy 2.x |
| Migrations | Alembic (async) | 1.x |
| Database | PostgreSQL | 16-alpine |
| Object Storage | AWS S3 (presigned PUT) | boto3 |
| CDN | AWS CloudFront (RSA signed URLs) | — |
| Auth | JWT (python-jose) + bcrypt | HS256 |
| Package Manager | uv (backend), npm (frontend) | — |
| Containers | Docker + Docker Compose | Multi-stage builds |

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- AWS account with S3 bucket and CloudFront distribution ([setup guide](#aws-setup))

### 1. Clone and configure

```bash
git clone https://github.com/your-username/cloud-drop.git
cd cloud-drop
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# PostgreSQL
POSTGRES_USER=clouddrop
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=clouddrop_db

# JWT
SECRET_KEY=generate-a-long-random-string-here

# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
CLOUDFRONT_DOMAIN=d1234abcd.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID=APKA...
CLOUDFRONT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

### 2. Start with Docker Compose

```bash
# Development (hot reload on both backend and frontend)
docker compose up --build

# Run database migrations
docker compose exec backend alembic upgrade head
```

The app is now running:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs

### 3. Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

In production, the frontend is served via Nginx on port 80 with `/api` requests proxied to the backend.

## Local Development (without Docker)

### Backend

```bash
cd backend
uv sync --extra dev              # Install dependencies
uv run alembic upgrade head      # Run migrations (needs PostgreSQL)
uv run fastapi dev app/main.py   # Start dev server on :8000
```

### Frontend

```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start Vite dev server on :5173 (proxies /api to :8000)
```

## API Reference

All endpoints are under `/api/v1`. Full interactive docs available at `/docs` (Swagger UI).

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | None | Create account, returns tokens |
| POST | `/auth/login` | None | Returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh token | Rotate access token |
| POST | `/auth/logout` | Bearer | Logout (stateless acknowledgment) |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/me` | Bearer | Get current user profile + storage usage |
| PATCH | `/users/me` | Bearer | Update profile |

### Files

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/files/upload-url` | Bearer | Get S3 presigned PUT URL |
| PATCH | `/files/{id}/confirm` | Bearer | Mark upload as complete |
| GET | `/files` | Bearer | List user's files (paginated) |
| GET | `/files/{id}` | Bearer | Get file metadata |
| DELETE | `/files/{id}` | Bearer | Soft delete file |

### Shares

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/shares` | Bearer | Create share link with TTL |
| GET | `/shares` | Bearer | List user's shares |
| DELETE | `/shares/{id}` | Bearer | Revoke a share link |
| GET | `/shares/{id}/url` | Bearer | Regenerate signed download URL |
| GET | `/public/shares/{id}` | None | Public share page (metadata + signed URL) |

### Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Returns `{"status": "ok"}` |

## Testing

Backend tests run against SQLite (no Docker or PostgreSQL needed):

```bash
cd backend
uv run pytest -v
```

```
tests/test_auth.py::test_register                    PASSED
tests/test_auth.py::test_register_duplicate_email     PASSED
tests/test_auth.py::test_login                        PASSED
tests/test_auth.py::test_login_wrong_password         PASSED
tests/test_auth.py::test_refresh_token                PASSED
tests/test_auth.py::test_protected_endpoint           PASSED
tests/test_auth.py::test_get_me                       PASSED
tests/test_files.py::test_upload_url                  PASSED
tests/test_files.py::test_confirm_upload              PASSED
tests/test_files.py::test_list_files                  PASSED
tests/test_files.py::test_delete_file                 PASSED
tests/test_files.py::test_quota_exceeded              PASSED
tests/test_shares.py::test_create_share               PASSED
tests/test_shares.py::test_list_shares                PASSED
tests/test_shares.py::test_revoke_share               PASSED
tests/test_shares.py::test_public_share_access        PASSED
tests/test_shares.py::test_revoked_share_blocked      PASSED

17 passed in 3.69s
```

## AWS Setup

### S3 Bucket

1. Create a bucket (e.g., `clouddrop-files-yourname`)
2. **Block all public access** (all 4 settings enabled)
3. Add CORS configuration:
   ```json
   [
     {
       "AllowedHeaders": ["Content-Type", "Content-Length"],
       "AllowedMethods": ["PUT"],
       "AllowedOrigins": ["http://localhost:5173", "https://yourdomain.com"],
       "ExposeHeaders": ["ETag"],
       "MaxAgeSeconds": 3000
     }
   ]
   ```

### CloudFront Distribution

1. Create distribution with your S3 bucket as origin
2. Enable **Origin Access Control (OAC)**
3. Set viewer access to require signed URLs
4. Create a key group with your RSA public key
5. Apply the OAC bucket policy to your S3 bucket

### IAM Policy

Create an IAM user with this policy for the application:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::your-bucket-name"
    }
  ]
}
```

## Project Structure

```
cloud-drop/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # Auth dependency (JWT validation)
│   │   │   └── v1/
│   │   │       ├── auth.py          # Register, login, refresh, logout
│   │   │       ├── files.py         # Upload URL, confirm, list, delete
│   │   │       ├── shares.py        # Create, revoke, list, public access
│   │   │       └── users.py         # Profile endpoints
│   │   ├── core/
│   │   │   ├── aws.py               # S3 + CloudFront helpers
│   │   │   ├── config.py            # Pydantic settings (env loader)
│   │   │   └── security.py          # JWT + bcrypt
│   │   ├── db/
│   │   │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │   │   └── session.py           # Async engine + session factory
│   │   ├── models/                  # User, File, Share ORM models
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── services/                # Business logic layer
│   │   └── main.py                  # FastAPI app + CORS + router
│   ├── alembic/                     # Database migrations
│   ├── tests/                       # 17 async tests
│   ├── Dockerfile                   # Multi-stage (builder + runtime)
│   └── pyproject.toml               # uv-managed Python deps
│
├── frontend/
│   ├── src/
│   │   ├── api/                     # Axios client + TanStack Query hooks
│   │   ├── components/
│   │   │   ├── ui/                  # 12 shadcn/ui-style components
│   │   │   ├── DropZone.tsx         # Drag-and-drop upload
│   │   │   ├── FileCard.tsx         # File display + actions
│   │   │   └── ShareModal.tsx       # Share link creation dialog
│   │   ├── pages/                   # Login, Register, Dashboard, ShareView
│   │   ├── stores/                  # Zustand auth store
│   │   └── lib/utils.ts             # cn(), formatBytes(), formatDate()
│   ├── Dockerfile                   # Multi-stage (build + Nginx)
│   ├── nginx.conf                   # SPA fallback + /api proxy
│   └── vite.config.ts               # Tailwind v4 plugin + API proxy
│
├── docker-compose.yml               # Dev (hot reload)
├── docker-compose.prod.yml          # Production overrides
├── .env.example                     # All 14 environment variables
└── CLAUDE.md                        # AI assistant context file
```

## License

MIT
