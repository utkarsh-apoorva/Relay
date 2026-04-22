import pytest
from backend.security import hash_api_key, lookup_api_key, migrate_api_keys


class TestHashApiKey:
    def test_hash_api_key_format(self):
        raw_key = "test-key-12345"
        hashed = hash_api_key(raw_key)

        assert hashed.startswith("sha256$")
        assert len(hashed) > 10

    def test_hash_api_key_deterministic(self):
        raw_key = "test-key-12345"
        hashed1 = hash_api_key(raw_key)
        hashed2 = hash_api_key(raw_key)

        assert hashed1 == hashed2

    def test_hash_api_key_different_for_different_keys(self):
        hashed1 = hash_api_key("key1")
        hashed2 = hash_api_key("key2")

        assert hashed1 != hashed2

    def test_hash_api_key_not_reversible(self):
        raw_key = "test-key-12345"
        hashed = hash_api_key(raw_key)

        assert raw_key not in hashed
        assert hashed.count("$") == 1


class TestLookupApiKey:
    def test_lookup_api_key_valid(self, db, seed_db):
        from backend.models import ApiKey

        raw_key = "test-human-key-12345"
        result = lookup_api_key(db, raw_key)

        assert result is not None
        assert result.agent_id == "human"

    def test_lookup_api_key_invalid(self, db, seed_db):
        result = lookup_api_key(db, "invalid-key")
        assert result is None

    def test_lookup_api_key_empty(self, db, seed_db):
        result = lookup_api_key(db, "")
        assert result is None


class TestMigrateApiKeys:
    def test_migrate_keys_already_hashed(self, db, seed_db):
        migrate_api_keys(db)

        from backend.models import ApiKey

        all_keys = db.query(ApiKey).all()
        for key in all_keys:
            if key.key_hash:
                assert key.key is None or key.key == ""

    def test_migrate_keys_preserves_agent_id(self, db, seed_db):
        from backend.models import ApiKey

        migrate_api_keys(db)

        human_key = db.query(ApiKey).filter(ApiKey.agent_id == "human").first()
        assert human_key is not None
        assert human_key.agent_id == "human"

        agent1_key = db.query(ApiKey).filter(ApiKey.agent_id == "agent1").first()
        assert agent1_key is not None
        assert agent1_key.agent_id == "agent1"


class TestApiKeyModelIntegration:
    def test_api_key_lookup_by_hash(self, db, seed_db):
        from backend.models import ApiKey

        human_key = db.query(ApiKey).filter(ApiKey.agent_id == "human").first()
        assert human_key is not None
        assert human_key.key_hash is not None

        found = db.query(ApiKey).filter(ApiKey.key_hash == human_key.key_hash).first()
        assert found is not None
        assert found.agent_id == "human"


class TestSecurityHelpers:
    def test_ensure_api_key_storage(self, db_engine):
        from backend.security import ensure_api_key_storage

        ensure_api_key_storage(db_engine)

        from sqlalchemy import text

        with db_engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(api_keys)"))
            columns = {row[1] for row in result}
            assert "key_hash" in columns

    def test_migrate_agent_webhooks(self, db_engine):
        from backend.security import migrate_agent_webhooks

        migrate_agent_webhooks(db_engine)

        from sqlalchemy import text

        with db_engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(agents)"))
            columns = {row[1] for row in result}
            assert "webhook_url" in columns
            assert "webhook_secret" in columns


class TestApiKeyAuthIntegration:
    def test_valid_api_key_authenticates(self, client, auth_headers):
        response = client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200

    def test_invalid_api_key_rejected(self, client):
        response = client.get("/api/projects", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401

    def test_missing_api_key_rejected(self, client):
        response = client.get("/api/projects")
        assert response.status_code == 401

    def test_agent_api_key_authenticates(self, client, agent1_headers):
        response = client.get("/api/agents", headers=agent1_headers)
        assert response.status_code == 200