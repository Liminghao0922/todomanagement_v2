<template>
  <div class="todos-page">
    <!-- 未登录提示 -->
    <div v-if="!authStore.isAuthenticated" class="login-prompt">
      <div class="prompt-content">
        <h2>🔐 Welcome to Todo Management</h2>
        <p>Please login to access your todos</p>
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
          <h1>📋 My Todos</h1>
          <button
            @click="goToNewTodo"
            class="btn btn-primary"
          >
            ➕ New Todo
          </button>
        </div>
      </div>

      <AIAssistant />

      <div v-if="error" class="error-box">
        ⚠️ {{ error }}
      </div>

      <!-- 搜索和过滤 -->
      <div class="search-section">
        <div class="search-controls">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="🔍 Search by title..."
            class="input search-input"
          />
          <select v-model="statusFilter" class="input filter-select">
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="in-progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
          <select v-model="priorityFilter" class="input filter-select">
            <option value="">All Priority</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div class="filter-controls-secondary">
          <select v-model="projectFilter" class="input filter-select">
            <option value="">All Projects</option>
            <option v-for="proj in projects" :key="proj.id" :value="proj.id">
              {{ proj.name }}
            </option>
          </select>
          <select v-model="categoryFilter" class="input filter-select">
            <option value="">All Categories</option>
            <option v-for="cat in categories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
          <select v-model="complexityFilter" class="input filter-select">
            <option value="">All Complexity</option>
            <option value="simple">Simple</option>
            <option value="medium">Medium</option>
            <option value="complex">Complex</option>
          </select>
        </div>
        <div class="date-controls">
          <input
            v-model="dueDateStart"
            type="date"
            class="input date-input"
          />
          <span class="date-separator">—</span>
          <input
            v-model="dueDateEnd"
            type="date"
            class="input date-input"
          />
          <div class="quick-filters">
            <button
              @click="clearDateFilters()"
              :class="{ active: !dueDateStart && !dueDateEnd }"
              class="btn btn-quick"
            >
              All
            </button>
            <button
              @click="setTodayFilter()"
              :class="{ active: dueDateStart === getTodayDate() && dueDateEnd === getTodayDate() }"
              class="btn btn-quick"
            >
              Today
            </button>
            <button
              @click="setWeekFilter()"
              :class="{ active: dueDateStart === getWeekStartDate() && dueDateEnd === getWeekEndDate() }"
              class="btn btn-quick"
            >
              This Week
            </button>
          </div>
        </div>
      </div>

      <!-- 表格视图 -->
      <div v-if="loading && todos.length === 0" class="loading">
        ⏳ Loading todos...
      </div>

      <!-- 生成测试数据按钮 -->
      <div class="empty-generate-section">
        <button
          @click="handleGenerateTestData"
          :disabled="generatingTestData"
          class="btn btn-secondary"
        >
          {{ generatingTestData ? '⏳ Generating...' : '🤖 Generate 50 Test Todos' }}
        </button>
      </div>

      <!-- 空状态卡片 -->
      <div v-if="!loading && todos.length === 0" class="empty-state">
        <p>No todos yet. Create one to get started! 🚀</p>
        <div class="empty-state-actions">
          <button
            @click="goToNewTodo"
            class="btn btn-primary btn-lg"
          >
            ➕ Create Your First Todo
          </button>
        </div>
      </div>

      <div v-else class="table-section">
        <table class="todos-table">
          <thead>
            <tr>
              <th style="width: 40px;"></th>
              <th style="width: 20%;">Title</th>
              <th style="width: 12%;">Project</th>
              <th style="width: 10%;">Category</th>
              <th style="width: 10%;">Complexity</th>
              <th style="width: 8%;">Priority</th>
              <th style="width: 8%;">Status</th>
              <th style="width: 8%;">Est. Hours</th>
              <th style="width: 10%;">Due Date</th>
              <th style="width: 60px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="todo in todos"
              :key="todo.id"
              class="todo-row"
              :class="todo.status"
            >
              <td class="checkbox-col">
                <input
                  type="checkbox"
                  :checked="todo.status === 'completed'"
                  @change="(e) => handleToggleTodo(todo.id, e.target.checked)"
                  class="row-checkbox"
                />
              </td>
              <td class="title-col">
                <span class="title-text" :class="{ completed: todo.status === 'completed' }">
                  {{ todo.title }}
                </span>
                <div v-if="todo.tags && todo.tags.length > 0" class="inline-tags">
                  <span v-for="tag in todo.tags" :key="tag" class="inline-tag">{{ tag }}</span>
                </div>
              </td>
              <td class="project-col">
                <span class="project-tag" v-if="todo.projectId">{{ getProjectName(todo.projectId) }}</span>
                <span v-else class="no-value">—</span>
              </td>
              <td class="category-col">
                <span class="category-tag" :class="todo.category" v-if="todo.category">{{ todo.category }}</span>
                <span v-else class="no-value">—</span>
              </td>
              <td class="complexity-col">
                <span class="complexity-badge" :class="todo.complexity" v-if="todo.complexity">{{ todo.complexity }}</span>
                <span v-else class="no-value">—</span>
              </td>
              <td class="priority-col">
                <span class="priority-badge" :class="todo.priority">
                  {{ todo.priority }}
                </span>
              </td>
              <td class="status-col">
                <select
                  :value="todo.status"
                  @change="(e) => handleStatusChange(todo.id, e.target.value)"
                  class="status-select"
                  :class="todo.status"
                >
                  <option value="pending">Pending</option>
                  <option value="in-progress">In Progress</option>
                  <option value="completed">Completed</option>
                </select>
              </td>
              <td class="hours-col">
                <span v-if="todo.estimatedHours" class="hours-text">{{ todo.estimatedHours }}h</span>
                <span v-else class="no-value">—</span>
              </td>
              <td class="date-col">
                <span v-if="todo.dueDate" class="date-text" :class="{ overdue: isOverdue(todo.dueDate) }">
                  {{ formatDate(todo.dueDate) }}
                </span>
                <span v-else class="no-date">—</span>
              </td>
              <td class="actions-col">
                <button
                  @click="goToEditTodo(todo)"
                  class="btn btn-icon btn-edit"
                  title="Edit"
                >
                  ✏️
                </button>
                <button
                  @click="handleDeleteTodo(todo.id)"
                  class="btn btn-icon btn-delete"
                  title="Delete"
                >
                  🗑️
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 加载更多按钮 -->
        <div class="load-more-section">
          <button
            @click="autoLoadMore"
            :disabled="!todoStore.hasMore || loading"
            class="btn btn-primary btn-load-more"
          >
            {{ loading ? '⏳ Loading...' : '📥 Load More' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTodoStore } from '@/stores/todoStore'
import { useAuthStore } from '@/stores/authStore'
import { getProjects } from '@/api/projects'
import AIAssistant from '@/components/AIAssistant.vue'
import type { Todo, Project } from '@/types'

const router = useRouter()
const todoStore = useTodoStore()
const authStore = useAuthStore()
const loading = computed(() => todoStore.loading)
const error = computed(() => todoStore.error)
const todos = computed(() => todoStore.todos)

const goToNewTodo = () => router.push('/todos/new')
const goToEditTodo = (todo: Todo) => router.push(`/todos/${todo.id}/edit`)

// Projects list
const projects = ref<Project[]>([])

// Categories list - used by the filter dropdown
const categories = ref<string[]>(['feature', 'bug', 'refactor', 'documentation'])

// 搜索和过滤
const searchQuery = ref('')
const statusFilter = ref('')
const priorityFilter = ref('')
const projectFilter = ref('')
const categoryFilter = ref('')
const complexityFilter = ref('')
const dueDateStart = ref('')
const dueDateEnd = ref('')

// 根据活动计算各个日期辅助函数
const getTodayDate = (): string => {
  const today = new Date()
  return today.toISOString().split('T')[0]
}

const getWeekStartDate = (): string => {
  const now = new Date()
  const dayOfWeek = now.getDay()
  const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
  const monday = new Date(now)
  monday.setDate(now.getDate() - daysToMonday)
  return monday.toISOString().split('T')[0]
}

const getWeekEndDate = (): string => {
  const monday = new Date(getWeekStartDate())
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return sunday.toISOString().split('T')[0]
}

const setTodayFilter = () => {
  const today = getTodayDate()
  dueDateStart.value = ''  // No start limit - include all overdue items
  dueDateEnd.value = today  // End at today - includes today's due items
}

const setWeekFilter = () => {
  dueDateStart.value = getWeekStartDate()
  dueDateEnd.value = getWeekEndDate()
}

const clearDateFilters = () => {
  dueDateStart.value = ''
  dueDateEnd.value = ''
}

// 检查是否有活跃的过滤器
const hasActiveFilters = computed(() => {
  return !!searchQuery.value || !!statusFilter.value || !!priorityFilter.value || !!projectFilter.value || !!categoryFilter.value || !!complexityFilter.value || !!dueDateStart.value || !!dueDateEnd.value
})

// 当Filter条件改变时，从后台重新加载过滤数据
let isAutoLoading = false

const autoLoadMore = async () => {
  if (isAutoLoading) return
  isAutoLoading = true
  try {
    const filters = {
      search: searchQuery.value || undefined,
      status: statusFilter.value || undefined,
      priority: priorityFilter.value || undefined,
      projectId: projectFilter.value || undefined,
      category: categoryFilter.value || undefined,
      complexity: complexityFilter.value || undefined,
      dueDateStart: dueDateStart.value || undefined,
      dueDateEnd: dueDateEnd.value || undefined,
    }
    await todoStore.loadMoreWithFilters(filters)
  } finally {
    isAutoLoading = false
  }
}
// 监听filter条件变化（当搜索或过滤条件改变时自动加载）
const applyFilters = async () => {
  const filters = {
    search: searchQuery.value || undefined,
    status: statusFilter.value || undefined,
    priority: priorityFilter.value || undefined,
    projectId: projectFilter.value || undefined,
    category: categoryFilter.value || undefined,
    complexity: complexityFilter.value || undefined,
    dueDateStart: dueDateStart.value || undefined,
    dueDateEnd: dueDateEnd.value || undefined,
  }
  await todoStore.fetchTodos(filters)
}

// 分别监听每个过滤条件的变化
watch(() => searchQuery.value, applyFilters)
watch(() => statusFilter.value, applyFilters)
watch(() => priorityFilter.value, applyFilters)
watch(() => projectFilter.value, applyFilters)
watch(() => categoryFilter.value, applyFilters)
watch(() => complexityFilter.value, applyFilters)
watch(() => dueDateStart.value, applyFilters)
watch(() => dueDateEnd.value, applyFilters)

// 处理登录
const handleLogin = async () => {
  const success = await authStore.login()
  if (success && authStore.isAuthenticated) {
    setTimeout(() => {
      applyFilters()
    }, 500)
  }
}

// 格式化日期
const formatDate = (dateString: string | Date) => {
  if (!dateString) return ''
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

// 检查是否逾期
const isOverdue = (dueDate: string | Date) => {
  if (!dueDate) return false
  const date = typeof dueDate === 'string' ? new Date(dueDate) : dueDate
  return date < new Date() && date.toDateString() !== new Date().toDateString()
}

// 截断文本
const truncate = (text: string | undefined, length: number) => {
  if (!text) return '—'
  return text.length > length ? text.substring(0, length) + '...' : text
}

// 切换 Todo 状态
const handleToggleTodo = async (id: string, completed: boolean) => {
  try {
    await todoStore.updateTodo(id, {
      status: completed ? 'completed' : 'pending',
    } as any)
  } catch (err) {
    console.error('Failed to update todo:', err)
  }
}

// 更改状态
const handleStatusChange = async (id: string, newStatus: string) => {
  try {
    await todoStore.updateTodo(id, {
      status: newStatus as 'pending' | 'in-progress' | 'completed',
    } as any)
  } catch (err) {
    console.error('Failed to update todo status:', err)
  }
}

// 删除 Todo
const handleDeleteTodo = async (id: string) => {
  if (confirm('Are you sure you want to delete this todo?')) {
    try {
      await todoStore.deleteTodo(id)
    } catch (err) {
      console.error('Failed to delete todo:', err)
    }
  }
}

// 生成测试数据
const generatingTestData = ref(false)
const handleGenerateTestData = async () => {
  if (!authStore.userId) {
    alert('Please login first')
    return
  }

  const count = 50
  const message = 'Generate 50 test todos (with auto-created project) for current user?'
  
  if (!confirm(message)) {
    return
  }

  generatingTestData.value = true
  try {
    const response = await fetch(
      `/api/generate-todos?userId=${authStore.userId}&count=${count}`,
      { method: 'POST' }
    )
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    const data = await response.json()
    const projectInfo = data.projectCreated ? `\nProject: "${data.projectName}" (auto-created)` : ''
    alert(`✅ Generated ${data.createdCount} todos (${data.seededHighImpact} high-impact)!\nTime: ${data.timeSeconds}s${projectInfo}`)
    
    // 重新加载数据
    await todoStore.fetchTodos()
  } catch (err: any) {
    console.error('Failed to generate test data:', err)
    alert(`❌ Failed to generate test data: ${err.message}`)
  } finally {
    generatingTestData.value = false
  }
}

// 页面挂载
onMounted(async () => {
  if (authStore.isAuthenticated && authStore.userId) {
    // Load projects first
    try {
      projects.value = await getProjects(authStore.userId)
    } catch (err) {
      console.error('Failed to load projects:', err)
    }
    
    // Then load todos
    applyFilters()
  }
})

// Helper function to get project name by ID
const getProjectName = (projectId?: string): string => {
  if (!projectId) return '—'
  const project = projects.value.find(p => p.id === projectId)
  return project?.name || '—'
}

</script>

<style scoped>
.todos-page {
  max-width: 1400px;
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

/* Header Section */
.header-section {
  margin-bottom: 1.5rem;
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-section h1 {
  font-size: 2rem;
  margin: 0;
  color: #2c3e50;
  flex: 1;
  min-width: 200px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.5rem;
  flex-wrap: wrap;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.5rem;
  background: white;
  border-radius: 10px;
  border-left: 4px solid #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stat .label {
  font-weight: 500;
  color: #666;
  font-size: 0.9rem;
}

.stat .value {
  font-size: 2rem;
  font-weight: bold;
  color: #667eea;
}

/* Create Section */
.create-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-start;
}

.btn-toggle {
  padding: 0.6rem 1rem;
  font-size: 0.9rem;
  background: #f0f0f0;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.btn-toggle.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  font-family: inherit;
  transition: all 0.2s;
}

.input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-input {
  flex: 1;
}

.filter-select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.textarea {
  resize: vertical;
  min-height: 80px;
}

.select {
  cursor: pointer;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
  border: 1px solid #ddd;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.btn-icon {
  padding: 0.5rem;
  font-size: 1.1rem;
  background: transparent;
  border: none;
}

.btn-edit {
  color: #667eea;
}

.btn-edit:hover {
  background: #f0f0ff;
}

.btn-delete {
  color: #ff6b6b;
}

.btn-delete:hover {
  background: #fff0f0;
}

.btn-pagination {
  padding: 0.6rem 1.2rem;
  background: #f0f0f0;
  color: #333;
  border: 1px solid #ddd;
}

.btn-pagination:hover:not(:disabled) {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.error-box {
  padding: 1rem;
  background: #ffe5e5;
  border: 1px solid #ff6b6b;
  border-radius: 6px;
  color: #d32f2f;
  margin-bottom: 1rem;
}

.loading {
  text-align: center;
  padding: 3rem 2rem;
  color: #666;
  font-size: 1.1rem;
  background: white;
  border-radius: 12px;
}

.empty-generate-section {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.empty-generate-section .btn {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: #999;
  font-size: 1.1rem;
  background: white;
  border-radius: 12px;
}

.empty-state-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1.5rem;
  flex-wrap: wrap;
}

.empty-state-actions .btn-lg {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  white-space: nowrap;
}

/* Search Section */
.search-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.search-controls {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

@media (min-width: 512px) {
  .search-controls {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .search-controls {
    grid-template-columns: 2fr 1fr 1fr;
  }
}

.filter-controls-secondary {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e9ecef;
}

@media (min-width: 512px) {
  .filter-controls-secondary {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .filter-controls-secondary {
    grid-template-columns: repeat(3, 1fr);
  }
}

.date-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding-bottom: 0.75rem;
}

.date-input {
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  min-width: 120px;
}

.date-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.date-separator {
  color: #999;
  font-weight: bold;
  padding: 0 0.25rem;
  white-space: nowrap;
}

.quick-filters {
  display: flex;
  gap: 0.5rem;
  margin-left: 0;
  flex-wrap: wrap;
}

@media (min-width: 768px) {
  .quick-filters {
    margin-left: auto;
  }
}

.btn-quick {
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-quick:hover {
  border-color: #667eea;
  color: #667eea;
}

.btn-quick.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

/* Table Section */
.table-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  overflow-x: auto;
}

.todos-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 0;
  table-layout: auto;
  min-width: 100%;
}

.todos-table thead {
  background: #f8f9fa;
  border-bottom: 2px solid #e9ecef;
  position: sticky;
  top: 0;
}

.todos-table th {
  padding: 0.6rem;
  text-align: left;
  font-weight: 600;
  color: #495057;
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.todos-table tbody tr {
  border-bottom: 1px solid #e9ecef;
  transition: background-color 0.2s;
}

.todos-table tbody tr:hover {
  background-color: #f8f9fa;
}

.todos-table td {
  padding: 0.6rem;
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

.checkbox-col {
  text-align: center;
  width: 5%;
  min-width: 40px;
}

.row-checkbox {
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.title-col {
  font-weight: 500;
  color: #2c3e50;
  width: 18%;
  min-width: 150px;
}

.project-col {
  width: 12%;
  min-width: 100px;
}

.category-col {
  width: 10%;
  min-width: 80px;
}

.complexity-col {
  width: 10%;
  min-width: 80px;
}

.priority-col {
  width: 10%;
  min-width: 80px;
}

.status-col {
  width: 11%;
  min-width: 95px;
}

.hours-col {
  width: 8%;
  min-width: 70px;
  text-align: center;
}

.date-col {
  width: 10%;
  min-width: 90px;
}

.actions-col {
  width: 6%;
  min-width: 70px;
  text-align: center;
}

.title-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.title-text.completed {
  text-decoration: line-through;
  color: #999;
}

.inline-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.4rem;
}

.inline-tag {
  display: inline-block;
  background: #f0f0ff;
  color: #667eea;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.description-col {
  color: #666;
  font-size: 0.9rem;
}

.description-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 250px;
}

.priority-col {
  text-align: center;
}

.priority-badge {
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  display: inline-block;
  text-align: center;
  white-space: nowrap;
}

.priority-badge.low {
  background: #d4edda;
  color: #155724;
}

.priority-badge.medium {
  background: #fff3cd;
  color: #856404;
}

.priority-badge.high {
  background: #f8d7da;
  color: #721c24;
}

/* Project, Category, Complexity Styles */
.project-col {
  text-align: center;
}

.project-tag {
  display: inline-block;
  background: #e3f2fd;
  color: #1565c0;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}

.category-col {
  text-align: center;
}

.category-tag {
  display: inline-block;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}

.category-tag.feature {
  background: #c8e6c9;
  color: #2e7d32;
}

.category-tag.bug {
  background: #ffccbc;
  color: #d84315;
}

.category-tag.refactor {
  background: #ffe0b2;
  color: #e65100;
}

.category-tag.documentation {
  background: #f3e5f5;
  color: #6a1b9a;
}

.complexity-col {
  text-align: center;
}

.complexity-badge {
  display: inline-block;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
  white-space: nowrap;
}

.complexity-badge.simple {
  background: #4caf50;
}

.complexity-badge.medium {
  background: #ff9800;
}

.complexity-badge.complex {
  background: #f44336;
}

.hours-col {
  text-align: center;
}

.hours-text {
  display: inline-block;
  background: #f3e5f5;
  color: #6a1b9a;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.75rem;
}

.no-value {
  color: #999;
  font-style: italic;
}

.actions-col {
  text-align: center;
  display: flex;
  justify-content: center;
  gap: 0.5rem;
}

.btn-icon {
  padding: 0.4rem;
  font-size: 0.9rem;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-edit {
  color: #667eea;
}

.btn-edit:hover {
  background: #f0f0ff;
  border-radius: 4px;
}

.btn-delete {
  color: #ff6b6b;
}

.btn-delete:hover {
  background: #fff0f0;
  border-radius: 4px;
}

/* Load More */
.load-more-section {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
  flex-wrap: wrap;
}

.btn-load-more {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  flex: 0 1 auto;
  min-width: 200px;
}

.generate-section {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1.5rem;
  background: #f8f9fa;
}

.btn-generate-test-data {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  min-width: 200px;
}

.btn-load-more:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-generate-test-data {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  min-width: 280px;
  background: linear-gradient(135deg, #48dbfb 0%, #0abde3 100%);
  color: white;
}

.btn-generate-test-data:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(10, 189, 227, 0.4);
}

.btn-generate-test-data:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.3rem;
  color: #2c3e50;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.btn-close:hover {
  color: #2c3e50;
}

.edit-form {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

/* Responsive */
@media (max-width: 1024px) {
  .search-controls {
    grid-template-columns: 1fr 1fr 1fr;
  }

  .form-row {
    grid-template-columns: 1fr 1fr;
  }

  .todos-table th,
  .todos-table td {
    padding: 0.75rem;
    font-size: 0.85rem;
  }
}

@media (max-width: 768px) {
  .todos-page {
    padding: 1rem;
  }

  .header-top {
    flex-direction: column;
  }

  .header-section h1 {
    font-size: 1.5rem;
  }

  .search-controls {
    grid-template-columns: 1fr;
  }

  .date-controls {
    flex-direction: column;
  }

  .quick-filters {
    margin-left: 0;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .load-more-section {
    padding: 1rem;
    flex-direction: column;
  }

  .btn-load-more {
    width: 100%;
  }

  .modal-content {
    width: 95%;
  }

  /* 表格在小屏幕上的调整 */
  .todos-table {
    font-size: 0.85rem;
  }

  .todos-table th,
  .todos-table td {
    padding: 0.5rem;
  }

  /* 隐藏较不重要的列 */
  .todos-table thead tr > th:nth-child(3),
  .todos-table tbody tr > td:nth-child(3) {
    display: none;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .create-section,
  .search-section {
    padding: 1rem;
  }

  .modal-content {
    width: 100%;
    border-radius: 12px 12px 0 0;
    max-height: 100vh;
  }

  .stats {
    grid-template-columns: 1fr;
  }
}

/* ── Estimate hours: input + button + modal ── */
.estimate-input-wrapper {
  display: flex;
  gap: 6px;
  align-items: stretch;
}
.estimate-input-wrapper .input {
  flex: 1;
}
.btn-estimate {
  white-space: nowrap;
  padding: 0 12px;
  border: 1px solid #c7daf3;
  background: linear-gradient(135deg, #f0f6ff 0%, #e8f1ff 100%);
  color: #0f3d91;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
}
.btn-estimate:hover:not(:disabled) {
  background: linear-gradient(135deg, #e2ecff 0%, #d6e6ff 100%);
}
.btn-estimate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f1f3f7;
  color: #8a99b3;
  border-color: #dde3ec;
}

.estimate-modal {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 540px;
  width: 92%;
  max-height: 86vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
}
.estimate-modal h3 {
  margin: 0 0 1rem;
  color: #173a67;
}

.estimate-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
  color: #5d7394;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e0e8f5;
  border-top-color: #0078d4;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.estimate-headline {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 8px;
}
.estimate-value {
  font-size: 2rem;
  font-weight: 700;
  color: #0f3d91;
}
.estimate-range {
  color: #6884a5;
  font-size: 0.9rem;
}
.estimate-reason {
  color: #1f3757;
  background: #f4f8ff;
  border-left: 3px solid #0078d4;
  padding: 8px 12px;
  border-radius: 6px;
  margin: 8px 0 16px;
  font-size: 0.9rem;
}

.estimate-samples .samples-label {
  font-weight: 600;
  color: #557197;
  font-size: 0.85rem;
  margin: 8px 0 4px;
}
.estimate-samples ul {
  list-style: none;
  padding: 0;
  margin: 0 0 16px;
}
.estimate-samples li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border: 1px solid #e6eef8;
  border-radius: 6px;
  margin-bottom: 4px;
  font-size: 0.85rem;
}
.sample-title {
  flex: 1;
  color: #1f3757;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sample-hours {
  color: #0f3d91;
  font-weight: 600;
}
.sample-sim {
  color: #8ca5c0;
  font-size: 0.75rem;
}

.estimate-empty {
  color: #6884a5;
  padding: 8px 0;
}
</style>
