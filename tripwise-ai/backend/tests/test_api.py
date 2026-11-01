from fastapi.testclient import TestClient

from app.main import app


def test_traveller_cannot_open_admin_and_can_update_profile():
    with TestClient(app) as client:
        registered = client.post(
            "/api/auth/register",
            json={"name": "Nia Traveller", "email": "nia.traveller@example.com", "password": "Tripwise#Travel1"},
        )
        assert registered.status_code == 201
        token = registered.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        blocked = client.get("/api/admin/dashboard", headers=headers)
        assert blocked.status_code == 403
        renamed = client.put("/api/auth/me", headers=headers, json={"name": "Nia K"})
        assert renamed.status_code == 200
        assert renamed.json()["data"]["name"] == "Nia K"
        wildlife = client.get("/api/destinations?audience=wildlife")
        assert wildlife.status_code == 200
        names = [row["name"] for row in wildlife.json()["data"]]
        assert "Dandeli" in names
