import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { api } from '../api/client';

const HUMAN_ID = import.meta.env.VITE_RELAY_HUMAN_ID || 'human';

const STATUS_COLORS = {
  'Backlog': '#4a4a55',
  'To Do': '#8b8b99',
  'In Progress': '#f0a732',
  'In Review': '#7c6aff',
  'Done': '#2adfaa',
  'Rejected': '#f05252',
};
const PRIORITY_COLORS = {
  P0: '#f05252',
  P1: '#f0a732',
  P2: '#7c6aff',
  P3: '#4a4a55',
};

function Field({ label, children }) {
  return children ? (
    <div className="tdp-field">
      <span className="tdp-field-label">{label}</span>
      <span className="tdp-field-value">{children}</span>
    </div>
  ) : null;
}

function Section({ title, children }) {
  return (
    <div className="tdp-section">
      {title && <h3 className="tdp-section-title">{title}</h3>}
      {children}
    </div>
  );
}

export default function TaskDetailPage() {
  const { projectId, taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [projects, setProjects] = useState([]);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api(`/api/tasks/${taskId}`),
      api(`/api/projects`),
    ]).then(([t, p]) => {
      setTask(t);
      setProjects(p);
      setLoading(false);
    });
  }, [taskId]);

  const submitComment = async (e) => {
    e.preventDefault();
    if (!comment.trim()) return;
    await api(`/api/tasks/${taskId}/comment`, {
      method: 'POST',
      body: JSON.stringify({ content: comment, author_id: HUMAN_ID }),
    });
    setComment('');
    const t = await api(`/api/tasks/${taskId}`);
    setTask(t);
  };

  if (loading) return <div className="tdp-loading">Loading task...</div>;
  if (!task) return <div className="tdp-loading">Task not found.</div>;

  const assignee = task.assignee_name || task.assignee_id || 'Unassigned';
  const project = projects.find((p) => p.id === task.project_id);

  return (
    <div className="tdp-layout">
      {/* Header */}
      <div className="tdp-header">
        <button className="tdp-back" onClick={() => navigate(-1)}>
          ← Back to {project?.name || 'Project'}
        </button>
        <div className="tdp-title-area">
          <div className="tdp-meta-top">
            <span className="tdp-badge" style={{ background: PRIORITY_COLORS[task.priority] }}>
              {task.priority}
            </span>
            <span className="tdp-badge" style={{ background: STATUS_COLORS[task.status] }}>
              {task.status}
            </span>
            {project && <span className="tdp-project-tag">{project.name}</span>}
          </div>
          <h1 className="tdp-title">{task.title}</h1>
        </div>
      </div>

      <div className="tdp-body">
        {/* Main content */}
        <div className="tdp-main">
          {task.description && (
            <Section title="Description">
              <MarkdownRenderer content={task.description} />
            </Section>
          )}

          {task.eval_brief && (
            <Section title="Eval Brief">
              <MarkdownRenderer content={task.eval_brief} />
            </Section>
          )}

          {task.result_description && (
            <Section title="Result">
              <MarkdownRenderer content={task.result_description} />
            </Section>
          )}

          {task.judgement && (
            <Section title="Judgement">
              <MarkdownRenderer content={task.judgement} />
            </Section>
          )}

          {/* Comments — humans only */}
          <Section title={`Comments (${(task.comments || []).length})`}>
            <div className="tdp-comments">
              {(task.comments || []).map((c) => (
                <div key={c.id} className="tdp-comment">
                  <div className="tdp-comment-head">
                    <span className="tdp-comment-author">{c.author_id === HUMAN_ID ? 'You' : c.author_id}</span>
                    <span className="tdp-comment-date">{new Date(c.created_at).toLocaleString()}</span>
                  </div>
                  <p className="tdp-comment-body">{c.content}</p>
                </div>
              ))}
              <form className="tdp-comment-form" onSubmit={submitComment}>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add a comment..."
                  rows={3}
                />
                <button type="submit" className="primary-button">Post</button>
              </form>
            </div>
          </Section>
        </div>

        {/* Sidebar */}
        <aside className="tdp-sidebar">
          <div className="tdp-sidebar-card">
            <Field label="Assignee"><span style={{marginRight: 6}}>👤</span>{assignee}</Field>
            <Field label="Reporter">{task.reporter_name || task.reporter_id}</Field>
            <Field label="Status"><span className="tdp-badge" style={{background: STATUS_COLORS[task.status] || '#4a4a55'}}>{task.status}</span></Field>
            <Field label="Priority"><span className="tdp-badge" style={{background: PRIORITY_COLORS[task.priority] || '#4a4a55'}}>{task.priority}</span></Field>
            <Field label="Due date">{task.due_date || 'Not set'}</Field>
            <Field label="Sprint">{task.sprint_name || 'No sprint'}</Field>
            <Field label="Project">{project?.name}</Field>
            <Field label="Created">{new Date(task.created_at).toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'})}</Field>
            <Field label="Updated">{new Date(task.updated_at).toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'})}</Field>
            {task.tags && (
              <Field label="Tags">
                <div className="tdp-tags">
                  {task.tags.split(',').map((t) => t.trim()).filter(Boolean).map((tag) => (
                    <span key={tag} className="tdp-tag">{tag}</span>
                  ))}
                </div>
              </Field>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}