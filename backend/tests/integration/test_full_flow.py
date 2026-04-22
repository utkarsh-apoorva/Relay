import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestFullProjectWorkflow:
    def test_create_project_and_tasks_flow(self, client, auth_headers, db, seed_project, seed_sprint):
        project_payload = {
            "name": "Integration Test Project",
            "description": "A project for integration testing",
            "status": "Active",
        }
        response = client.post("/api/projects", json=project_payload, headers=auth_headers)
        assert response.status_code == 200
        project = response.json()
        project_id = project["id"]
        assert project["name"] == "Integration Test Project"

        sprint_payload = {
            "project_id": project_id,
            "name": "Sprint 1",
            "start_date": "2026-01-01",
            "end_date": "2026-01-14",
        }
        response = client.post("/api/sprints", json=sprint_payload, headers=auth_headers)
        assert response.status_code == 200
        sprint = response.json()
        sprint_id = sprint["id"]

        task1_payload = {
            "project_id": project_id,
            "sprint_id": sprint_id,
            "title": "Task 1",
            "description": "First integration task",
            "assignee_id": "agent1",
            "priority": "P1",
            "status": "To Do",
        }
        response = client.post("/api/tasks", json=task1_payload, headers=auth_headers)
        assert response.status_code == 200
        task1 = response.json()
        task1_id = task1["id"]

        task2_payload = {
            "project_id": project_id,
            "sprint_id": sprint_id,
            "title": "Task 2",
            "description": "Second integration task",
            "assignee_id": "agent2",
            "priority": "P2",
            "status": "To Do",
            "depends_on": str(task1_id),
        }
        response = client.post("/api/tasks", json=task2_payload, headers=auth_headers)
        assert response.status_code == 200

        response = client.get(f"/api/tasks?project_id={project_id}", headers=auth_headers)
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 2

        response = client.patch(
            f"/api/tasks/{task1_id}",
            json={"status": "In Progress"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "In Progress"

        comment_payload = {"content": "Task is progressing well", "author_id": "human"}
        response = client.post(
            f"/api/tasks/{task1_id}/comment",
            json=comment_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

        response = client.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200

    def test_project_kanban_flow(self, client, auth_headers, seed_project):
        project_id = seed_project.id

        for i in range(5):
            response = client.post(
                "/api/tasks",
                json={
                    "project_id": project_id,
                    "title": f"Kanban Task {i+1}",
                    "assignee_id": "agent1",
                    "priority": "P2",
                    "status": "Backlog" if i < 2 else "To Do",
                },
                headers=auth_headers,
            )
            assert response.status_code == 200

        response = client.get(f"/api/tasks?project_id={project_id}", headers=auth_headers)
        tasks = response.json()

        backlog_tasks = [t for t in tasks if t["status"] == "Backlog"]
        todo_tasks = [t for t in tasks if t["status"] == "To Do"]

        assert len(backlog_tasks) == 2
        assert len(todo_tasks) == 3

        task_to_move = todo_tasks[0]
        response = client.patch(
            f"/api/tasks/{task_to_move['id']}",
            json={"status": "In Progress"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_agent_task_assignment_flow(self, client, auth_headers, seed_project):
        project_id = seed_project.id

        response = client.post(
            "/api/tasks",
            json={
                "project_id": project_id,
                "title": "Agent Assignment Test",
                "assignee_id": "agent1",
                "status": "To Do",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        task = response.json()
        assert task["assignee_id"] == "agent1"

        response = client.patch(
            f"/api/tasks/{task['id']}",
            json={"assignee_id": "agent2"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["assignee_id"] == "agent2"

        response = client.get("/api/agents", headers=auth_headers)
        agents = response.json()
        agent1 = next(a for a in agents if a["id"] == "agent1")
        agent2 = next(a for a in agents if a["id"] == "agent2")

        assert agent1["total_tasks"] >= 0
        assert agent2["total_tasks"] >= 0

    def test_sprint_task_integration(self, client, auth_headers, seed_project, seed_sprint):
        project_id = seed_project.id
        sprint_id = seed_sprint.id

        for i in range(3):
            response = client.post(
                "/api/sprints",
                json={
                    "project_id": project_id,
                    "name": f"Sprint {i+2}",
                    "start_date": f"2026-0{i+2}-01",
                    "end_date": f"2026-0{i+2}-14",
                },
                headers=auth_headers,
            )
            assert response.status_code == 200

        response = client.post(
            "/api/tasks",
            json={
                "project_id": project_id,
                "sprint_id": sprint_id,
                "title": "Sprint Task",
                "assignee_id": "agent1",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        task = response.json()
        assert task["sprint_id"] == sprint_id
        assert task["sprint_name"] == "Sprint 1"

        response = client.get(f"/api/sprints?project_id={project_id}", headers=auth_headers)
        sprints = response.json()
        assert len(sprints) == 4

    def test_wiki_full_flow(self, client, auth_headers, seed_project):
        project_id = seed_project.id

        response = client.get(f"/api/projects/{project_id}/wiki", headers=auth_headers)
        assert response.status_code == 404

        wiki_content = "# Project Wiki\n\nThis is the project documentation."
        response = client.put(
            f"/api/projects/{project_id}/wiki",
            json={"content": wiki_content},
            headers=auth_headers,
        )
        assert response.status_code == 200
        wiki = response.json()
        assert wiki["content"] == wiki_content

        response = client.get(f"/api/projects/{project_id}/wiki", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["content"] == wiki_content

        updated_content = "# Updated Wiki\n\nUpdated documentation."
        response = client.put(
            f"/api/projects/{project_id}/wiki",
            json={"content": updated_content},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == updated_content


class TestWebhooksIntegration:
    def test_task_webhook_payload_structure(self, client, auth_headers, seed_project, db):
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
                    "title": "Webhook Test Task",
                    "assignee_id": "agent1",
                },
                headers=auth_headers,
            )

            assert mock_fire.called
            event = mock_fire.call_args[0][2]

            assert "event" in event
            assert event["event"] == "task.assigned"
            assert "task" in event
            assert "meta_prompt" in event
            assert "task_url" in event

    def test_multiple_webhook_events(self, client, auth_headers, seed_task, db):
        from backend.models import Agent

        agent = db.query(Agent).filter(Agent.id == "agent1").first()
        agent.webhook_url = "https://example.com/webhook"
        agent.webhook_secret = "test-secret"
        db.add(agent)
        db.commit()

        with patch("backend.main.fire") as mock_fire:
            mock_fire.return_value = None

            client.patch(
                f"/api/tasks/{seed_task.id}",
                json={"status": "In Progress"},
                headers=auth_headers,
            )

            client.patch(
                f"/api/tasks/{seed_task.id}",
                json={"status": "In Review"},
                headers=auth_headers,
            )

            client.patch(
                f"/api/tasks/{seed_task.id}",
                json={"status": "Done", "result_description": "Completed"},
                headers=auth_headers,
            )

            assert mock_fire.call_count >= 3


class TestEndToEndScenarios:
    def test_orchestration_flow(self, client, auth_headers, seed_db):
        response = client.post(
            "/api/projects",
            json={
                "name": "Orchestration Test",
                "description": "This is a test project with enough description to be valid for orchestration. " * 10,
                "status": "Orchestrating",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        project = response.json()
        project_id = project["id"]

        response = client.get(f"/api/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 200

        response = client.get("/api/meta", headers=auth_headers)
        assert response.status_code == 200
        meta = response.json()
        assert "agent_registry" in meta
        assert len(meta["agent_registry"]) > 0

    def test_api_key_rotation_simulation(self, client, agent1_headers, db):
        from backend.models import ApiKey
        from backend.security import hash_api_key

        response = client.get("/api/agents", headers=agent1_headers)
        assert response.status_code == 200

        api_key = db.query(ApiKey).filter(ApiKey.agent_id == "agent1").first()
        assert api_key is not None
        assert api_key.key is None
        assert api_key.key_hash is not None

        response = client.get("/api/projects", headers=agent1_headers)
        assert response.status_code == 200

    def test_cross_agent_authorization(self, client, agent1_headers):
        response = client.patch(
            "/api/agents/agent2",
            json={},
            headers=agent1_headers,
        )
        assert response.status_code == 403

    def test_meta_endpoint_integration(self, client, auth_headers):
        response = client.get("/api/meta", headers=auth_headers)
        assert response.status_code == 200

        meta = response.json()

        assert meta["schema_version"] == "1.0"
        assert "project_schema" in meta
        assert "task_decomposition_rules" in meta

        rules = meta["task_decomposition_rules"]
        assert rules["max_description_words"] == 500

        agents = meta["agent_registry"]
        assert len(agents) >= 2

    def test_calendar_view_integration(self, client, auth_headers, seed_task):
        response = client.get("/api/calendar", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_approval_queue_integration(self, client, auth_headers):
        response = client.get("/api/approval-queue", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_usage_tokens_endpoint(self, client, auth_headers):
        response = client.get("/api/usage/tokens", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "rows" in data
        assert "totals" in data