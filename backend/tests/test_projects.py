import pytest


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"ok": "true"}


class TestMetaEndpoint:
    def test_meta_requires_auth(self, client):
        response = client.get("/api/meta")
        assert response.status_code == 401

    def test_meta_returns_schema(self, client, auth_headers):
        response = client.get("/api/meta", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert "schema_version" in data
        assert "meta_url" in data
        assert "project_schema" in data
        assert "task_decomposition_rules" in data
        assert "agent_registry" in data
        assert "meta_prompt" in data

    def test_meta_project_schema(self, client, auth_headers):
        response = client.get("/api/meta", headers=auth_headers)
        data = response.json()

        schema = data["project_schema"]
        assert "required_fields" in schema
        assert "field_limits" in schema
        assert "validation_rules" in schema
        assert "name" in schema["required_fields"]

    def test_meta_task_rules(self, client, auth_headers):
        response = client.get("/api/meta", headers=auth_headers)
        data = response.json()

        rules = data["task_decomposition_rules"]
        assert "atomic" in rules
        assert "max_description_words" in rules
        assert rules["max_description_words"] == 500

    def test_meta_agent_registry(self, client, auth_headers):
        response = client.get("/api/meta", headers=auth_headers)
        data = response.json()

        registry = data["agent_registry"]
        assert isinstance(registry, list)
        if registry:
            agent = registry[0]
            assert "id" in agent
            assert "name" in agent
            assert "role" in agent
            assert "model" in agent
            assert "provider" in agent
            assert "status" in agent


class TestProjectListEndpoint:
    def test_list_projects_requires_auth(self, client):
        response = client.get("/api/projects")
        assert response.status_code == 401

    def test_list_projects_empty(self, client, auth_headers):
        response = client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(self, client, auth_headers, seed_project):
        response = client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Project"

    def test_list_projects_ordered_by_updated_at(self, client, auth_headers, db, seed_project):
        from backend.models import Project
        from datetime import datetime

        project2 = Project(name="Newer Project", status="Active")
        db.add(project2)
        db.commit()
        db.refresh(project2)

        response = client.get("/api/projects", headers=auth_headers)
        data = response.json()
        assert data[0]["name"] == "Newer Project"


class TestProjectCreateEndpoint:
    def test_create_project_requires_auth(self, client):
        response = client.post("/api/projects", json={"name": "New Project"})
        assert response.status_code == 401

    def test_create_project_success(self, client, auth_headers):
        payload = {
            "name": "New Project",
            "description": "A new project",
            "status": "Active",
        }
        response = client.post("/api/projects", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Project"
        assert data["description"] == "A new project"
        assert data["status"] == "Active"
        assert "id" in data
        assert "task_count" in data
        assert "% done" in data

    def test_create_project_minimal(self, client, auth_headers):
        payload = {"name": "Minimal Project"}
        response = client.post("/api/projects", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Minimal Project"

    def test_create_project_missing_name(self, client, auth_headers):
        response = client.post("/api/projects", json={}, headers=auth_headers)
        assert response.status_code in (400, 500)

    def test_create_project_name_too_long(self, client, auth_headers):
        payload = {"name": "x" * 200}
        response = client.post("/api/projects", json=payload, headers=auth_headers)
        assert response.status_code in (400, 500)

    def test_create_project_description_too_long(self, client, auth_headers):
        payload = {"name": "Valid Name", "description": "x" * 6000}
        response = client.post("/api/projects", json=payload, headers=auth_headers)
        assert response.status_code in (400, 500)


class TestProjectPatchEndpoint:
    def test_patch_project_requires_auth(self, client, seed_project):
        response = client.patch(f"/api/projects/{seed_project.id}", json={"name": "New Name"})
        assert response.status_code == 401

    def test_patch_project_name(self, client, auth_headers, seed_project):
        response = client.patch(
            f"/api/projects/{seed_project.id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_patch_project_description(self, client, auth_headers, seed_project):
        response = client.patch(
            f"/api/projects/{seed_project.id}",
            json={"description": "Updated description"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"

    def test_patch_project_status(self, client, auth_headers, seed_project):
        response = client.patch(
            f"/api/projects/{seed_project.id}",
            json={"status": "Completed"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Completed"

    def test_patch_project_not_found(self, client, auth_headers):
        response = client.patch("/api/projects/99999", json={"name": "Test"}, headers=auth_headers)
        assert response.status_code == 404


class TestProjectWikiEndpoint:
    def test_get_wiki_not_found(self, client, auth_headers, seed_project):
        response = client.get(f"/api/projects/{seed_project.id}/wiki", headers=auth_headers)
        assert response.status_code == 404

    def test_put_wiki_create(self, client, auth_headers, seed_project):
        payload = {"content": "# Wiki Content\n\nSome content here."}
        response = client.put(
            f"/api/projects/{seed_project.id}/wiki",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "# Wiki Content\n\nSome content here."
        assert data["project_id"] == seed_project.id

    def test_put_wiki_update(self, client, auth_headers, seed_project, db):
        from backend.models import Wiki

        wiki = Wiki(project_id=seed_project.id, content="Original content")
        db.add(wiki)
        db.commit()

        payload = {"content": "Updated content"}
        response = client.put(
            f"/api/projects/{seed_project.id}/wiki",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"

    def test_get_wiki_after_create(self, client, auth_headers, seed_project, db):
        from backend.models import Wiki

        existing = db.query(Wiki).filter(Wiki.project_id == seed_project.id).first()
        if existing:
            existing.content = "Test wiki"
        else:
            db.add(Wiki(project_id=seed_project.id, content="Test wiki"))
        db.commit()

        response = client.get(f"/api/projects/{seed_project.id}/wiki", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["content"] == "Test wiki"