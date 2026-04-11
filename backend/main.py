from pathlib import Path
import json
from datetime import datetime
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import Base, engine, get_db, SessionLocal
from .models import Agent, Project, Sprint, Task, Comment, ApiKey
from .seed import seed

app = FastAPI(title='AgentOS')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed(db)

def auth(x_api_key: str | None, db: Session):
    if x_api_key is None or not db.query(ApiKey).filter(ApiKey.key == x_api_key).first():
        raise HTTPException(401, 'Invalid API key')

def to_dict_task(t, db):
    comments = db.query(Comment).filter(Comment.task_id == t.id).all()
    return {k: getattr(t, k) for k in ['id','project_id','sprint_id','title','description','assignee_id','reporter_id','priority','status','tags','due_date','created_at','updated_at']} | {'comments': [{'id': c.id, 'author_id': c.author_id, 'author_type': c.author_type, 'content': c.content, 'created_at': c.created_at} for c in comments]}

@app.get('/api/projects')
def list_projects(db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    projects = db.query(Project).all()
    out=[]
    for p in projects:
        total=db.query(Task).filter(Task.project_id==p.id).count()
        done=db.query(Task).filter(Task.project_id==p.id, Task.status=='Done').count()
        lead=db.query(Agent).filter(Agent.id==p.lead_agent_id).first()
        out.append({'id':p.id,'name':p.name,'description':p.description,'status':p.status,'lead_agent_id':p.lead_agent_id,'lead_agent_name':lead.name if lead else p.lead_agent_id,'sprint_count':db.query(Sprint).filter(Sprint.project_id==p.id).count(),'task_count':total,'% done':round((done/total*100) if total else 0,1),'last_updated':p.updated_at})
    return out

@app.post('/api/projects')
def create_project(payload: dict, db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    p=Project(name=payload['name'], description=payload.get('description',''), status=payload.get('status','Active'), lead_agent_id=payload.get('lead_agent_id','gandalf'))
    db.add(p); db.commit(); db.refresh(p); return {'id':p.id}

@app.get('/api/agents')
def list_agents(db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    agents=db.query(Agent).all()
    return [{'id':a.id,'name':a.name,'avatar':a.avatar,'role':a.role,'model':a.model,'provider':a.provider,'status':a.status,'last_active':a.last_active,'current_tasks':db.query(Task).filter(Task.assignee_id==a.id, Task.status=='In Progress').count()} for a in agents]

@app.get('/api/tasks')
def list_tasks(project_id:int|None=None, assignee_id:str|None=None, status:str|None=None, sprint_id:int|None=None, db:Session=Depends(get_db), x_api_key:str|None=Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    q=db.query(Task)
    if project_id is not None: q=q.filter(Task.project_id==project_id)
    if assignee_id is not None: q=q.filter(Task.assignee_id==assignee_id)
    if status is not None: q=q.filter(Task.status==status)
    if sprint_id is not None: q=q.filter(Task.sprint_id==sprint_id)
    return [to_dict_task(t, db) for t in q.order_by(Task.updated_at.desc()).all()]

@app.post('/api/tasks')
def create_task(payload: dict, db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    assignee = payload.get('assignee_id','')
    title = payload['title']
    t=Task(project_id=payload['project_id'], sprint_id=payload.get('sprint_id'), title=title, description=payload.get('description',''), assignee_id=assignee, reporter_id=payload.get('reporter_id','utkarsh'), priority=payload.get('priority','P2'), status=payload.get('status','Backlog'), tags=payload.get('tags',''), due_date=payload.get('due_date',''))
    if payload.get('comment'):
        db.add(t); db.commit(); db.refresh(t)
        db.add(Comment(task_id=t.id, author_id=payload.get('reporter_id','utkarsh'), author_type='human' if payload.get('reporter_id','utkarsh')=='utkarsh' else 'agent', content=payload['comment']))
        db.commit(); return to_dict_task(t, db)
    db.add(t); db.commit(); db.refresh(t); return to_dict_task(t, db)

@app.patch('/api/tasks/{task_id}')
def patch_task(task_id:int, payload: dict, db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    t=db.query(Task).get(task_id)
    if not t: raise HTTPException(404)
    for k in ['title','description','assignee_id','reporter_id','priority','status','tags','due_date','sprint_id']:
        if k in payload: setattr(t,k,payload[k])
    t.updated_at=datetime.utcnow().isoformat(); db.commit(); db.refresh(t); return to_dict_task(t, db)

@app.post('/api/tasks/{task_id}/comment')
def add_comment(task_id:int, payload: dict, db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    c=Comment(task_id=task_id, author_id=payload.get('author_id','utkarsh'), author_type=payload.get('author_type','human'), content=payload['content'])
    db.add(c); db.commit(); return {'ok':True}

@app.get('/api/sprints')
def list_sprints(db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    return [{'id':s.id,'project_id':s.project_id,'name':s.name,'start_date':s.start_date,'end_date':s.end_date} for s in db.query(Sprint).all()]

@app.get('/api/usage/tokens')
def usage(db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    root = Path.home()/'.openclaw/agents'
    rates={'openai/gpt-5.4-mini':0.000015,'anthropic/claude-sonnet-4-6':0.00003,'zai/glm-5.1':0.00001}
    rows=[]
    totals={}
    if root.exists():
        for agentdir in root.iterdir():
            sess=agentdir/'sessions'/'sessions.json'
            if not sess.exists(): continue
            try: data=json.loads(sess.read_text())
            except Exception: continue
            for entry in data if isinstance(data,list) else data.get('sessions',[]):
                model=entry.get('model','unknown'); toks=int(entry.get('usage',{}).get('total_tokens', entry.get('total_tokens',0)))
                agent=agentdir.name; cost=toks/1000*rates.get(model,0.0)
                rows.append({'agent':agent,'model':model,'tokens':toks,'estimated_cost':round(cost,4)})
                totals[(agent,model)] = totals.get((agent,model),0)+toks
    return {'rows':rows,'totals':[{'agent':a,'model':m,'tokens':t} for (a,m),t in totals.items()]}

@app.get('/api/calendar')
def calendar(project_id:int|None=None, db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    q=db.query(Task).filter(Task.due_date!='')
    if project_id is not None: q=q.filter(Task.project_id==project_id)
    return [{'id':t.id,'title':t.title,'due_date':t.due_date,'project_id':t.project_id,'status':t.status} for t in q.all()]

@app.get('/api/approval-queue')
def approval_queue(db: Session = Depends(get_db), x_api_key: str | None = Header(default=None, alias='X-API-Key')):
    auth(x_api_key, db)
    return [to_dict_task(t, db) for t in db.query(Task).filter(Task.assignee_id=='utkarsh').all()]
