import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import TaskDetailPage from './pages/TaskDetailPage'
import ProjectCreationPage from './pages/ProjectCreationPage'
import ProjectPage from './pages/ProjectPage'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/projects/new" element={<ProjectCreationPage />} />
      <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetailPage />} />
      <Route path="/projects/:projectId" element={<ProjectPage />} />
      <Route path="*" element={<App />} />
    </Routes>
  </BrowserRouter>
)