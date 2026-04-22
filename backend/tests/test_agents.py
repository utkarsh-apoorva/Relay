import pytest
import hashlib
import hmac


class TestAgentListEndpoint:
    def test_list_agents_requires_auth(self, client):
        response = client.get("/api/agents")
        assert response.status_code == 401

    def test_list_agents_returns_data(self, client, auth_headers):
        response = client.get("/api/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_agents_contains_fields(self, client, auth_headers):
        response = client.get("/api/agents", headers=auth_headers)
        data = response.json()
        if data:
            agent = data[0]
            assert "id" in agent
            assert "name" in agent
            assert "role" in agent
            assert "model" in agent
            assert "provider" in agent
            assert "status" in agent
            assert "current_tasks" in agent
            assert "total_tasks" in agent
            assert "capabilities" in agent

    def test_list_agents_includes_meta_endpoint(self, client, auth_headers):
        response = client.get("/api/agents", headers=auth_headers)
        data = response.json()
        if data:
            assert "meta_endpoint" in data[0]
            assert "meta_prompt_version" in data[0]
            assert "meta_directive" in data[0]


class TestAgentUpdateEndpoint:
    def test_patch_agent_requires_auth(self, client):
        response = client.patch("/api/agents/agent1", json={})
        assert response.status_code == 401

    def test_patch_agent_not_found(self, client, agent1_headers, db):
        response = client.patch("/api/agents/agent1", json={"status": "Busy"}, headers=agent1_headers)
        assert response.status_code == 200

    def test_patch_agent_cannot_update_other_agent(self, client, agent1_headers):
        response = client.patch("/api/agents/agent2", json={}, headers=agent1_headers)
        assert response.status_code == 403


class TestAgentWebhookEndpoint:
    def test_delete_webhook_requires_auth(self, client):
        response = client.delete("/api/agents/agent1/webhook")
        assert response.status_code == 401

    def test_delete_webhook_not_found(self, client, agent1_headers):
        response = client.delete("/api/agents/agent1/webhook", headers=agent1_headers)
        assert response.status_code == 200

    def test_delete_webhook_success(self, client, agent1_headers, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "secret"
        db.add(agent)
        db.commit()

        response = client.delete("/api/agents/agent1/webhook", headers=agent1_headers)
        assert response.status_code == 200
        assert response.json()["ok"] is True

        db.refresh(agent)
        assert agent.webhook_url is None
        assert agent.webhook_secret is None

    def test_delete_webhook_cannot_delete_other_agent_webhook(self, client, agent1_headers):
        response = client.delete("/api/agents/agent2/webhook", headers=agent1_headers)
        assert response.status_code == 403


class TestAgentRegistrationWebhook:
    def test_patch_agent_webhook_requires_hmac(self, client, agent1_headers, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        response = client.patch(
            "/api/agents/agent1",
            json={"webhook_url": "https://example.com/webhook"},
            headers=agent1_headers,
        )
        assert response.status_code == 400
        assert "hmac" in response.json()["detail"].lower()

    def test_patch_agent_webhook_requires_url(self, client, agent1_headers, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        response = client.patch(
            "/api/agents/agent1",
            json={"hmac": "some-hmac"},
            headers=agent1_headers,
        )
        assert response.status_code == 400
        assert "webhook_url" in response.json()["detail"].lower()

    def test_patch_agent_webhook_invalid_url(self, client, agent1_headers, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        response = client.patch(
            "/api/agents/agent1",
            json={"webhook_url": "not-a-url", "hmac": "some-hmac"},
            headers=agent1_headers,
        )
        assert response.status_code == 400

    def test_patch_agent_webhook_url_too_long(self, client, agent1_headers, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        response = client.patch(
            "/api/agents/agent1",
            json={"webhook_url": "https://example.com/" + "x" * 500, "hmac": "some-hmac"},
            headers=agent1_headers,
        )
        assert response.status_code == 400

    def test_patch_agent_webhook_invalid_hmac(self, client, agent1_headers, db):
        import os
        os.environ["AGENT_AGENT1_WEBHOOK_SECRET"] = "test-secret"

        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        response = client.patch(
            "/api/agents/agent1",
            json={
                "webhook_url": "https://example.com/webhook",
                "hmac": "wrong-hmac",
                "api_key": "test-api-key",
            },
            headers=agent1_headers,
        )
        assert response.status_code == 401

    def test_patch_agent_webhook_success(self, client, agent1_headers, db):
        import os
        os.environ["AGENT_AGENT1_WEBHOOK_SECRET"] = "test-secret"

        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        api_key = "test-api-key"
        expected_hmac = hmac.new(
            "test-secret".encode(),
            api_key.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = client.patch(
            "/api/agents/agent1",
            json={
                "webhook_url": "https://example.com/webhook",
                "hmac": expected_hmac,
                "api_key": api_key,
            },
            headers=agent1_headers,
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

        db.refresh(agent)
        assert agent.webhook_url == "https://example.com/webhook"


class TestAgentCapabilities:
    def test_agent_capabilities_parsing(self, client, auth_headers, db):
        from backend.models import Agent

        agent = Agent(
            id="cap-test-agent",
            name="Capabilities Test",
            capabilities="coding, design, review",
        )
        db.add(agent)
        db.commit()

        response = client.get("/api/agents", headers=auth_headers)
        agents = response.json()
        cap_agent = next((a for a in agents if a["id"] == "cap-test-agent"), None)

        assert cap_agent is not None
        assert "coding" in cap_agent["capabilities"]
        assert "design" in cap_agent["capabilities"]
        assert "review" in cap_agent["capabilities"]


class TestAgentStatus:
    def test_agent_current_tasks_count(self, client, auth_headers, seed_task):
        response = client.get("/api/agents", headers=auth_headers)
        agents = response.json()
        agent1 = next((a for a in agents if a["id"] == "agent1"), None)

        assert agent1 is not None
        assert agent1["total_tasks"] >= 1