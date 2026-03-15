import pytest
from unittest.mock import patch
from httpx import AsyncClient


async def _create_active_file(
    async_client: AsyncClient, auth_headers: dict
) -> str:
    with patch(
        "app.api.v1.files.generate_presigned_upload_url",
        return_value="https://s3.presigned.example.com",
    ):
        upload_resp = await async_client.post(
            "/api/v1/files/upload-url",
            json={
                "filename": "shareable.pdf",
                "size_bytes": 1024,
                "mime_type": "application/pdf",
            },
            headers=auth_headers,
        )
    file_id = upload_resp.json()["file_id"]
    await async_client.patch(f"/api/v1/files/{file_id}/confirm", headers=auth_headers)
    return file_id


@pytest.mark.asyncio
async def test_create_share(async_client: AsyncClient, auth_headers: dict):
    file_id = await _create_active_file(async_client, auth_headers)

    with patch(
        "app.api.v1.shares.generate_cloudfront_signed_url",
        return_value="https://cdn.example.com/signed",
    ):
        response = await async_client.post(
            "/api/v1/shares",
            json={"file_id": file_id, "ttl": "24h"},
            headers=auth_headers,
        )
    assert response.status_code == 201
    data = response.json()
    assert data["file_id"] == file_id
    assert data["signed_url"] == "https://cdn.example.com/signed"


@pytest.mark.asyncio
async def test_list_shares(async_client: AsyncClient, auth_headers: dict):
    file_id = await _create_active_file(async_client, auth_headers)

    with patch(
        "app.api.v1.shares.generate_cloudfront_signed_url",
        return_value="https://cdn.example.com/signed",
    ):
        await async_client.post(
            "/api/v1/shares",
            json={"file_id": file_id, "ttl": "1h"},
            headers=auth_headers,
        )

    response = await async_client.get("/api/v1/shares", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_revoke_share(async_client: AsyncClient, auth_headers: dict):
    file_id = await _create_active_file(async_client, auth_headers)

    with patch(
        "app.api.v1.shares.generate_cloudfront_signed_url",
        return_value="https://cdn.example.com/signed",
    ):
        create_resp = await async_client.post(
            "/api/v1/shares",
            json={"file_id": file_id, "ttl": "7d"},
            headers=auth_headers,
        )
    share_id = create_resp.json()["id"]

    response = await async_client.delete(
        f"/api/v1/shares/{share_id}", headers=auth_headers
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_public_share_access(async_client: AsyncClient, auth_headers: dict):
    file_id = await _create_active_file(async_client, auth_headers)

    with patch(
        "app.api.v1.shares.generate_cloudfront_signed_url",
        return_value="https://cdn.example.com/signed",
    ):
        create_resp = await async_client.post(
            "/api/v1/shares",
            json={"file_id": file_id, "ttl": "24h"},
            headers=auth_headers,
        )
    share_id = create_resp.json()["id"]

    with patch(
        "app.api.v1.shares.generate_cloudfront_signed_url",
        return_value="https://cdn.example.com/public-signed",
    ):
        response = await async_client.get(f"/api/v1/public/shares/{share_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "shareable.pdf"
    assert data["signed_url"] == "https://cdn.example.com/public-signed"


@pytest.mark.asyncio
async def test_revoked_share_blocked(async_client: AsyncClient, auth_headers: dict):
    file_id = await _create_active_file(async_client, auth_headers)

    with patch(
        "app.api.v1.shares.generate_cloudfront_signed_url",
        return_value="https://cdn.example.com/signed",
    ):
        create_resp = await async_client.post(
            "/api/v1/shares",
            json={"file_id": file_id, "ttl": "24h"},
            headers=auth_headers,
        )
    share_id = create_resp.json()["id"]

    await async_client.delete(f"/api/v1/shares/{share_id}", headers=auth_headers)

    response = await async_client.get(f"/api/v1/public/shares/{share_id}")
    assert response.status_code == 410
