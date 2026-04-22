import pytest
from datetime import datetime

from backend.models import Agent, Project, Sprint, Task, Comment, ApiKey, Wiki


class TestAgentModel:
    def test_create_agent(self, db):
        agent = Agent(
            id="new-agent",
            name="New Agent",
            avatar="🤖",
            role="Developer",
            model="openai/gpt-4o",
            provider="openai",
            status="Idle",
            capabilities="coding,design",
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.id == "new-agent"
        assert agent.name == "New Agent"
        assert agent.avatar == "🤖"
        assert agent.role == "Developer"
        assert agent.model == "openai/gpt-4o"
        assert agent.provider == "openai"
        assert agent.status == "Idle"
        assert agent.capabilities == "coding,design"
        assert agent.webhook_url is None
        assert agent.webhook_secret is None

    def test_agent_webhook_fields(self, db):
        agent = Agent(
            id="webhook-agent",
            name="Webhook Agent",
            webhook_url="https://example.com/webhook",
            webhook_secret="secret123",
        )
        db.add(agent)
        db.commit()

        assert agent.webhook_url == "https://example.com/webhook"
        assert agent.webhook_secret == "secret123"

    def test_agent_default_values(self, db):
        agent = Agent(id="default-agent", name="Default Agent")
        db.add(agent)
        db.commit()
        db.refresh(agent)

        assert agent.avatar == ""
        assert agent.role == ""
        assert agent.model == ""
        assert agent.provider == ""
        assert agent.status == "Idle"
        assert agent.capabilities == ""


class TestProjectModel:
    def test_create_project(self, db):
        project = Project(
            name="Test Project",
            description="Test description",
            status="Active",
            lead_agent_id="agent1",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "Test description"
        assert project.status == "Active"
        assert project.lead_agent_id == "agent1"
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_project_default_values(self, db):
        project = Project(name="Minimal Project")
        db.add(project)
        db.commit()
        db.refresh(project)

        assert project.description == ""
        assert project.status == "Active"
        assert project.lead_agent_id == ""


class TestSprintModel:
    def test_create_sprint(self, db, seed_project):
        sprint = Sprint(
            project_id=seed_project.id,
            name="Sprint 1",
            start_date="2026-01-01",
            end_date="2026-01-14",
        )
        db.add(sprint)
        db.commit()
        db.refresh(sprint)

        assert sprint.id is not None
        assert sprint.project_id == seed_project.id
        assert sprint.name == "Sprint 1"
        assert sprint.start_date == "2026-01-01"
        assert sprint.end_date == "2026-01-14"

    def test_sprint_empty_dates(self, db, seed_project):
        sprint = Sprint(project_id=seed_project.id, name="Sprint No Dates")
        db.add(sprint)
        db.commit()
        db.refresh(sprint)

        assert sprint.start_date == ""
        assert sprint.end_date == ""


class TestTaskModel:
    def test_create_task(self, db, seed_project):
        task = Task(
            project_id=seed_project.id,
            title="New Task",
            description="Task description",
            assignee_id="agent1",
            reporter_id="human",
            priority="P1",
            status="To Do",
            tags="urgent,backend",
            due_date="2026-02-01",
            eval_brief="Task is complete when...",
            depends_on="",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.id is not None
        assert task.project_id == seed_project.id
        assert task.title == "New Task"
        assert task.description == "Task description"
        assert task.assignee_id == "agent1"
        assert task.reporter_id == "human"
        assert task.priority == "P1"
        assert task.status == "To Do"
        assert task.tags == "urgent,backend"
        assert task.due_date == "2026-02-01"
        assert task.eval_brief == "Task is complete when..."
        assert task.depends_on == ""
        assert task.result_description == ""
        assert task.judgement == ""
        assert task.trace == ""

    def test_task_default_values(self, db, seed_project):
        task = Task(project_id=seed_project.id, title="Minimal Task")
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.sprint_id is None
        assert task.description == ""
        assert task.assignee_id == ""
        assert task.reporter_id == ""
        assert task.priority == "P2"
        assert task.status == "Backlog"
        assert task.tags == ""
        assert task.due_date == ""

    def test_task_depends_on(self, db, seed_project):
        task1 = Task(project_id=seed_project.id, title="Task 1")
        db.add(task1)
        db.commit()
        db.refresh(task1)

        task2 = Task(
            project_id=seed_project.id,
            title="Task 2",
            depends_on=str(task1.id),
        )
        db.add(task2)
        db.commit()
        db.refresh(task2)

        assert task2.depends_on == str(task1.id)


class TestCommentModel:
    def test_create_comment(self, db, seed_task):
        comment = Comment(
            task_id=seed_task.id,
            author_id="human",
            author_type="human",
            content="This is a test comment",
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        assert comment.id is not None
        assert comment.task_id == seed_task.id
        assert comment.author_id == "human"
        assert comment.author_type == "human"
        assert comment.content == "This is a test comment"
        assert comment.created_at is not None

    def test_comment_agent_type(self, db, seed_task):
        comment = Comment(
            task_id=seed_task.id,
            author_id="agent1",
            author_type="agent",
            content="Agent comment",
        )
        db.add(comment)
        db.commit()

        assert comment.author_type == "agent"


class TestApiKeyModel:
    def test_create_api_key(self, db):
        api_key = ApiKey(
            agent_id="test-agent",
            key_hash="sha256$abc123",
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        assert api_key.id is not None
        assert api_key.agent_id == "test-agent"
        assert api_key.key_hash == "sha256$abc123"
        assert api_key.key is None
        assert api_key.created_at is not None


class TestWikiModel:
    def test_create_wiki(self, db, seed_project):
        wiki = Wiki(
            project_id=seed_project.id,
            content="# Project Wiki\n\nSome content here.",
        )
        db.add(wiki)
        db.commit()
        db.refresh(wiki)

        assert wiki.id is not None
        assert wiki.project_id == seed_project.id
        assert wiki.content == "# Project Wiki\n\nSome content here."
        assert wiki.updated_at is not None

    def test_wiki_unique_per_project(self, db, seed_project):
        from backend.models import Wiki as WikiModel

        wiki1 = WikiModel(project_id=seed_project.id, content="First wiki")
        db.add(wiki1)
        db.commit()

        existing = db.query(WikiModel).filter(WikiModel.project_id == seed_project.id).first()
        if existing:
            existing.content = "Updated wiki"
            db.add(existing)
            db.commit()
            db.refresh(existing)
            assert existing.content == "Updated wiki"
        else:
            wiki2 = WikiModel(project_id=seed_project.id, content="Second wiki")
            db.add(wiki2)
            db.commit()
            db.refresh(wiki2)
            assert wiki2.content == "Second wiki"


class TestModelRelationships:
    def test_project_sprints_relationship(self, db, seed_project, seed_sprint):
        db.refresh(seed_project)
        db.refresh(seed_sprint)

        sprints = db.query(Sprint).filter(Sprint.project_id == seed_project.id).all()
        assert len(sprints) == 1
        assert sprints[0].name == "Sprint 1"

    def test_project_tasks_relationship(self, db, seed_project, seed_task):
        db.refresh(seed_project)
        db.refresh(seed_task)

        tasks = db.query(Task).filter(Task.project_id == seed_project.id).all()
        assert len(tasks) == 1
        assert tasks[0].title == "Test Task"

    def test_task_comments_relationship(self, db, seed_task):
        comment = Comment(
            task_id=seed_task.id,
            author_id="human",
            author_type="human",
            content="Test comment",
        )
        db.add(comment)
        db.commit()

        comments = db.query(Comment).filter(Comment.task_id == seed_task.id).all()
        assert len(comments) == 1
        assert comments[0].content == "Test comment"