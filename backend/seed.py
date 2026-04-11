from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Agent, Project, Sprint, Task, ApiKey

AGENTS = [
    ('gandalf', 'Gandalf', '🧙', 'Orchestrator', 'zai/glm-5.1', 'zai', 'Online'),
    ('ive', 'Ive', '🎨', 'Design & Product', 'anthropic/claude-sonnet-4-6', 'anthropic', 'Idle'),
    ('linus', 'Linus', '🐧', 'Coding', 'openai/gpt-5.4-mini', 'openai', 'Online'),
    ('thanos', 'Thanos', '🟣', 'Experimentation', 'zai/glm-5.1', 'zai', 'Idle'),
]

def seed(db: Session):
    if db.query(Agent).count():
        return
    for a in AGENTS:
        db.add(Agent(id=a[0], name=a[1], avatar=a[2], role=a[3], model=a[4], provider=a[5], status=a[6], last_active=datetime.utcnow().isoformat()))
    db.commit()
    p = Project(name='AgentOS', description='Multi-agent project management', status='Active', lead_agent_id='gandalf')
    db.add(p); db.commit(); db.refresh(p)
    s = Sprint(project_id=p.id, name='MVP Sprint', start_date=datetime.utcnow().date().isoformat(), end_date=(datetime.utcnow()+timedelta(days=14)).date().isoformat())
    db.add(s); db.commit(); db.refresh(s)
    tasks = [
        ('Build backend API', 'Implement tasks, projects, agents, usage endpoints', 'linus', 'gandalf', 'P1', 'In Progress'),
        ('Design dark UI', 'Minimal dashboard and navigation', 'ive', 'gandalf', 'P2', 'To Do'),
        ('Usage parser', 'Read OpenClaw session stores', 'thanos', 'linus', 'P1', 'Backlog'),
        ('Approval flow', 'Support utkarsh approvals', 'utkarsh', 'gandalf', 'P0', 'In Review'),
    ]
    for title, desc, assignee, reporter, priority, status in tasks:
        db.add(Task(project_id=p.id, sprint_id=s.id, title=title, description=desc, assignee_id=assignee, reporter_id=reporter, priority=priority, status=status, tags='agentos', due_date=''))
    db.add(ApiKey(agent_id='gandalf', key='gandalf-key'))
    db.commit()
