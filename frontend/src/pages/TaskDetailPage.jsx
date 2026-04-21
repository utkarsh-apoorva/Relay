import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MarkdownRenderer from '../components/MarkdownRenderer';
import MarkdownEditor from '../components/MarkdownEditor';
import { api, ApiError } from '../api/client';

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

function Section({ title, accent, children }) {
  return (
    <div className="tdp-section" style={accent ? { borderLeft: `3px solid ${accent}`, paddingLeft: 12 } : {}}>
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
  const [editingField, setEditingField] = useState(null); // 'description' | 'eval_brief' | 'result_description' | 'judgement' | null
  const [draft, setDraft] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

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

  // Humans only. Comment form is for human viewers only.
  const showCommentForm = true;

  const assignee = task?.assignee_name || task?.assignee_id || 'Unassigned';
  const project = projects.find((p) => p.id === task?.project_id);

  const sectionAccentMap = {
    'description': null,
    'eval_brief': '#f0a732',
    'result_description': '#2adfaa',
    'judgement': '#7c6aff',
  };

  const startEditing = (field, value) => {
    setEditingField(field);
    setDraft(value || '');
    setFieldErrors({});
  };

  const cancelEditing = () => {
    setEditingField(null);
    setDraft('');
    setFieldErrors({});
  };

  const saveField = async (fieldName) => {
    try {
      await api(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        body: JSON.stringify({ [fieldName]: draft }),
      });
      const updated = await api(`/api/tasks/${taskId}`);
      setTask(updated);
      cancelEditing();
    } catch (err) {
      if (err instanceof ApiError && err.field) {
        setFieldErrors({ [err.field]: err.message });
      }
    }
  };

  if (loading) return <div className="tdp-loading">Loading task...</div>;
  if (!task) return <div className="tdp-loading">Task not found.</div>;

  return (
    <div className="tdp-layout">
      {/* Header */}
      <div className="tdp-header">
        <button className="tdp-back" onClick={() => navigate(`/projects/${projectId}`)}>
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
          <Section title="Description">
            {editingField === 'description' ? (
              <div className="tdp-section-edit-mode">
                <MarkdownEditor value={draft} onChange={setDraft} />
                {fieldErrors.description && <p className="tdp-field-error">{fieldErrors.description}</p>}
                <div className="tdp-edit-bar">
                  <button className="secondary-button" onClick={cancelEditing}>Cancel</button>
                  <button className="primary-button" onClick={() => saveField('description')}>Save</button>
                </div>
              </div>
            ) : (
              <div className="tdp-section-view">
                {task.description
                  ? <MarkdownRenderer content={task.description} />
                  : <p className="tdp-empty-placeholder">No description yet. <button className="tdp-section-edit-btn" onClick={() => startEditing('description', '')}>Add one</button></p>
                }
                <button className="tdp-section-edit-btn" onClick={() => startEditing('description', task.description || '')}>✏️ {task.description ? 'Edit' : 'Add'}</button>
              </div>
            )}
          </Section>

          <Section title="Eval Brief" accent={sectionAccentMap['eval_brief']}>
            {editingField === 'eval_brief' ? (
              <div className="tdp-section-edit-mode">
                <MarkdownEditor value={draft} onChange={setDraft} />
                {fieldErrors.eval_brief && <p className="tdp-field-error">{fieldErrors.eval_brief}</p>}
                <div className="tdp-edit-bar">
                  <button className="secondary-button" onClick={cancelEditing}>Cancel</button>
                  <button className="primary-button" onClick={() => saveField('eval_brief')}>Save</button>
                </div>
              </div>
            ) : (
              <div className="tdp-section-view">
                {task.eval_brief
                  ? <MarkdownRenderer content={task.eval_brief} />
                  : <p className="tdp-empty-placeholder">No eval brief yet. <button className="tdp-section-edit-btn" onClick={() => startEditing('eval_brief', '')}>Add one</button></p>
                }
                <button className="tdp-section-edit-btn" onClick={() => startEditing('eval_brief', task.eval_brief || '')}>✏️ {task.eval_brief ? 'Edit' : 'Add'}</button>
              </div>
            )}
          </Section>

          <Section title="Result" accent={sectionAccentMap['result_description']}>
            {editingField === 'result_description' ? (
              <div className="tdp-section-edit-mode">
                <MarkdownEditor value={draft} onChange={setDraft} />
                {fieldErrors.result_description && <p className="tdp-field-error">{fieldErrors.result_description}</p>}
                <div className="tdp-edit-bar">
                  <button className="secondary-button" onClick={cancelEditing}>Cancel</button>
                  <button className="primary-button" onClick={() => saveField('result_description')}>Save</button>
                </div>
              </div>
            ) : (
              <div className="tdp-section-view">
                {task.result_description
                  ? <MarkdownRenderer content={task.result_description} />
                  : <p className="tdp-empty-placeholder">No result yet. <button className="tdp-section-edit-btn" onClick={() => startEditing('result_description', '')}>Add one</button></p>
                }
                <button className="tdp-section-edit-btn" onClick={() => startEditing('result_description', task.result_description || '')}>✏️ {task.result_description ? 'Edit' : 'Add'}</button>
              </div>
            )}
          </Section>

          <Section title="Judgement" accent={sectionAccentMap['judgement']}>
            {editingField === 'judgement' ? (
              <div className="tdp-section-edit-mode">
                <MarkdownEditor value={draft} onChange={setDraft} />
                {fieldErrors.judgement && <p className="tdp-field-error">{fieldErrors.judgement}</p>}
                <div className="tdp-edit-bar">
                  <button className="secondary-button" onClick={cancelEditing}>Cancel</button>
                  <button className="primary-button" onClick={() => saveField('judgement')}>Save</button>
                </div>
              </div>
            ) : (
              <div className="tdp-section-view">
                {task.judgement
                  ? <MarkdownRenderer content={task.judgement} />
                  : <p className="tdp-empty-placeholder">No judgement yet. <button className="tdp-section-edit-btn" onClick={() => startEditing('judgement', '')}>Add one</button></p>
                }
                <button className="tdp-section-edit-btn" onClick={() => startEditing('judgement', task.judgement || '')}>✏️ {task.judgement ? 'Edit' : 'Add'}</button>
              </div>
            )}
          </Section>

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
              {/* Humans only — comment form is for human viewers */}
              {showCommentForm && (
                <form className="tdp-comment-form" onSubmit={submitComment}>
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Add a comment..."
                    rows={3}
                  />
                  <button type="submit" className="primary-button">Post</button>
                </form>
              )}
            </div>
          </Section>
        </div>

        {/* Sidebar */}
        <aside className="tdp-sidebar">
          <div className="tdp-sidebar-card">
            <Field label="Assignee"><span style={{marginRight: 6}}>👤</span>{assignee}</Field>
            <Field label="Reporter">{task.reporter_name || task.reporter_id}</Field>
            <Field label="Due date">{task.due_date || 'Not set'}</Field>
            <Field label="Sprint">{task.sprint_name || 'No sprint'}</Field>
            <Field label="Project">{project?.name}</Field>
            {task.tags && (
              <Field label="Tags">
                <div className="tdp-tags">
                  {task.tags.split(',').map((t) => t.trim()).filter(Boolean).map((tag) => (
                    <span key={tag} className="tdp-tag">{tag}</span>
                  ))}
                </div>
              </Field>
            )}
            <Field label="Status"><span className="tdp-badge" style={{background: STATUS_COLORS[task.status] || '#4a4a55'}}>{task.status}</span></Field>
            <Field label="Priority"><span className="tdp-badge" style={{background: PRIORITY_COLORS[task.priority] || '#4a4a55'}}>{task.priority}</span></Field>
            <Field label="Created">{new Date(task.created_at).toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'})}</Field>
            <Field label="Updated">{new Date(task.updated_at).toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'})}</Field>
          </div>
        </aside>
      </div>
    </div>
  );
}