# CloudDrop — SaaS File Management & Sharing Platform
### Full-Stack Design Document — Claude Code Edition
**Stack:** React 19 · FastAPI 0.135 · PostgreSQL 16 · AWS S3 · AWS CloudFront · Docker

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Architecture](#3-architecture)
4. [Project Structure](#4-project-structure)
5. [Database Schema](#5-database-schema)
6. [API Reference](#6-api-reference)
7. [Core Feature: File Upload & CDN Delivery](#7-core-feature-file-upload--cdn-delivery)
8. [Core Feature: Secure Sharing with Expiry Links](#8-core-feature-secure-sharing-with-expiry-links)
9. [Authentication & Authorization](#9-authentication--authorization)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Docker & Containerization](#11-docker--containerization)
12. [Environment Variables](#12-environment-variables)
13. [AWS Infrastructure Setup](#13-aws-infrastructure-setup)
14. [Optional Features](#14-optional-features)
15. [Testing Strategy](#15-testing-strategy)
16. [README & GitHub Presentation Tips](#16-readme--github-presentation-tips)

---

## 1. Project Overview

CloudDrop is a production-grade, multi-tenant SaaS file management and sharing platform. Every technology choice is deliberate and resume-worthy:

- **React 19 + Vite 6** for a modern, fast frontend with TypeScript
- **FastAPI 0.135** (Python 3.13) for an async, self-documenting REST API
- **PostgreSQL 16** for relational persistence with multi-tenant data isolation
- **AWS S3** for scalable object storage with direct browser upload via presigned URLs
- **AWS CloudFront** for global CDN delivery with signed URL access control
- **Docker + Docker Compose** for reproducible dev and production environments

### Core Value Proposition
Users upload files via drag-and-drop → stored in S3 (browser uploads directly, bypassing the server) → shared via time-limited CloudFront signed URLs. The S3 bucket is never publicly accessible; all delivery goes through CloudFront with Origin Access Control (OAC).

---

## 2. Technology Stack

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| Frontend | React + TypeScript + Vite | React 19, Vite 6 | React 19 Actions, fast HMR, native ESM |
| UI | shadcn/ui + Tailwind CSS | Tailwind v4 | Accessible headless components |
| State/Data | TanStack Query (React Query) | v5 | Server-state caching, optimistic updates |
| State (auth) | Zustand | v5 | Lightweight global auth store |
| Routing | React Router DOM | v7 | Lazy loading, nested routes |
| HTTP Client | Axios | v1 | Interceptors for JWT refresh |
| Backend | FastAPI + Pydantic v2 | 0.135.1 | Async, auto OpenAPI docs, Pydantic v2 |
| Python | Python | 3.13 | Best performance, longest support |
| Dep. Manager | uv (Astral) | latest | FastAPI-recommended, 10-100x faster than pip |
| ORM | SQLAlchemy 2 (async) + asyncpg | 2.x | Async engine, native PostgreSQL driver |
| Migrations | Alembic | 1.x | Auto-generated from SQLAlchemy models |
| Database | PostgreSQL | 16-alpine | ACID, JSONB support, row-level security ready |
| Object Storage | AWS S3 + boto3 | boto3 1.x | Presigned PUT (upload), OAC origin restriction |
| CDN | AWS CloudFront | RSA signed URLs | Signed URLs with configurable TTL |
| Auth | JWT (python-jose + passlib) | — | Stateless RS256-signed tokens |
| Containerization | Docker + Docker Compose v2 | — | Multi-stage builds, prod/dev parity |
| Reverse Proxy | Nginx | alpine | SPA fallback + /api proxy to backend |
| Testing (BE) | pytest + httpx + pytest-asyncio | — | Async-native test client |
| Testing (FE) | Vitest + Testing Library | — | Fast Vite-based runner |

---

## 3. Architecture

### 3.1 High-Level Diagram

```
┌──────────────────────────────────────────────────────────┐
│                        Browser                           │
│               React 19 SPA (Nginx :3000)                 │
└──────────────┬───────────────────────────────────────────┘
               │ /api/* (proxied by Nginx)
               ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Backend (:8000)                      │
│   Auth · File Metadata · Presigned URL Gen · Shares      │
└────────┬─────────────────────────┬────────────────────────┘
         │ SQL (asyncpg)           │ boto3
         ▼                         ▼
┌────────────────┐       ┌─────────────────────────────────┐
│  PostgreSQL 16 │       │           AWS S3 Bucket          │
│  (metadata,    │       │  (private, OAC, no public URLs)  │
│   users,       │       └──────────────┬──────────────────┘
│   shares)      │                      │ Origin (OAC only)
└────────────────┘                      ▼
                            ┌───────────────────────┐
                            │    AWS CloudFront      │
                            │  (Signed URLs, HTTPS,  │
                            │   global edge cache)   │
                            └───────────────────────┘
```

### 3.2 Upload Flow (Direct Browser → S3)

The browser never sends bytes through the FastAPI server — this eliminates bandwidth costs and scales to large files without change.

```
1. Browser  →  POST /api/v1/files/upload-url  →  FastAPI
               { filename, size, mime_type }

2. FastAPI  →  boto3.generate_presigned_url("put_object", expires=900)
               Creates file record in PostgreSQL with status="pending"
               Returns { upload_url, file_id, s3_key }

3. Browser  →  PUT {upload_url}  →  S3 directly (with Content-Type header)
               (S3 CORS allows app domain for PUT)

4. Browser  →  PATCH /api/v1/files/{file_id}/confirm  →  FastAPI
               FastAPI updates status="active" in PostgreSQL
```

### 3.3 Download / Share Flow (CloudFront Signed URL)

```
1. Authenticated user requests share link or file preview

2. FastAPI generates CloudFront signed URL:
   - Canned policy: simple expiry (1h / 24h / 7d)
   - Custom policy: IP restriction + expiry (optional feature)

3. Share record written to PostgreSQL:
   { id, file_id, owner_id, expires_at, is_revoked, access_count }

4. URL returned to browser. Recipient opens CloudFront URL.

5. CloudFront validates RSA signature → cache hit or fetches from S3 via OAC
   S3 bucket rejects all non-CloudFront requests (OAC policy)
```

### 3.4 Multi-Tenancy Model

Every table with user-owned data has an `owner_id UUID` FK referencing `users.id`. All SQLAlchemy repository queries receive the current user's ID from the JWT dependency injection and apply `WHERE owner_id = :current_user_id`. This is enforced at the service layer — never left to the route handler.

---

## 4. Project Structure

```
clouddrop/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                  # get_current_user, get_db
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py              # /register, /login, /refresh
│   │   │       ├── files.py             # upload-url, confirm, list, delete
│   │   │       ├── shares.py            # create, revoke, list
│   │   │       └── users.py             # /me, update profile
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic BaseSettings (.env loader)
│   │   │   ├── security.py              # JWT encode/decode, bcrypt hashing
│   │   │   └── aws.py                   # boto3 S3 + CloudFront helpers
│   │   ├── db/
│   │   │   ├── base.py                  # SQLAlchemy DeclarativeBase
│   │   │   └── session.py               # async_sessionmaker, get_db()
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── file.py
│   │   │   └── share.py
│   │   ├── schemas/
│   │   │   ├── auth.py                  # LoginRequest, TokenResponse
│   │   │   ├── file.py                  # FileCreate, FileOut, UploadUrlResponse
│   │   │   └── share.py                 # ShareCreate, ShareOut
│   │   ├── services/
│   │   │   ├── file_service.py          # business logic, calls aws.py
│   │   │   └── share_service.py
│   │   └── main.py                      # FastAPI app factory, lifespan, CORS
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_files.py
│   │   └── test_shares.py
│   ├── Dockerfile
│   ├── pyproject.toml                   # managed by uv
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts                # axios instance + JWT interceptor
│   │   │   ├── files.ts                 # TanStack Query hooks for files
│   │   │   ├── shares.ts
│   │   │   └── auth.ts
│   │   ├── components/
│   │   │   ├── ui/                      # shadcn/ui re-exports
│   │   │   ├── DropZone.tsx             # drag-and-drop upload area
│   │   │   ├── FileCard.tsx             # file list item
│   │   │   ├── ShareModal.tsx           # TTL picker + copy link
│   │   │   └── ProtectedRoute.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx            # main file manager view
│   │   │   └── ShareView.tsx            # public share preview page
│   │   ├── stores/
│   │   │   └── authStore.ts             # Zustand: token, user, setToken
│   │   ├── lib/
│   │   │   └── utils.ts                 # cn(), formatBytes(), formatDate()
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── nginx.conf                        # SPA fallback + proxy_pass /api
│   ├── Dockerfile
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── docker-compose.yml                    # dev (with hot reload)
├── docker-compose.prod.yml               # prod overrides
├── .env.example
└── README.md
```

---

## 5. Database Schema

### 5.1 `users`

```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         VARCHAR(255) UNIQUE NOT NULL,
  full_name     VARCHAR(255),
  hashed_password TEXT NOT NULL,
  is_active     BOOLEAN DEFAULT TRUE,
  storage_used  BIGINT DEFAULT 0,      -- bytes, updated on upload/delete
  storage_quota BIGINT DEFAULT 5368709120, -- 5 GB default
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);
```

### 5.2 `files`

```sql
CREATE TABLE files (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename      VARCHAR(512) NOT NULL,       -- original filename shown in UI
  s3_key        TEXT NOT NULL UNIQUE,        -- e.g. users/{owner_id}/{uuid}/{filename}
  mime_type     VARCHAR(255),
  size_bytes    BIGINT NOT NULL DEFAULT 0,
  status        VARCHAR(20) DEFAULT 'pending'
                  CHECK (status IN ('pending', 'active', 'deleted')),
  folder_id     UUID REFERENCES folders(id), -- nullable (optional feature)
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_files_owner_id ON files(owner_id);
CREATE INDEX idx_files_status ON files(status);
```

### 5.3 `shares`

```sql
CREATE TABLE shares (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_id       UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at    TIMESTAMPTZ NOT NULL,
  is_revoked    BOOLEAN DEFAULT FALSE,
  access_count  INT DEFAULT 0,
  last_accessed TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_shares_file_id ON shares(file_id);
CREATE INDEX idx_shares_owner_id ON shares(owner_id);
CREATE INDEX idx_shares_expires_at ON shares(expires_at);
```

### 5.4 `folders` _(Optional Feature)_

```sql
CREATE TABLE folders (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name       VARCHAR(255) NOT NULL,
  parent_id  UUID REFERENCES folders(id),   -- for nested folders
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.5 `audit_log` _(Optional Feature)_

```sql
CREATE TABLE audit_log (
  id         BIGSERIAL PRIMARY KEY,
  user_id    UUID REFERENCES users(id),
  action     VARCHAR(100) NOT NULL,  -- 'upload', 'download', 'share_created', etc.
  file_id    UUID REFERENCES files(id),
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 6. API Reference

Base path: `/api/v1`

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Create account, returns tokens |
| POST | `/auth/login` | None | Returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh token | Rotate access token |
| POST | `/auth/logout` | Bearer | Invalidate refresh token |

### Files

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/files` | Bearer | List user's files (paginated) |
| POST | `/files/upload-url` | Bearer | Get S3 presigned PUT URL |
| PATCH | `/files/{id}/confirm` | Bearer | Mark upload complete |
| GET | `/files/{id}` | Bearer | Get file metadata |
| DELETE | `/files/{id}` | Bearer | Soft delete (status=deleted) |

### Shares

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/shares` | Bearer | Create share link for a file |
| GET | `/shares` | Bearer | List all shares owned by user |
| DELETE | `/shares/{id}` | Bearer | Revoke a share link |
| GET | `/shares/{id}/url` | Bearer | Regenerate CloudFront signed URL |
| GET | `/public/shares/{id}` | None | Public preview endpoint |

### Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Bearer | Get current user profile |
| PATCH | `/users/me` | Bearer | Update profile / full_name |

---

## 7. Core Feature: File Upload & CDN Delivery

### 7.1 Backend — `app/core/aws.py`

```python
import boto3
from botocore.config import Config
from app.core.config import settings

def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )

def generate_presigned_upload_url(s3_key: str, mime_type: str, expires: int = 900) -> str:
    """Returns a presigned PUT URL valid for `expires` seconds (default 15 min)."""
    client = get_s3_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": s3_key,
            "ContentType": mime_type,
        },
        ExpiresIn=expires,
        HttpMethod="PUT",
    )

def generate_cloudfront_signed_url(s3_key: str, expires_at: datetime) -> str:
    """
    Returns a CloudFront signed URL using a canned policy.
    Requires CLOUDFRONT_PRIVATE_KEY and CLOUDFRONT_KEY_PAIR_ID in settings.
    """
    from botocore.signers import CloudFrontSigner
    import rsa

    def rsa_signer(message: bytes) -> bytes:
        private_key = rsa.PrivateKey.load_pkcs1(
            settings.CLOUDFRONT_PRIVATE_KEY.encode()
        )
        return rsa.sign(message, private_key, "SHA-1")

    cf_url = f"https://{settings.CLOUDFRONT_DOMAIN}/{s3_key}"
    signer = CloudFrontSigner(settings.CLOUDFRONT_KEY_PAIR_ID, rsa_signer)
    return signer.generate_presigned_url(cf_url, date_less_than=expires_at)

def delete_s3_object(s3_key: str) -> None:
    client = get_s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
```

### 7.2 Backend — `app/api/v1/files.py`

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.aws import generate_presigned_upload_url
from app.models.user import User
from app.schemas.file import UploadUrlRequest, UploadUrlResponse, FileOut
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/upload-url", response_model=UploadUrlResponse)
async def request_upload_url(
    body: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate quota
    if current_user.storage_used + body.size_bytes > current_user.storage_quota:
        raise HTTPException(status_code=400, detail="Storage quota exceeded")

    s3_key = f"users/{current_user.id}/{uuid.uuid4()}/{body.filename}"
    upload_url = generate_presigned_upload_url(s3_key, body.mime_type)

    file = await FileService(db).create_pending(
        owner_id=current_user.id,
        filename=body.filename,
        s3_key=s3_key,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    return UploadUrlResponse(upload_url=upload_url, file_id=file.id, s3_key=s3_key)

@router.patch("/{file_id}/confirm", response_model=FileOut)
async def confirm_upload(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileService(db).confirm(file_id, owner_id=current_user.id)
```

### 7.3 Frontend — `DropZone.tsx` Upload Flow

```typescript
// src/components/DropZone.tsx
import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { apiClient } from "@/api/client";

export function DropZone() {
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      // 1. Get presigned URL from our API
      const { data } = await apiClient.post("/files/upload-url", {
        filename: file.name,
        size_bytes: file.size,
        mime_type: file.type,
      });

      // 2. Upload directly to S3 — note: no auth headers here
      await axios.put(data.upload_url, file, {
        headers: { "Content-Type": file.type },
        onUploadProgress: (e) => {
          // update progress state here
        },
      });

      // 3. Confirm upload with our API
      await apiClient.patch(`/files/${data.file_id}/confirm`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
    },
  });

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach((file) => uploadMutation.mutate(file));
    },
    [uploadMutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
        ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400"}`}
    >
      <input {...getInputProps()} />
      <p className="text-gray-600">
        {isDragActive ? "Drop files here..." : "Drag & drop files, or click to select"}
      </p>
    </div>
  );
}
```

---

## 8. Core Feature: Secure Sharing with Expiry Links

### 8.1 Backend — `app/api/v1/shares.py`

```python
from datetime import datetime, timedelta, UTC
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.aws import generate_cloudfront_signed_url
from app.models.user import User
from app.schemas.share import ShareCreate, ShareOut
from app.services.share_service import ShareService

router = APIRouter(prefix="/shares", tags=["shares"])

TTL_OPTIONS = {"1h": 3600, "24h": 86400, "7d": 604800}

@router.post("", response_model=ShareOut)
async def create_share(
    body: ShareCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ttl_seconds = TTL_OPTIONS.get(body.ttl, 86400)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    share = await ShareService(db).create(
        file_id=body.file_id,
        owner_id=current_user.id,
        expires_at=expires_at,
    )

    signed_url = generate_cloudfront_signed_url(share.file.s3_key, expires_at)
    return ShareOut.model_validate({**share.__dict__, "signed_url": signed_url})

@router.delete("/{share_id}", status_code=204)
async def revoke_share(
    share_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ShareService(db).revoke(share_id, owner_id=current_user.id)
```

### 8.2 Frontend — `ShareModal.tsx`

```typescript
// src/components/ShareModal.tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";

const TTL_OPTIONS = [
  { value: "1h", label: "1 Hour" },
  { value: "24h", label: "24 Hours" },
  { value: "7d", label: "7 Days" },
];

export function ShareModal({ fileId }: { fileId: string }) {
  const [ttl, setTtl] = useState("24h");
  const [copiedUrl, setCopiedUrl] = useState("");

  const shareMutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/shares", { file_id: fileId, ttl });
      return data.signed_url as string;
    },
    onSuccess: (url) => {
      navigator.clipboard.writeText(url);
      setCopiedUrl(url);
    },
  });

  return (
    <div className="space-y-4">
      <Select value={ttl} onValueChange={setTtl} options={TTL_OPTIONS} />
      <Button onClick={() => shareMutation.mutate()} disabled={shareMutation.isPending}>
        {shareMutation.isPending ? "Generating..." : "Create Share Link"}
      </Button>
      {copiedUrl && (
        <p className="text-sm text-green-600">Link copied to clipboard!</p>
      )}
    </div>
  );
}
```

---

## 9. Authentication & Authorization

### 9.1 JWT Strategy

```python
# app/core/security.py
from datetime import datetime, timedelta, UTC
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )

def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)
```

### 9.2 Auth Dependency (`app/api/deps.py`)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user
```

### 9.3 Frontend — Axios Interceptor & Zustand Auth Store

```typescript
// src/stores/authStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: { id: string; email: string; full_name: string } | null;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: AuthState["user"]) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setUser: (user) => set({ user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: "auth-storage" }
  )
);
```

```typescript
// src/api/client.ts
import axios from "axios";
import { useAuthStore } from "@/stores/authStore";

export const apiClient = axios.create({ baseURL: "/api/v1" });

// Attach JWT to every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = useAuthStore.getState().refreshToken;
      const { data } = await axios.post("/api/v1/auth/refresh", { refresh_token: refreshToken });
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
      original.headers.Authorization = `Bearer ${data.access_token}`;
      return apiClient(original);
    }
    return Promise.reject(err);
  }
);
```

---

## 10. Frontend Architecture

### 10.1 Route Structure

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProtectedRoute } from "@/components/ProtectedRoute";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/share/:shareId" element={<ShareView />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/folder/:folderId" element={<Dashboard />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

### 10.2 TanStack Query File Hooks

```typescript
// src/api/files.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export const fileKeys = {
  all: ["files"] as const,
  list: (folderId?: string) => [...fileKeys.all, "list", folderId] as const,
};

export function useFiles(folderId?: string) {
  return useQuery({
    queryKey: fileKeys.list(folderId),
    queryFn: async () => {
      const { data } = await apiClient.get("/files", { params: { folder_id: folderId } });
      return data;
    },
  });
}

export function useDeleteFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) => apiClient.delete(`/files/${fileId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: fileKeys.all }),
  });
}
```

---

## 11. Docker & Containerization

### 11.1 Backend `Dockerfile` (multi-stage)

```dockerfile
# backend/Dockerfile

# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.13-slim AS builder
WORKDIR /app

# Install uv (FastAPI-recommended package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests first (cache layer)
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual env
RUN uv sync --frozen --no-install-project

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Activate venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Use exec form for graceful shutdown
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
```

### 11.2 Frontend `Dockerfile` (multi-stage)

```dockerfile
# frontend/Dockerfile

# ── Stage 1: build React app ──────────────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: serve with Nginx ─────────────────────────────────────────────────
FROM nginx:alpine AS runtime

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx config (SPA fallback + /api proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 11.3 `frontend/nginx.conf`

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy /api requests to FastAPI backend (service name in Docker network)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 256;
}
```

### 11.4 `docker-compose.yml` (Development)

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: clouddrop_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      target: runtime           # use runtime stage (no dev deps)
    container_name: clouddrop_backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    volumes:
      - ./backend/app:/app/app  # hot reload in dev
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    command: ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]

  frontend:
    build:
      context: ./frontend
      target: builder           # dev: run Vite dev server
    container_name: clouddrop_frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000/api/v1
    volumes:
      - ./frontend/src:/app/src  # hot reload
    ports:
      - "5173:5173"
    depends_on:
      - backend
    command: ["npm", "run", "dev", "--", "--host"]

volumes:
  postgres_data:
```

### 11.5 `docker-compose.prod.yml` (Production Overrides)

```yaml
# Usage: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

services:
  backend:
    build:
      target: runtime
    volumes: []   # no source mounts in prod
    command: ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
    restart: unless-stopped

  frontend:
    build:
      target: runtime   # full Nginx build
    ports:
      - "80:80"
    volumes: []
    restart: unless-stopped

  db:
    restart: unless-stopped
```

---

## 12. Environment Variables

### `.env.example`

```dotenv
# ── PostgreSQL ──────────────────────────────────────────────────────────────
POSTGRES_USER=clouddrop
POSTGRES_PASSWORD=changeme
POSTGRES_DB=clouddrop_db

# ── FastAPI ─────────────────────────────────────────────────────────────────
SECRET_KEY=change-this-to-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development

# ── AWS ─────────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

S3_BUCKET_NAME=clouddrop-files-yourname
CLOUDFRONT_DOMAIN=d1234abcd.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID=APKA...
# Paste PEM private key as single line with \n literals
CLOUDFRONT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

---

## 13. AWS Infrastructure Setup

### 13.1 S3 Bucket Configuration

1. Create bucket `clouddrop-files-{yourname}` in your chosen region
2. **Block all public access** — enable all 4 block public access settings
3. **CORS configuration** (required for direct browser PUT):

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

4. **Bucket policy** — restrict to CloudFront OAC only (applied after CloudFront setup)

### 13.2 CloudFront Distribution Setup

1. **Create distribution** with S3 bucket as origin
2. **Enable Origin Access Control (OAC)** — creates a managed policy that allows only CloudFront to access S3
3. **Restrict viewer access** → set to "Yes" (requires signed URLs)
4. **Trusted key groups** → create a key group with your RSA public key
5. **Cache policy** → use CachingOptimized for assets, no-cache for dynamic
6. Copy the S3 bucket policy statement from the OAC setup and apply it to the bucket

### 13.3 IAM Policy for Application

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::clouddrop-files-yourname/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::clouddrop-files-yourname"
    }
  ]
}
```

> Create an IAM user with this policy and use its credentials in `.env`. For production, use an IAM Role on ECS/EC2 instead.

---

## 14. Optional Features

These features are pre-designed and ready to implement after the two core features are polished.

### 14.1 Storage Usage Dashboard

A visual breakdown showing how much of their 5 GB quota a user has consumed, with a per-file-type chart.

**Implementation:**
- Backend: `GET /users/me/storage-stats` — SQLAlchemy aggregate query:
  ```sql
  SELECT mime_type, SUM(size_bytes) as total
  FROM files WHERE owner_id = :id AND status = 'active'
  GROUP BY mime_type
  ```
- Frontend: Recharts `PieChart` + progress bar component in the Dashboard sidebar

### 14.2 Folder Organization

Hierarchical folder tree (max 2 levels recommended for simplicity).

**Implementation:**
- `folders` table already in schema (Section 5.4)
- Backend: `POST /folders`, `GET /folders`, `DELETE /folders/{id}`
- Frontend: Sidebar folder tree with drag-and-drop reorder (using `@dnd-kit/core`)
- `files` table has nullable `folder_id` FK — move files between folders via `PATCH /files/{id}`

### 14.3 File Preview (Images & PDFs)

Show inline previews without downloading.

**Implementation:**
- Backend: `GET /files/{id}/preview-url` — returns a short-lived CloudFront signed URL (15 min TTL)
- Frontend: `<img>` for images, `<iframe>` for PDFs, using the signed preview URL
- Show thumbnail grid view vs. list view toggle in Dashboard

### 14.4 Share Analytics

Track access_count and last_accessed per share link.

**Implementation:**
- `shares.access_count` and `shares.last_accessed` already in schema
- Add a public middleware endpoint `GET /public/shares/{id}` that increments the counter before returning the signed URL
- Frontend: "Analytics" tab in share management modal showing access count per link

### 14.5 Email Notifications

Notify users when someone accesses their shared file.

**Implementation:**
- FastAPI `BackgroundTasks`: after incrementing `access_count`, enqueue a background task
- Use `fastapi-mail` or `boto3` SES to send the notification email
- Add `notify_on_access: bool` column to `shares` table

### 14.6 Expiry Warning Cron Job

Notify users when their share links are about to expire.

**Implementation:**
- FastAPI APScheduler (or a simple Docker service with `schedule` library)
- Runs daily: `SELECT * FROM shares WHERE expires_at < now() + interval '24 hours' AND is_revoked = false`
- Sends summary email via SES

### 14.7 Terraform Infrastructure as Code

Define the entire AWS infrastructure as code.

**Files to create:**
```
infra/
├── main.tf
├── s3.tf         # bucket, CORS, OAC policy
├── cloudfront.tf # distribution, key group, cache policy
├── iam.tf        # app user, policies
└── variables.tf
```

> This is the single highest-signal optional feature for a senior engineering portfolio.

---

## 15. Testing Strategy

### 15.1 Backend Tests (`pytest`)

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.db.session import get_db
from app.db.base import Base

TEST_DB_URL = "postgresql+asyncpg://test:test@localhost:5432/clouddrop_test"

@pytest_asyncio.fixture
async def async_client():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

```python
# tests/test_files.py
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_upload_url_returns_presigned_url(async_client, auth_headers):
    with patch("app.core.aws.generate_presigned_upload_url", return_value="https://s3.presigned"):
        response = await async_client.post(
            "/api/v1/files/upload-url",
            json={"filename": "test.pdf", "size_bytes": 1024, "mime_type": "application/pdf"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["upload_url"] == "https://s3.presigned"
```

### 15.2 Frontend Tests (`Vitest`)

```typescript
// src/components/__tests__/DropZone.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DropZone } from "../DropZone";

describe("DropZone", () => {
  it("renders upload prompt", () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <DropZone />
      </QueryClientProvider>
    );
    expect(screen.getByText(/drag & drop files/i)).toBeInTheDocument();
  });
});
```

---

## 16. README & GitHub Presentation Tips

Your `README.md` is what recruiters see first. Structure it as follows:

```
# CloudDrop 🗂️
> A production-grade SaaS file management platform with direct S3 uploads and CloudFront CDN delivery.

[Live Demo badge] [License badge] [Tech stack badges]

## ✨ Features
...

## 🏗️ Architecture
[Paste the ASCII diagram from Section 3.1]

## 🚀 Quick Start (Docker)
docker compose up --build

## 🔑 Environment Setup
cp .env.example .env
# Fill in AWS credentials and PostgreSQL settings

## 📡 API Docs
http://localhost:8000/docs  (Swagger UI auto-generated by FastAPI)

## 🏛️ Tech Stack
[Table from Section 2]

## 📸 Screenshots
[3-4 screenshots: Login, Dashboard with files, Share modal, Share preview page]
```

**Key things that get recruiter clicks:**
- A live demo URL (deploy on Railway, Fly.io, or AWS ECS Free Tier)
- The architecture diagram — shows systems thinking
- Screenshots — shows it actually works
- The `docker compose up --build` quick-start — shows production mindset

---

*Document version: 1.0 — March 2026 | Stack verified against FastAPI 0.135.1, React 19, Vite 6, PostgreSQL 16, Node.js 22, Python 3.13*
