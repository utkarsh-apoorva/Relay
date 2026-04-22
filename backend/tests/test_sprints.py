import pytest


class TestSprintListEndpoint:
    def test_list_sprints_requires_auth(self, client):
        response = client.get("/api/sprints")
        assert response.status_code == 401

    def test_list_sprints_empty(self, client, auth_headers):
        response = client.get("/api/sprints", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sprints_with_data(self, client, auth_headers, seed_sprint):
        response = client.get("/api/sprints", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Sprint 1"

    def test_list_sprints_filter_by_project(self, client, auth_headers, seed_sprint, seed_project):
        response = client.get(f"/api/sprints?project_id={seed_project.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["project_id"] == seed_project.id

    def test_list_sprints_contains_fields(self, client, auth_headers, seed_sprint):
        response = client.get("/api/sprints", headers=auth_headers)
        data = response.json()
        sprint = data[0]
        assert "id" in sprint
        assert "project_id" in sprint
        assert "name" in sprint
        assert "start_date" in sprint
        assert "end_date" in sprint


class TestSprintCreateEndpoint:
    def test_create_sprint_requires_auth(self, client, seed_project):
        payload = {
            "project_id": seed_project.id,
            "name": "New Sprint",
        }
        response = client.post("/api/sprints", json=payload)
        assert response.status_code == 401

    def test_create_sprint_success(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "name": "New Sprint",
            "start_date": "2026-04-01",
            "end_date": "2026-04-14",
        }
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Sprint"
        assert data["project_id"] == seed_project.id
        assert data["start_date"] == "2026-04-01"
        assert data["end_date"] == "2026-04-14"
        assert "id" in data

    def test_create_sprint_minimal(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "name": "Minimal Sprint",
        }
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Sprint"
        assert data["start_date"] == ""
        assert data["end_date"] == ""

    def test_create_sprint_missing_name(self, client, auth_headers, seed_project):
        payload = {"project_id": seed_project.id}
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 400

    def test_create_sprint_missing_project_id(self, client, auth_headers):
        payload = {"name": "Sprint Without Project"}
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 400

    def test_create_sprint_invalid_project(self, client, auth_headers):
        payload = {
            "project_id": 99999,
            "name": "Invalid Project Sprint",
        }
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_create_sprint_name_too_long(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "name": "x" * 200,
        }
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 400

    def test_create_sprint_invalid_date_format(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "name": "Invalid Date Sprint",
            "start_date": "not-a-date",
        }
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 400

    def test_create_sprint_updates_project(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "name": "Project Update Sprint",
        }
        response = client.post("/api/sprints", json=payload, headers=auth_headers)
        assert response.status_code == 200


class TestSprintRelationships:
    def test_sprint_belongs_to_project(self, client, auth_headers, seed_sprint, seed_project):
        response = client.get(f"/api/sprints?project_id={seed_project.id}", headers=auth_headers)
        data = response.json()
        assert data[0]["project_id"] == seed_project.id

    def test_project_sprint_count(self, client, auth_headers, seed_project, seed_sprint):
        response = client.get("/api/projects", headers=auth_headers)
        data = response.json()
        project = next((p for p in data if p["id"] == seed_project.id), None)
        assert project is not None
        assert project["sprint_count"] == 1


class TestSprintTaskIntegration:
    def test_tasks_can_reference_sprint(self, client, auth_headers, seed_task, seed_sprint):
        response = client.get(f"/api/tasks?sprint_id={seed_sprint.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sprint_id"] == seed_sprint.id

    def test_task_sprint_name_in_response(self, client, auth_headers, seed_task, seed_sprint):
        response = client.get("/api/tasks", headers=auth_headers)
        data = response.json()
        task = data[0]
        assert "sprint_name" in task
        assert task["sprint_name"] == "Sprint 1"