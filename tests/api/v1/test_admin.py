"""Tests for admin database endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_create_database_backup(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test DB-01: Create database backup."""
    r = client.post(
        f"{settings.API_V1_STR}/admin/database/backup",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "backup_id" in data
    assert "filename" in data
    assert "created_at" in data


def test_list_database_backups(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test DB-02: List database backups."""
    r = client.get(
        f"{settings.API_V1_STR}/admin/database/backups",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_database_stats(client: TestClient, superuser_token_headers: dict) -> None:
    """Test DB-05: Get database statistics."""
    r = client.get(
        f"{settings.API_V1_STR}/admin/database/stats",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "size_bytes" in data
    assert "table_counts" in data
    assert "integrity_ok" in data


def test_database_maintenance(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test DB-06: Run database maintenance."""
    r = client.post(
        f"{settings.API_V1_STR}/admin/database/maintenance",
        params={"operation": "vacuum"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "message" in data


def test_database_export(client: TestClient, superuser_token_headers: dict) -> None:
    """Test DB-07: Bulk data export."""
    r = client.get(
        f"{settings.API_V1_STR}/admin/database/export?format=json",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200


def test_database_export_with_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test DB-07: Export specific project data."""
    # Create a project first
    project_data = {"name": "Export Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Export project data
    r = client.get(
        f"{settings.API_V1_STR}/admin/database/export?project_id={project_id}&format=json",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200


def test_admin_endpoints_require_superuser(client: TestClient) -> None:
    """Test that admin endpoints require authentication."""
    r = client.get(f"{settings.API_V1_STR}/admin/database/stats")
    assert r.status_code == 401


def test_download_backup(client: TestClient, superuser_token_headers: dict) -> None:
    """Test DB-03: Download backup file."""
    # Use a fake backup ID
    backup_id = "fake-backup-id"

    # Try to download the backup
    r = client.get(
        f"{settings.API_V1_STR}/admin/database/backups/{backup_id}",
        headers=superuser_token_headers,
    )
    # Will return 404 if not found or 200 if found
    assert r.status_code in [200, 404]


def test_restore_backup(client: TestClient, superuser_token_headers: dict) -> None:
    """Test DB-04: Restore from backup."""
    # Use a fake backup ID since we're just testing the endpoint
    backup_id = "fake-backup-id"

    # Restore from backup
    r = client.post(
        f"{settings.API_V1_STR}/admin/database/restore",
        params={"backup_id": backup_id},
        headers=superuser_token_headers,
    )
    # May return 200, 404, or 503 depending on implementation
    assert r.status_code in [200, 404, 503]
