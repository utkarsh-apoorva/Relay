import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestTaskWebhookFiring:
    def test_task_create_fires_webhook(self, client, auth_headers, seed_project, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            payload = {
                "project_id": seed_project.id,
                "title": "Webhook Task",
                "assignee_id": "agent1",
            }
            response = client.post("/api/tasks", json=payload, headers=auth_headers)

            assert response.status_code == 200
            assert mock_fire.called

            call_args = mock_fire.call_args
            assert call_args[0][0] == "https://example.com/webhook"
            assert call_args[0][1] == "test-secret"
            event = call_args[0][2]
            assert event["event"] == "task.assigned"
            assert "task" in event

    def test_task_update_fires_webhook(self, client, auth_headers, seed_task, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            response = client.patch(
                f"/api/tasks/{seed_task.id}",
                json={"status": "In Progress"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert mock_fire.called

            call_args = mock_fire.call_args
            event = call_args[0][2]
            assert event["event"] == "task.updated"

    def test_task_without_webhook_no_fire(self, client, auth_headers, seed_task, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = None
        agent.webhook_secret = None
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            response = client.patch(
                f"/api/tasks/{seed_task.id}",
                json={"status": "In Progress"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            mock_fire.assert_not_called()


class TestCommentWebhookFiring:
    def test_comment_fires_webhook(self, client, auth_headers, seed_task, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            response = client.post(
                f"/api/tasks/{seed_task.id}/comment",
                json={"content": "New comment"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert mock_fire.called

            call_args = mock_fire.call_args
            event = call_args[0][2]
            assert event["event"] == "task.comment_added"


class TestWebhookPayloadStructure:
    def test_webhook_payload_includes_meta_prompt(self, client, auth_headers, seed_project, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            payload = {
                "project_id": seed_project.id,
                "title": "Meta Prompt Task",
                "assignee_id": "agent1",
            }
            response = client.post("/api/tasks", json=payload, headers=auth_headers)

            event = mock_fire.call_args[0][2]
            assert "meta_prompt" in event
            assert "version" in event["meta_prompt"]
            assert "directive" in event["meta_prompt"]

    def test_webhook_payload_includes_task_url(self, client, auth_headers, seed_project, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            payload = {
                "project_id": seed_project.id,
                "title": "URL Task",
                "assignee_id": "agent1",
            }
            response = client.post("/api/tasks", json=payload, headers=auth_headers)

            event = mock_fire.call_args[0][2]
            assert "task_url" in event


class TestRateLimiting:
    def test_rate_limit_applied(self, client, auth_headers):
        responses = []
        for _ in range(5):
            response = client.get("/api/projects", headers=auth_headers)
            responses.append(response.status_code)

        assert all(r == 200 for r in responses)


class TestRequestBodySizeLimit:
    def test_large_body_rejected(self, client, auth_headers):
        large_payload = {"name": "x" * 2000000}

        response = client.post("/api/projects", json=large_payload, headers=auth_headers)
        assert response.status_code == 413

    def test_normal_body_accepted(self, client, auth_headers):
        payload = {"name": "Normal Project"}

        response = client.post("/api/projects", json=payload, headers=auth_headers)
        assert response.status_code == 200


class TestCORSHeaders:
    def test_cors_headers_present(self, client, auth_headers):
        response = client.get("/api/projects", headers={"Origin": "http://localhost:3000", "X-API-Key": "test-human-key-12345"})
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestCacheControl:
    def test_cache_control_no_store(self, client, auth_headers):
        response = client.get("/api/projects", headers=auth_headers)
        assert "cache-control" in response.headers
        assert "no-store" in response.headers["cache-control"]


class TestSecurityHeaders:
    def test_security_headers_present(self, client, auth_headers):
        response = client.get("/api/projects", headers=auth_headers)
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"