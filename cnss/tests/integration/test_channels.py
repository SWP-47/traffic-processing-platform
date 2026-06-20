import asyncio
from unittest.mock import patch
from datetime import datetime, timezone
from app.store.memory import InMemoryStateStore


class TestChannelsEndpoint:
    def _setup_store(self, channels):
        test_store = InMemoryStateStore()
        loop = asyncio.new_event_loop()
        for ch_id in channels:
            loop.run_until_complete(
                test_store.update_channel_activity(ch_id, 1, datetime.now(timezone.utc))
            )
        loop.close()
        return test_store

    def test_admin_sees_all_channels(self, client, admin_headers):
        test_store = self._setup_store(["ch-admin-1", "ch-admin-2"])
        with patch("app.main.state_store", test_store):
            response = client.get("/api/v1/channels", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        ids = {ch["channel_id"] for ch in data["channels"]}
        assert ids == {"ch-admin-1", "ch-admin-2"}

    def test_viewer_sees_only_scoped_channels(self, client, viewer_headers):
        # Viewer token (from conftest) has scope ["bridge-berlin-01"]
        test_store = self._setup_store(["bridge-berlin-01", "bridge-prague-01"])
        with patch("app.main.state_store", test_store):
            response = client.get("/api/v1/channels", headers=viewer_headers)

        assert response.status_code == 200
        data = response.json()
        ids = {ch["channel_id"] for ch in data["channels"]}
        assert ids == {"bridge-berlin-01"}
        assert "bridge-prague-01" not in ids

    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/channels")
        assert response.status_code == 401
