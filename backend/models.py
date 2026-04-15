from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    avatar: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="")
    model: Mapped[str] = mapped_column(String, default="")
    provider: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="Idle")
    last_active: Mapped[str] = mapped_column(String, default="")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="Active")
    lead_agent_id: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())


class Sprint(Base):
    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String)
    start_date: Mapped[str] = mapped_column(String, default="")
    end_date: Mapped[str] = mapped_column(String, default="")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    sprint_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sprints.id"), nullable=True, default=None)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    assignee_id: Mapped[str] = mapped_column(String, default="")
    reporter_id: Mapped[str] = mapped_column(String, default="")
    priority: Mapped[str] = mapped_column(String, default="P2")
    status: Mapped[str] = mapped_column(String, default="Backlog")
    tags: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    author_id: Mapped[str] = mapped_column(String)
    author_type: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String)
    key: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True, default=None)
    key_hash: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True, default=None)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat())
