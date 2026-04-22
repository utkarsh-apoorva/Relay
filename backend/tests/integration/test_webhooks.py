import pytest
from unittest.mock import patch, MagicMock


class TestWebhookDelivery:
    def test_webhook_delivery_success(self, client, auth_headers, seed_project, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.dispatcher._deliver") as mock_deliver:
            mock_deliver.return_value = True

            response = client.post(
                "/api/tasks",
                json={
                    "project_id": seed_project.id,
                    "title": "Webhook Delivery Test",
                    "assignee_id": "agent1",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_webhook_retry_on_failure(self, client, auth_headers, seed_project, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.dispatcher._deliver") as mock_deliver:
            mock_deliver.return_value = False

            response = client.post(
                "/api/tasks",
                json={
                    "project_id": seed_project.id,
                    "title": "Webhook Retry Test",
                    "assignee_id": "agent1",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert mock_deliver.called


class TestDispatcherSignatures:
    def test_hmac_signature_generation(self):
        import hashlib
        import hmac

        secret = "test-secret"
        body = b'{"event": "test"}'

        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        from backend.dispatcher import _sign
        result = _sign(secret, body)

        assert result == expected

    def test_signature_verification(self):
        import hashlib
        import hmac

        secret = "test-secret"
        body = b'{"event": "task.assigned"}'

        from backend.dispatcher import _sign
        sig = _sign(secret, body)

        assert sig.startswith("sha256=")
        assert len(sig) == 71


class TestWebhookPayloadValidation:
    def test_webhook_payload_has_required_fields(self, client, auth_headers, seed_project, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            response = client.post(
                "/api/tasks",
                json={
                    "project_id": seed_project.id,
                    "title": "Payload Validation Test",
                    "assignee_id": "agent1",
                    "description": "Test description",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            payload = mock_fire.call_args[0][2]

            assert "event" in payload
            assert "task" in payload
            assert "meta_prompt" in payload
            assert "task_url" in payload

            task = payload["task"]
            assert "id" in task
            assert "title" in task
            assert "status" in task
            assert "assignee_id" in task