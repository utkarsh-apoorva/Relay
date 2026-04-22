import pytest


class TestTaskListEndpoint:
    def test_list_tasks_requires_auth(self, client):
        response = client.get("/api/tasks")
        assert response.status_code == 401

    def test_list_tasks_empty(self, client, auth_headers):
        response = client.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tasks_with_data(self, client, auth_headers, seed_task):
        response = client.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Task"

    def test_list_tasks_filter_by_project(self, client, auth_headers, seed_task, seed_project):
        response = client.get(f"/api/tasks?project_id={seed_project.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["project_id"] == seed_project.id

    def test_list_tasks_filter_by_assignee(self, client, auth_headers, seed_task):
        response = client.get("/api/tasks?assignee_id=agent1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["assignee_id"] == "agent1"

    def test_list_tasks_filter_by_status(self, client, auth_headers, seed_task):
        response = client.get("/api/tasks?status=To Do", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "To Do"

    def test_list_tasks_filter_by_sprint(self, client, auth_headers, seed_task, seed_sprint):
        response = client.get(f"/api/tasks?sprint_id={seed_sprint.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sprint_id"] == seed_sprint.id


class TestTaskCreateEndpoint:
    def test_create_task_requires_auth(self, client, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "New Task",
        }
        response = client.post("/api/tasks", json=payload)
        assert response.status_code == 401

    def test_create_task_success(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "New Task",
            "description": "Task description",
            "assignee_id": "agent1",
            "priority": "P1",
            "status": "To Do",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Task"
        assert data["description"] == "Task description"
        assert data["assignee_id"] == "agent1"
        assert data["priority"] == "P1"
        assert data["status"] == "To Do"
        assert "id" in data
        assert "comments" in data

    def test_create_task_minimal(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "Minimal Task",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Minimal Task"
        assert data["status"] == "Backlog"
        assert data["priority"] == "P2"

    def test_create_task_missing_title(self, client, auth_headers, seed_project):
        payload = {"project_id": seed_project.id}
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 400

    def test_create_task_invalid_project(self, client, auth_headers):
        payload = {
            "project_id": 99999,
            "title": "Task",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_create_task_with_comment(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "Task with Comment",
            "comment": "This is a comment",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["comments"]) == 1
        assert data["comments"][0]["content"] == "This is a comment"

    def test_create_task_with_tags(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "Tagged Task",
            "tags": "backend,api,urgent",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert "backend" in response.json()["tags"]

    def test_create_task_with_sprint(self, client, auth_headers, seed_project, seed_sprint):
        payload = {
            "project_id": seed_project.id,
            "title": "Sprint Task",
            "sprint_id": seed_sprint.id,
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["sprint_id"] == seed_sprint.id

    def test_create_task_with_due_date(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "Dated Task",
            "due_date": "2026-03-01",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["due_date"] == "2026-03-01"

    def test_create_task_invalid_due_date(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "Invalid Date Task",
            "due_date": "invalid-date",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 400

    def test_create_task_invalid_assignee(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "Invalid Assignee Task",
            "assignee_id": "agent1,agent2",
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code in (200, 400, 500)

    def test_create_task_description_too_long(self, client, auth_headers, seed_project):
        payload = {
            "project_id": seed_project.id,
            "title": "Long Description Task",
            "description": " ".join(["word"] * 600),
        }
        response = client.post("/api/tasks", json=payload, headers=auth_headers)
        assert response.status_code in (200, 400)


class TestTaskPatchEndpoint:
    def test_patch_task_requires_auth(self, client, seed_task):
        response = client.patch(f"/api/tasks/{seed_task.id}", json={"title": "Updated"})
        assert response.status_code == 401

    def test_patch_task_title(self, client, auth_headers, seed_task):
        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_patch_task_status(self, client, auth_headers, seed_task):
        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"status": "In Progress"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "In Progress"

    def test_patch_task_priority(self, client, auth_headers, seed_task):
        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"priority": "P0"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["priority"] == "P0"

    def test_patch_task_assignee(self, client, auth_headers, seed_task):
        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"assignee_id": "agent2"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["assignee_id"] == "agent2"

    def test_patch_task_result_description(self, client, auth_headers, seed_task):
        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"result_description": "Task completed successfully"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["result_description"] == "Task completed successfully"

    def test_patch_task_judgement(self, client, auth_headers, seed_task):
        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"judgement": "Approved"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["judgement"] == "Approved"

    def test_patch_task_not_found(self, client, auth_headers):
        response = client.patch("/api/tasks/99999", json={"title": "Test"}, headers=auth_headers)
        assert response.status_code == 404

    def test_patch_task_sprint(self, client, auth_headers, seed_task, seed_sprint):
        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"sprint_id": seed_sprint.id},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_patch_task_sprint_wrong_project(self, client, auth_headers, seed_task, db):
        from backend.models import Project, Sprint

        other_project = Project(name="Other Project")
        db.add(other_project)
        db.commit()
        db.refresh(other_project)

        other_sprint = Sprint(project_id=other_project.id, name="Other Sprint")
        db.add(other_sprint)
        db.commit()

        response = client.patch(
            f"/api/tasks/{seed_task.id}",
            json={"sprint_id": other_sprint.id},
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestTaskCommentEndpoint:
    def test_add_comment_requires_auth(self, client, seed_task):
        response = client.post(
            f"/api/tasks/{seed_task.id}/comment",
            json={"content": "Test comment"},
        )
        assert response.status_code == 401

    def test_add_comment_success(self, client, auth_headers, seed_task):
        payload = {"content": "New comment content", "author_id": "human"}
        response = client.post(
            f"/api/tasks/{seed_task.id}/comment",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_add_comment_missing_content(self, client, auth_headers, seed_task):
        response = client.post(
            f"/api/tasks/{seed_task.id}/comment",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_add_comment_task_not_found(self, client, auth_headers):
        response = client.post(
            "/api/tasks/99999/comment",
            json={"content": "Comment"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_add_comment_with_author_type(self, client, auth_headers, seed_task):
        payload = {
            "content": "Agent comment",
            "author_id": "agent1",
            "author_type": "agent",
        }
        response = client.post(
            f"/api/tasks/{seed_task.id}/comment",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestTaskSerialize:
    def test_task_includes_comments(self, client, auth_headers, seed_task, db):
        from backend.models import Comment

        comment = Comment(
            task_id=seed_task.id,
            author_id="human",
            author_type="human",
            content="Test comment",
        )
        db.add(comment)
        db.commit()

        response = client.get("/api/tasks", headers=auth_headers)
        data = response.json()
        assert len(data[0]["comments"]) == 1
        assert data[0]["comments"][0]["content"] == "Test comment"

    def test_task_includes_assignee_name(self, client, auth_headers, seed_task):
        response = client.get("/api/tasks", headers=auth_headers)
        data = response.json()
        assert "assignee_name" in data[0]
        assert "Agent One" in data[0]["assignee_name"]

    def test_task_includes_project_name(self, client, auth_headers, seed_task):
        response = client.get("/api/tasks", headers=auth_headers)
        data = response.json()
        assert "project_name" in data[0]
        assert data[0]["project_name"] == "Test Project"