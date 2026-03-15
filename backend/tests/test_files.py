import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_url(async_client: AsyncClient, auth_headers: dict):
    with patch(
        "app.api.v1.files.generate_presigned_upload_url",
        return_value="https://s3.presigned.example.com",
    ):
        response = await async_client.post(
            "/api/v1/files/upload-url",
            json={
                "filename": "test.pdf",
                "size_bytes": 1024,
                "mime_type": "application/pdf",
            },
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["upload_url"] == "https://s3.presigned.example.com"
    assert "file_id" in data
    assert "s3_key" in data


@pytest.mark.asyncio
async def test_confirm_upload(async_client: AsyncClient, auth_headers: dict):
    with patch(
        "app.api.v1.files.generate_presigned_upload_url",
        return_value="https://s3.presigned.example.com",
    ):
        upload_resp = await async_client.post(
            "/api/v1/files/upload-url",
            json={
                "filename": "test.pdf",
                "size_bytes": 2048,
                "mime_type": "application/pdf",
            },
            headers=auth_headers,
        )
    file_id = upload_resp.json()["file_id"]

    response = await async_client.patch(
        f"/api/v1/files/{file_id}/confirm",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_list_files(async_client: AsyncClient, auth_headers: dict):
    with patch(
        "app.api.v1.files.generate_presigned_upload_url",
        return_value="https://s3.presigned.example.com",
    ):
        upload_resp = await async_client.post(
            "/api/v1/files/upload-url",
            json={
                "filename": "listed.pdf",
                "size_bytes": 512,
                "mime_type": "application/pdf",
            },
            headers=auth_headers,
        )
    file_id = upload_resp.json()["file_id"]
    await async_client.patch(f"/api/v1/files/{file_id}/confirm", headers=auth_headers)

    response = await async_client.get("/api/v1/files", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["files"]) >= 1


@pytest.mark.asyncio
async def test_delete_file(async_client: AsyncClient, auth_headers: dict):
    with patch(
        "app.api.v1.files.generate_presigned_upload_url",
        return_value="https://s3.presigned.example.com",
    ):
        upload_resp = await async_client.post(
            "/api/v1/files/upload-url",
            json={
                "filename": "delete-me.pdf",
                "size_bytes": 256,
                "mime_type": "application/pdf",
            },
            headers=auth_headers,
        )
    file_id = upload_resp.json()["file_id"]
    await async_client.patch(f"/api/v1/files/{file_id}/confirm", headers=auth_headers)

    with patch("app.services.file_service.delete_s3_object"):
        response = await async_client.delete(
            f"/api/v1/files/{file_id}", headers=auth_headers
        )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_quota_exceeded(async_client: AsyncClient, auth_headers: dict):
    with patch(
        "app.api.v1.files.generate_presigned_upload_url",
        return_value="https://s3.presigned.example.com",
    ):
        response = await async_client.post(
            "/api/v1/files/upload-url",
            json={
                "filename": "huge.bin",
                "size_bytes": 6_000_000_000,  # exceeds 5GB quota
                "mime_type": "application/octet-stream",
            },
            headers=auth_headers,
        )
    assert response.status_code == 400
    assert "quota" in response.json()["detail"].lower()
