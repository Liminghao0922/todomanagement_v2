<template>
  <div class="projects-page">
    <!-- 未登录提示 -->
    <div v-if="!authStore.isAuthenticated" class="login-prompt">
      <div class="prompt-content">
        <h2>🔐 Welcome to Project Management</h2>
        <p>Please login to access your projects</p>
        <button @click="handleLogin" class="btn btn-primary btn-lg">
          {{ authStore.isLoading ? '⏳ Logging in...' : '🔐 Login with Microsoft' }}
        </button>
        <p v-if="authStore.error" class="error-text">{{ authStore.error }}</p>
      </div>
    </div>

    <!-- 已登录内容 -->
    <template v-else>
      <div class="header-section">
        <div class="header-top">
          <h1>📁 Projects</h1>
          <button 
            @click="showCreateForm = !showCreateForm" 
            class="btn btn-toggle"
            :class="{ active: showCreateForm }"
          >
            {{ showCreateForm ? '✕ Close' : '➕ New Project' }}
          </button>
        </div>
      </div>

      <!-- 创建表单 -->
      <form v-if="showCreateForm" @submit.prevent="handleCreateProject" class="create-section">
        <div class="create-form">
          <input
            v-model="newForm.name"
            type="text"
            placeholder="Project Name (required)"
            required
            class="input"
          />
          <textarea
            v-model="newForm.description"
            placeholder="Description (optional)"
            class="input textarea"
            rows="2"
          ></textarea>
          <div class="form-row">
            <select v-model="newForm.status" class="input select">
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
            <select v-model="newForm.priority" class="input select">
              <option value="low">Low Priority</option>
              <option value="medium">Medium Priority</option>
              <option value="high">High Priority</option>
            </select>
          </div>
          <div class="form-row">
            <div class="date-field">
              <label>Start Date</label>
              <input
                v-model="newForm.startDate"
                type="date"
                class="input"
              />
            </div>
            <div class="date-field">
              <label>End Date</label>
              <input
                v-model="newForm.endDate"
                type="date"
                class="input"
              />
            </div>
          </div>
          <div class="form-actions">
            <button type="submit" :disabled="loading" class="btn btn-primary">
              {{ loading ? 'Creating...' : 'Create Project' }}
            </button>
            <button type="button" @click="resetForm" class="btn btn-secondary">
              Clear
            </button>
          </div>
        </div>
      </form>

      <div v-if="error" class="error-box">
        ⚠️ {{ error }}
      </div>

      <!-- 搜索和过滤 -->
      <div class="search-section">
        <div class="search-controls">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="🔍 Search by name..."
            class="input search-input"
          />
          <select v-model="statusFilter" class="input filter-select">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </select>
          <select v-model="priorityFilter" class="input filter-select">
            <option value="">All Priority</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading && projects.length === 0" class="loading">
        ⏳ Loading projects...
      </div>

      <!-- 空状态 -->
      <div v-else-if="filteredProjects.length === 0" class="empty-state">
        <p>No projects yet. Create one to get started! 🚀</p>
      </div>

      <!-- 项目卡片视图 -->
      <div v-else class="projects-grid">
        <div
          v-for="project in filteredProjects"
          :key="project.id"
          class="project-card"
          :class="project.status"
        >
          <div class="card-header">
            <h3 class="project-name">{{ project.name }}</h3>
            <div class="card-badges">
              <span class="badge status-badge" :class="project.status">{{ project.status }}</span>
              <span class="badge priority-badge" :class="project.priority">{{ project.priority }}</span>
            </div>
          </div>

          <p v-if="project.description" class="project-description">
            {{ truncate(project.description, 150) }}
          </p>

          <div class="project-dates" v-if="project.startDate || project.endDate">
            <div v-if="project.startDate" class="date-info">
              <span class="label">Start:</span>
              <span class="value">{{ formatDate(project.startDate) }}</span>
            </div>
            <div v-if="project.endDate" class="date-info">
              <span class="label">End:</span>
              <span class="value">{{ formatDate(project.endDate) }}</span>
            </div>
          </div>

          <div class="project-todos" v-if="project.todos && project.todos.length > 0">
            <span class="todo-badge">📋 {{ project.todos.length }} todo{{ project.todos.length !== 1 ? 's' : '' }}</span>
          </div>

          <div class="card-footer">
            <small class="created-date">
              Created {{ formatDate(project.createdAt) }}
            </small>
            <div class="card-actions">
              <button
                @click="openEditDialog(project)"
                class="btn btn-icon btn-edit"
                title="Edit"
              >
                ✏️
              </button>
              <button
                @click="handleDeleteProject(project.id)"
                class="btn btn-icon btn-delete"
                title="Delete"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>

  <!-- 编辑对话框 -->
  <div v-if="editingProject" class="modal-overlay" @click="closeEditDialog">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>Edit Project</h3>
        <button @click="closeEditDialog" class="btn-close">✕</button>
      </div>
      <form @submit.prevent="handleSaveEdit" class="edit-form">
        <div class="form-group">
          <label>Name *</label>
          <input v-model="editForm.name" type="text" class="input" required />
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea v-model="editForm.description" class="input textarea" rows="3"></textarea>
        </div>
        <div class="form-group form-row">
          <div>
            <label>Status</label>
            <select v-model="editForm.status" class="input select">
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div>
            <label>Priority</label>
            <select v-model="editForm.priority" class="input select">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>
        <div class="form-group form-row">
          <div>
            <label>Start Date</label>
            <input v-model="editForm.startDate" type="date" class="input" />
          </div>
          <div>
            <label>End Date</label>
            <input v-model="editForm.endDate" type="date" class="input" />
          </div>
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn btn-primary">Save Changes</button>
          <button type="button" @click="closeEditDialog" class="btn btn-secondary">Cancel</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/authStore'
import { getProjects, createProject, updateProject, deleteProject } from '@/api/projects'
import type { Project } from '@/types'

const authStore = useAuthStore()
const loading = ref(false)
const error = ref('')
const projects = ref<Project[]>([])

// Filters
const searchQuery = ref('')
const statusFilter = ref('')
const priorityFilter = ref('')

// Create form
const newForm = ref({
  name: '',
  description: '',
  status: 'active' as const,
  priority: 'medium' as const,
  startDate: '',
  endDate: '',
})

const showCreateForm = ref(false)
const editingProject = ref<Project | null>(null)
const editForm = ref({
  name: '',
  description: '',
  status: 'active' as const,
  priority: 'medium' as const,
  startDate: '',
  endDate: '',
})

// Filtered projects based on search and filters
const filteredProjects = computed(() => {
  return projects.value.filter((project: Project) => {
    const matchesSearch = !searchQuery.value || 
      project.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (project.description && project.description.toLowerCase().includes(searchQuery.value.toLowerCase()))
    
    const matchesStatus = !statusFilter.value || project.status === statusFilter.value
    const matchesPriority = !priorityFilter.value || project.priority === priorityFilter.value
    
    return matchesSearch && matchesStatus && matchesPriority
  })
})

// Handle login
const handleLogin = async () => {
  const success = await authStore.login()
  if (success && authStore.isAuthenticated) {
    setTimeout(() => {
      loadProjects()
    }, 500)
  }
}

// Format date
const formatDate = (dateString: string | Date) => {
  if (!dateString) return ''
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

// Truncate text
const truncate = (text: string | undefined, length: number) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

// Load projects
const loadProjects = async () => {
  if (!authStore.userId) return
  
  loading.value = true
  error.value = ''
  try {
    projects.value = await getProjects(authStore.userId)
  } catch (err) {
    console.error('Failed to load projects:', err)
    error.value = 'Failed to load projects'
  } finally {
    loading.value = false
  }
}

// Create project
const handleCreateProject = async () => {
  if (!newForm.value.name.trim()) return
  if (!authStore.userId) return

  loading.value = true
  error.value = ''
  try {
    const newProject = await createProject(authStore.userId, {
      name: newForm.value.name,
      description: newForm.value.description || undefined,
      status: newForm.value.status,
      priority: newForm.value.priority,
      startDate: newForm.value.startDate || undefined,
      endDate: newForm.value.endDate || undefined,
    })

    if (newProject) {
      projects.value.unshift(newProject)
      resetForm()
      showCreateForm.value = false
    }
  } catch (err) {
    console.error('Failed to create project:', err)
    error.value = 'Failed to create project'
  } finally {
    loading.value = false
  }
}

// Reset form
const resetForm = () => {
  newForm.value = {
    name: '',
    description: '',
    status: 'active',
    priority: 'medium',
    startDate: '',
    endDate: '',
  }
}

// Open edit dialog
const openEditDialog = (project: Project) => {
  editingProject.value = project
  editForm.value = {
    name: project.name,
    description: project.description || '',
    status: project.status,
    priority: project.priority,
    startDate: project.startDate ? formatDateForInput(project.startDate) : '',
    endDate: project.endDate ? formatDateForInput(project.endDate) : '',
  }
}

// Close edit dialog
const closeEditDialog = () => {
  editingProject.value = null
}

// Format date for input
const formatDateForInput = (dateString: string | Date) => {
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  return date.toISOString().split('T')[0]
}

// Save edit
const handleSaveEdit = async () => {
  if (!editingProject.value || !editForm.value.name.trim()) return

  loading.value = true
  error.value = ''
  try {
    const updated = await updateProject(editingProject.value.id, {
      name: editForm.value.name,
      description: editForm.value.description || undefined,
      status: editForm.value.status,
      priority: editForm.value.priority,
      startDate: editForm.value.startDate || undefined,
      endDate: editForm.value.endDate || undefined,
    })

    if (updated) {
      const index = projects.value.findIndex((p: Project) => p.id === editingProject.value!.id)
      if (index >= 0) {
        projects.value[index] = updated
      }
      closeEditDialog()
    }
  } catch (err) {
    console.error('Failed to save project:', err)
    error.value = 'Failed to save project'
  } finally {
    loading.value = false
  }
}

// Delete project
const handleDeleteProject = async (id: string) => {
  if (confirm('Are you sure you want to delete this project? Associated todos will not be deleted.')) {
    loading.value = true
    error.value = ''
    try {
      const success = await deleteProject(id)
      if (success) {
        projects.value = projects.value.filter((p: Project) => p.id !== id)
      }
    } catch (err) {
      console.error('Failed to delete project:', err)
      error.value = 'Failed to delete project'
    } finally {
      loading.value = false
    }
  }
}

// Page mount
onMounted(() => {
  if (authStore.isAuthenticated) {
    loadProjects()
  }
})
</script>

<style scoped>
.projects-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  background: #fafbfc;
  min-height: 100vh;
}

.login-prompt {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 500px;
}

.prompt-content {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  max-width: 400px;
}

.prompt-content h2 {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.prompt-content p {
  font-size: 1.1rem;
  margin-bottom: 1.5rem;
}

.error-text {
  color: #ffcccc;
  font-size: 0.95rem;
  margin-top: 1rem;
}

.btn-lg {
  padding: 0.875rem 2rem;
  font-size: 1rem;
  width: 100%;
}

/* Header */
.header-section {
  margin-bottom: 2rem;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.header-top h1 {
  font-size: 2rem;
  color: #333;
  margin: 0;
}

/* Create Form */
.create-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  border: 1px solid #e0e0e0;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.date-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.date-field label {
  font-size: 0.9rem;
  color: #666;
  font-weight: 500;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

/* Buttons */
.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

.btn-toggle {
  background: #f0f0f0;
  color: #333;
}

.btn-toggle.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-icon {
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
}

.btn-icon:hover {
  background: #f5f5f5;
}

.btn-edit {
  color: #4CAF50;
}

.btn-delete {
  color: #f44336;
}

/* Input Styles */
.input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  font-family: inherit;
}

.input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.textarea {
  resize: vertical;
  min-height: 100px;
}

.select {
  cursor: pointer;
}

.search-input {
  flex: 1;
  min-width: 250px;
}

.filter-select {
  min-width: 150px;
}

/* Search Section */
.search-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  border: 1px solid #e0e0e0;
}

.search-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

/* Loading & Empty States */
.loading {
  text-align: center;
  padding: 3rem;
  color: #666;
  font-size: 1.1rem;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 12px;
  color: #999;
  border: 2px dashed #ddd;
}

/* Error Box */
.error-box {
  background: #ffebee;
  color: #c62828;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  border-left: 4px solid #f44336;
}

/* Projects Grid */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.project-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid #e0e0e0;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

.project-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
  border-color: #667eea;
}

.project-card.active {
  border-left: 4px solid #4CAF50;
}

.project-card.completed {
  border-left: 4px solid #2196F3;
}

.project-card.archived {
  border-left: 4px solid #999;
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.project-name {
  margin: 0;
  font-size: 1.25rem;
  color: #333;
  flex: 1;
  word-break: break-word;
}

.card-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.badge {
  display: inline-block;
  padding: 0.4rem 0.8rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: capitalize;
}

.status-badge {
  background: #e3f2fd;
  color: #1976d2;
}

.status-badge.active {
  background: #e8f5e9;
  color: #388e3c;
}

.status-badge.completed {
  background: #e1f5fe;
  color: #0277bd;
}

.status-badge.archived {
  background: #f5f5f5;
  color: #666;
}

.priority-badge {
  background: #fff3e0;
  color: #e65100;
}

.priority-badge.low {
  background: #f3e5f5;
  color: #6a1b9a;
}

.priority-badge.medium {
  background: #fff3e0;
  color: #e65100;
}

.priority-badge.high {
  background: #ffebee;
  color: #c62828;
}

.project-description {
  color: #666;
  font-size: 0.95rem;
  margin: 0 0 1rem 0;
  line-height: 1.4;
}

.project-dates {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
  font-size: 0.9rem;
  color: #666;
  flex-wrap: wrap;
}

.date-info {
  display: flex;
  gap: 0.5rem;
}

.date-info .label {
  font-weight: 600;
}

.date-info .value {
  color: #333;
}

.project-todos {
  padding: 0.75rem;
  background: #f5f5f5;
  border-radius: 6px;
  margin: 1rem 0;
}

.todo-badge {
  font-size: 0.9rem;
  color: #667eea;
  font-weight: 600;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid #f0f0f0;
}

.created-date {
  color: #aaa;
  font-size: 0.85rem;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.modal-header h3 {
  margin: 0;
  color: #333;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
  padding: 0;
}

.btn-close:hover {
  color: #333;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  color: #333;
  font-weight: 600;
  font-size: 0.9rem;
}

.form-group.form-row {
  flex-direction: row;
}

.form-group.form-row > div {
  flex: 1;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.modal-actions .btn {
  flex: 1;
}

/* Responsive */
@media (max-width: 768px) {
  .projects-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .search-controls {
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }

  .card-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .header-top {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
