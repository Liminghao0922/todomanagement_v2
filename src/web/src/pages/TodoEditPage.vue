<template>
  <div class="todo-edit-page">
    <!-- 未登录提示 -->
    <div v-if="!authStore.isAuthenticated" class="login-prompt">
      <div class="prompt-content">
        <h2>🔐 Please login to continue</h2>
        <button @click="handleLogin" class="btn btn-primary btn-lg">
          {{ authStore.isLoading ? '⏳ Logging in...' : '🔐 Login with Microsoft' }}
        </button>
        <p v-if="authStore.error" class="error-text">{{ authStore.error }}</p>
      </div>
    </div>

    <template v-else>
      <div class="page-header">
        <button @click="goBack" class="btn btn-secondary">← Back</button>
        <h1>{{ isEditMode ? '✏️ Edit Todo' : '➕ New Todo' }}</h1>
        <div style="width: 80px"></div>
      </div>

      <div v-if="loadingTodo" class="loading">⏳ Loading todo…</div>
      <div v-else-if="loadError" class="error-box">⚠️ {{ loadError }}</div>

      <form v-else @submit.prevent="handleSubmit" class="create-section">
        <div class="create-form">
          <input
            v-model="form.title"
            type="text"
            placeholder="Todo Title (required)"
            required
            class="input"
          />
          <textarea
            v-model="form.description"
            placeholder="Description (optional)"
            class="input textarea"
            rows="3"
          ></textarea>

          <div class="form-row">
            <select v-model="form.status" class="input select">
              <option value="pending">Pending</option>
              <option value="in-progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>
            <select v-model="form.priority" class="input select">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <input
              v-model="form.dueDate"
              type="date"
              class="input"
              placeholder="Due Date"
            />
          </div>

          <div class="form-row">
            <input
              v-model="form.plannedStartDate"
              type="date"
              class="input"
              placeholder="Planned Start Date"
            />
            <input
              v-model="form.plannedEndDate"
              type="date"
              class="input"
              placeholder="Planned End Date"
            />
            <div class="schedule-hint">Timeline graph uses Planned Start/End dates.</div>
          </div>

          <div class="form-row">
            <select v-model="form.complexity" class="input select">
              <option value="">Complexity</option>
              <option value="simple">Simple</option>
              <option value="medium">Medium</option>
              <option value="complex">Complex</option>
            </select>
            <select v-model="form.projectId" class="input select">
              <option value="">Select Project</option>
              <option v-for="proj in projects" :key="proj.id" :value="proj.id">
                {{ proj.name }}
              </option>
            </select>
            <input
              v-model="form.category"
              type="text"
              placeholder="Category"
              list="categories-list"
              class="input"
            />
            <datalist id="categories-list">
              <option v-for="cat in categories" :key="cat" :value="cat" />
            </datalist>
          </div>

          <div class="form-row">
            <div class="estimate-input-wrapper">
              <input
                v-model="form.estimatedHours"
                type="number"
                step="0.1"
                min="0"
                placeholder="Estimated Hours"
                class="input"
              />
              <button
                type="button"
                class="btn-estimate"
                :disabled="!canEstimate"
                :title="canEstimate ? 'Estimate from past similar todos' : 'Enter a title first to estimate hours'"
                @click="openEstimateDialog"
              >
                ✨ Estimate
              </button>
            </div>
            <input
              v-model="form.actualHours"
              type="number"
              step="0.1"
              min="0"
              placeholder="Actual Hours"
              class="input"
            />
            <input
              v-model="form.tags"
              type="text"
              placeholder="Tags (comma-separated)"
              class="input"
            />
          </div>

          <!-- Task Relationships -->
          <div class="relationships-section">
            <label>📊 Task Relationships (Optional)</label>

            <div v-if="form.blockedBy.length || form.precedes.length || form.subtaskOf.length" class="selected-relations">
              <div class="selected-relations-title">✅ Selected Relationships</div>

              <div v-if="form.blockedBy.length" class="selected-rel-group">
                <span class="selected-rel-label">🔴 Blocked By</span>
                <div class="selected-rel-chips">
                  <span v-for="relatedId in form.blockedBy" :key="`blocked-${relatedId}`" class="selected-rel-chip">
                    <span class="selected-rel-text">{{ getRelatedTodoTitle(relatedId) }}</span>
                    <button
                      type="button"
                      class="selected-rel-remove"
                      @click="removeRelation(form.blockedBy, relatedId)"
                      title="Remove relation"
                    >✕</button>
                  </span>
                </div>
              </div>

              <div v-if="form.precedes.length" class="selected-rel-group">
                <span class="selected-rel-label">⏭️ Precedes</span>
                <div class="selected-rel-chips">
                  <span v-for="relatedId in form.precedes" :key="`precedes-${relatedId}`" class="selected-rel-chip">
                    <span class="selected-rel-text">{{ getRelatedTodoTitle(relatedId) }}</span>
                    <button
                      type="button"
                      class="selected-rel-remove"
                      @click="removeRelation(form.precedes, relatedId)"
                      title="Remove relation"
                    >✕</button>
                  </span>
                </div>
              </div>

              <div v-if="form.subtaskOf.length" class="selected-rel-group">
                <span class="selected-rel-label">📌 Subtask Of</span>
                <div class="selected-rel-chips">
                  <span v-for="relatedId in form.subtaskOf" :key="`subtask-${relatedId}`" class="selected-rel-chip">
                    <span class="selected-rel-text">{{ getRelatedTodoTitle(relatedId) }}</span>
                    <button
                      type="button"
                      class="selected-rel-remove"
                      @click="removeRelation(form.subtaskOf, relatedId)"
                      title="Remove relation"
                    >✕</button>
                  </span>
                </div>
              </div>
            </div>

            <div class="relationships-container">
              <div class="relationship-group">
                <h4>🔴 Blocked By</h4>
                <input
                  v-model="relationSearch.blockedBy"
                  type="text"
                  placeholder="🔍 Search tasks..."
                  class="input search-relation"
                />
                <div class="todo-checklist">
                  <label v-for="todo in relationOptions(relationSearch.blockedBy, form.blockedBy)" :key="todo.id" v-show="todo.id !== editingTodoId" class="checklist-item">
                    <input
                      type="checkbox"
                      :checked="form.blockedBy.includes(todo.id)"
                      @change="(e) => toggleRelation(form.blockedBy, todo.id, (e.target as HTMLInputElement).checked)"
                    />
                    <span class="checklist-label">{{ todo.title }}</span>
                  </label>
                </div>
              </div>

              <div class="relationship-group">
                <h4>⏭️ Precedes</h4>
                <input
                  v-model="relationSearch.precedes"
                  type="text"
                  placeholder="🔍 Search tasks..."
                  class="input search-relation"
                />
                <div class="todo-checklist">
                  <label v-for="todo in relationOptions(relationSearch.precedes, form.precedes)" :key="todo.id" v-show="todo.id !== editingTodoId" class="checklist-item">
                    <input
                      type="checkbox"
                      :checked="form.precedes.includes(todo.id)"
                      @change="(e) => toggleRelation(form.precedes, todo.id, (e.target as HTMLInputElement).checked)"
                    />
                    <span class="checklist-label">{{ todo.title }}</span>
                  </label>
                </div>
              </div>

              <div class="relationship-group">
                <h4>📌 Subtask Of</h4>
                <input
                  v-model="relationSearch.subtaskOf"
                  type="text"
                  placeholder="🔍 Search tasks..."
                  class="input search-relation"
                />
                <div class="todo-checklist">
                  <label v-for="todo in relationOptions(relationSearch.subtaskOf, form.subtaskOf)" :key="todo.id" v-show="todo.id !== editingTodoId" class="checklist-item">
                    <input
                      type="radio"
                      name="subtask-parent"
                      :value="todo.id"
                      :checked="form.subtaskOf.length > 0 && form.subtaskOf[0] === todo.id"
                      @change="(e) => form.subtaskOf = (e.target as HTMLInputElement).checked ? [todo.id] : []"
                    />
                    <span class="checklist-label">{{ todo.title }}</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div v-if="submitError" class="error-box">⚠️ {{ submitError }}</div>

          <div class="form-actions">
            <button type="submit" :disabled="submitting" class="btn btn-primary">
              {{ submitting ? (isEditMode ? 'Saving…' : 'Creating…') : (isEditMode ? 'Save Changes' : 'Create Todo') }}
            </button>
            <button type="button" @click="goBack" class="btn btn-secondary">Cancel</button>
          </div>
        </div>
      </form>
    </template>

    <!-- Estimate Hours Dialog -->
    <div v-if="showEstimateDialog" class="modal-overlay" @click.self="closeEstimateDialog">
      <div class="modal estimate-modal">
        <h3>✨ Estimate Hours from Past Data</h3>

        <div v-if="estimateLoading" class="estimate-loading">
          <div class="spinner" />
          <p>Searching past similar todos…</p>
        </div>

        <div v-else-if="estimateError" class="error-box">⚠️ {{ estimateError }}</div>

        <div v-else-if="estimateResult && estimateResult.found" class="estimate-result">
          <div class="estimate-headline">
            <span class="estimate-value">{{ estimateResult.estimatedHours }}h</span>
            <span class="estimate-range">range {{ estimateResult.minHours }}h – {{ estimateResult.maxHours }}h</span>
          </div>
          <p class="estimate-reason">{{ estimateResult.reasoning }}</p>
          <div v-if="estimateResult.similarTodos?.length" class="estimate-samples">
            <p class="samples-label">Based on:</p>
            <ul>
              <li v-for="s in estimateResult.similarTodos" :key="s.id">
                <span class="sample-title">{{ s.title }}</span>
                <span class="sample-hours">{{ s.actualHours }}h</span>
                <span class="sample-sim">sim {{ (s.similarity * 100).toFixed(0) }}%</span>
              </li>
            </ul>
          </div>
          <div class="modal-actions">
            <button class="btn btn-primary" @click="applyEstimate">Apply {{ estimateResult.estimatedHours }}h</button>
            <button class="btn btn-secondary" @click="closeEstimateDialog">Cancel</button>
          </div>
        </div>

        <div v-else-if="estimateResult && !estimateResult.found" class="estimate-empty">
          <p>{{ estimateResult.message || 'No similar past todos with recorded actual hours were found.' }}</p>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="closeEstimateDialog">Close</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { getProjects } from '@/api/projects'
import { getTodos, createTodo, updateTodo } from '@/api/todos'
import { estimateHours, type EstimateHoursResponse } from '@/api/ai'
import type { Todo, Project } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const editingTodoId = computed<string>(() => (route.params.id as string) || '')
const isEditMode = computed(() => !!editingTodoId.value)

const loadingTodo = ref(false)
const loadError = ref('')
const submitting = ref(false)
const submitError = ref('')

// Form state
const form = ref({
  title: '',
  description: '',
  priority: 'medium' as 'low' | 'medium' | 'high',
  status: 'pending' as 'pending' | 'in-progress' | 'completed',
  tags: '',
  plannedStartDate: '',
  plannedEndDate: '',
  dueDate: '',
  estimatedHours: '',
  complexity: '' as '' | 'simple' | 'medium' | 'complex',
  projectId: '',
  category: '',
  actualHours: '',
  blockedBy: [] as string[],
  precedes: [] as string[],
  subtaskOf: [] as string[],
})

const relationSearch = ref({ blockedBy: '', precedes: '', subtaskOf: '' })

const projects = ref<Project[]>([])
const categories = ref<string[]>(['feature', 'bug', 'refactor', 'documentation'])
const allTodos = ref<Todo[]>([])
const todoTitleCache = ref<Record<string, string>>({})

// Estimate dialog
const showEstimateDialog = ref(false)
const estimateLoading = ref(false)
const estimateError = ref('')
const estimateResult = ref<EstimateHoursResponse | null>(null)
const canEstimate = computed(() => form.value.title.trim().length > 0)

// Helpers
const formatDateForInput = (value: string | Date): string => {
  if (!value) return ''
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return ''
  return d.toISOString().split('T')[0]
}

const handleLogin = async () => {
  await authStore.login()
}

const goBack = () => {
  router.push('/')
}

// Relations
const toggleRelation = (relationArray: string[], todoId: string, checked: boolean) => {
  if (checked) {
    if (!relationArray.includes(todoId)) relationArray.push(todoId)
  } else {
    const i = relationArray.indexOf(todoId)
    if (i > -1) relationArray.splice(i, 1)
  }
}

const removeRelation = (relationArray: string[], todoId: string) => {
  const i = relationArray.indexOf(todoId)
  if (i > -1) relationArray.splice(i, 1)
}

const relationOptions = (searchText: string, selectedIds: string[]): Todo[] => {
  const map = new Map<string, Todo>()
  for (const t of allTodos.value) map.set(t.id, t)

  for (const id of selectedIds || []) {
    if (map.has(id)) continue
    const title = todoTitleCache.value[id] || `Unknown Task (${id.slice(0, 8)})`
    map.set(id, {
      id, userId: '', title, status: 'pending', priority: 'medium',
      tags: [], createdAt: '', updatedAt: '',
    } as Todo)
  }

  const all = Array.from(map.values())
  if (!searchText.trim()) return all
  const q = searchText.toLowerCase()
  return all.filter(t => (t.title || '').toLowerCase().includes(q))
}

const getRelatedTodoTitle = (todoId: string): string => {
  const todo = allTodos.value.find(t => t.id === todoId)
  if (todo?.title) return todo.title
  return todoTitleCache.value[todoId] || `Unknown Task (${todoId.slice(0, 8)})`
}

// Estimate
const openEstimateDialog = async () => {
  const title = form.value.title.trim()
  const description = form.value.description.trim()
  if (!title) {
    estimateError.value = 'Please enter a title first.'
    showEstimateDialog.value = true
    return
  }
  showEstimateDialog.value = true
  estimateLoading.value = true
  estimateError.value = ''
  estimateResult.value = null
  try {
    estimateResult.value = await estimateHours({
      title,
      description,
      category: form.value.category || undefined,
      complexity: form.value.complexity || undefined,
    })
  } catch (err: any) {
    estimateError.value = err?.message || 'Failed to estimate hours.'
  } finally {
    estimateLoading.value = false
  }
}

const applyEstimate = () => {
  if (estimateResult.value?.estimatedHours != null) {
    form.value.estimatedHours = String(estimateResult.value.estimatedHours)
  }
  closeEstimateDialog()
}

const closeEstimateDialog = () => {
  showEstimateDialog.value = false
  estimateError.value = ''
  estimateResult.value = null
}

// Load all todos for relation pickers
const loadAllTodos = async () => {
  if (!authStore.userId) return
  const pageSize = 200
  let offset = 0
  let total = 0
  const collected: Todo[] = []
  do {
    const result = await getTodos(authStore.userId, pageSize, offset)
    for (const item of result.items || []) {
      collected.push(item)
      todoTitleCache.value[item.id] = item.title
    }
    total = result.total || 0
    offset += pageSize
  } while (offset < total)
  allTodos.value = collected
}

const loadEditingTodo = async () => {
  const id = editingTodoId.value
  if (!id) return
  loadingTodo.value = true
  loadError.value = ''
  try {
    const todo = allTodos.value.find(t => t.id === id)
    if (!todo) {
      loadError.value = 'Todo not found.'
      return
    }
    form.value = {
      title: todo.title,
      description: todo.description || '',
      priority: todo.priority,
      status: todo.status,
      tags: (todo.tags || []).join(', '),
      plannedStartDate: formatDateForInput(todo.plannedStartDate as any),
      plannedEndDate: formatDateForInput(todo.plannedEndDate as any),
      dueDate: formatDateForInput(todo.dueDate as any),
      estimatedHours: todo.estimatedHours?.toString() || '',
      complexity: (todo.complexity || '') as any,
      projectId: todo.projectId || '',
      category: todo.category || '',
      actualHours: todo.actualHours?.toString() || '',
      blockedBy: [...((todo as any).blockedBy || [])],
      precedes: [...((todo as any).precedes || [])],
      subtaskOf: [...((todo as any).subtaskOf || [])],
    }
  } catch (err: any) {
    loadError.value = err?.message || 'Failed to load todo.'
  } finally {
    loadingTodo.value = false
  }
}

const handleSubmit = async () => {
  if (!form.value.title.trim() || !authStore.userId) return

  submitting.value = true
  submitError.value = ''

  // Add new category to local list
  if (form.value.category && !categories.value.includes(form.value.category.trim())) {
    categories.value.push(form.value.category.trim())
  }

  const payload: any = {
    title: form.value.title,
    description: form.value.description || undefined,
    priority: form.value.priority,
    status: form.value.status,
    plannedStartDate: form.value.plannedStartDate || undefined,
    plannedEndDate: form.value.plannedEndDate || undefined,
    dueDate: form.value.dueDate ? new Date(form.value.dueDate) : undefined,
    tags: form.value.tags.split(',').map(t => t.trim()).filter(Boolean),
    estimatedHours: form.value.estimatedHours ? parseFloat(form.value.estimatedHours) : undefined,
    complexity: form.value.complexity || undefined,
    projectId: form.value.projectId || undefined,
    category: form.value.category || undefined,
    actualHours: form.value.actualHours ? parseFloat(form.value.actualHours) : undefined,
    blockedBy: form.value.blockedBy,
    precedes: form.value.precedes,
    subtaskOf: form.value.subtaskOf,
  }

  try {
    if (isEditMode.value) {
      payload.userId = authStore.userId
      await updateTodo(editingTodoId.value, payload)
    } else {
      payload.userId = authStore.userId
      await createTodo(payload)
    }
    router.push('/')
  } catch (err: any) {
    submitError.value = err?.message || 'Failed to save todo.'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (!authStore.isAuthenticated || !authStore.userId) return
  try {
    projects.value = await getProjects(authStore.userId)
  } catch (err) {
    console.warn('Failed to load projects:', err)
  }
  await loadAllTodos()
  await loadEditingTodo()
})
</script>

<style scoped>
.todo-edit-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem;
  background: #fafbfc;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.page-header h1 {
  margin: 0;
  font-size: 1.7rem;
  color: #2c3e50;
  flex: 1;
  text-align: center;
}

.login-prompt {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.prompt-content {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  max-width: 400px;
}

.error-text { color: #ffcccc; font-size: 0.95rem; margin-top: 1rem; }

.create-section {
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.create-form { display: flex; flex-direction: column; gap: 0.85rem; }

.form-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }

.schedule-hint {
  display: flex; align-items: center; padding: 0 0.5rem;
  font-size: 0.82rem; color: #6b7280;
}

.form-actions { display: flex; gap: 0.75rem; justify-content: flex-start; margin-top: 0.5rem; }

.input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  font-family: inherit;
  transition: all 0.2s;
}

.input:focus {
  outline: none; border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.textarea { resize: vertical; min-height: 80px; }
.select { cursor: pointer; }

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn:disabled { opacity: 0.6; cursor: not-allowed; }

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

.btn-secondary:hover { background: #e0e0e0; }

.btn-lg { padding: 0.875rem 2rem; font-size: 1rem; }

.error-box {
  padding: 1rem;
  background: #ffe5e5;
  border: 1px solid #ff6b6b;
  border-radius: 6px;
  color: #d32f2f;
}

.loading {
  text-align: center;
  padding: 3rem 2rem;
  color: #666;
  font-size: 1.1rem;
  background: white;
  border-radius: 12px;
}

/* Relationships */
.relationships-section {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 1rem;
  background: #f8f9fa;
}

.relationships-section > label {
  display: block; font-size: 1rem; font-weight: 600; color: #333; margin-bottom: 0.5rem;
}

.relationships-container {
  display: grid; grid-template-columns: 1fr; gap: 1.5rem; margin-top: 1rem;
}

@media (min-width: 768px) {
  .relationships-container { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .relationships-container { grid-template-columns: repeat(3, 1fr); }
}

.selected-relations {
  margin-top: 1rem;
  padding: 0.75rem;
  border: 1px solid #d8e2f8;
  border-radius: 8px;
  background: #ffffff;
}

.selected-relations-title {
  font-size: 0.9rem; font-weight: 700; color: #2c3e50; margin-bottom: 0.75rem;
}

.selected-rel-group + .selected-rel-group { margin-top: 0.65rem; }

.selected-rel-label {
  display: inline-block; font-size: 0.82rem; font-weight: 600; color: #4a5568; margin-bottom: 0.35rem;
}

.selected-rel-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }

.selected-rel-chip {
  display: inline-flex; align-items: center; gap: 0.35rem;
  background: #eef3ff; border: 1px solid #d6e0ff; border-radius: 999px;
  padding: 0.2rem 0.45rem 0.2rem 0.6rem;
}

.selected-rel-text {
  font-size: 0.8rem; color: #2f3c54; max-width: 220px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.selected-rel-remove {
  border: none; background: transparent; color: #5f6b85;
  cursor: pointer; font-size: 0.78rem; line-height: 1; padding: 0.1rem;
}

.selected-rel-remove:hover { color: #d64545; }

.relationship-group { display: flex; flex-direction: column; gap: 0.5rem; }
.relationship-group h4 { margin: 0; font-size: 0.95rem; color: #2c3e50; font-weight: 600; }

.search-relation {
  width: 100%; padding: 0.5rem; margin-bottom: 0.5rem;
  border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;
}

.todo-checklist {
  display: flex; flex-direction: column; gap: 0.5rem;
  max-height: 220px; overflow-y: auto;
  padding: 0.5rem 0; border: 1px solid #ddd; border-radius: 4px; background: white;
}

.checklist-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.4rem 0.5rem; cursor: pointer; transition: background 0.2s;
}
.checklist-item:hover { background: #f0f0f0; }
.checklist-item input[type="checkbox"],
.checklist-item input[type="radio"] { cursor: pointer; width: 16px; height: 16px; }

.checklist-label {
  font-size: 0.85rem; color: #333; flex: 1;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* Estimate */
.estimate-input-wrapper { display: flex; gap: 6px; align-items: stretch; }
.estimate-input-wrapper .input { flex: 1; }
.btn-estimate {
  white-space: nowrap; padding: 0 12px;
  border: 1px solid #c7daf3;
  background: linear-gradient(135deg, #f0f6ff 0%, #e8f1ff 100%);
  color: #0f3d91; border-radius: 6px; cursor: pointer;
  font-size: 0.85rem; font-weight: 600;
}
.btn-estimate:hover:not(:disabled) {
  background: linear-gradient(135deg, #e2ecff 0%, #d6e6ff 100%);
}
.btn-estimate:disabled {
  opacity: 0.5; cursor: not-allowed;
  background: #f1f3f7; color: #8a99b3; border-color: #dde3ec;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex; justify-content: center; align-items: center;
  z-index: 1000;
}
.estimate-modal {
  background: white; border-radius: 12px; padding: 1.5rem;
  max-width: 540px; width: 92%; max-height: 86vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
}
.estimate-modal h3 { margin: 0 0 1rem; color: #173a67; }

.estimate-loading {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 24px 0; color: #5d7394;
}
.spinner {
  width: 32px; height: 32px;
  border: 3px solid #e0e8f5; border-top-color: #0078d4;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.estimate-headline {
  display: flex; align-items: baseline; gap: 12px; margin-bottom: 8px;
}
.estimate-value { font-size: 2rem; font-weight: 700; color: #0f3d91; }
.estimate-range { color: #6884a5; font-size: 0.9rem; }
.estimate-reason {
  color: #1f3757; background: #f4f8ff; border-left: 3px solid #0078d4;
  padding: 8px 12px; border-radius: 6px; margin: 8px 0 16px; font-size: 0.9rem;
}
.estimate-samples .samples-label {
  font-weight: 600; color: #557197; font-size: 0.85rem; margin: 8px 0 4px;
}
.estimate-samples ul { list-style: none; padding: 0; margin: 0 0 16px; }
.estimate-samples li {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 10px; border: 1px solid #e6eef8; border-radius: 6px;
  margin-bottom: 4px; font-size: 0.85rem;
}
.sample-title { flex: 1; color: #1f3757; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sample-hours { color: #0f3d91; font-weight: 600; }
.sample-sim { color: #8ca5c0; font-size: 0.75rem; }

.estimate-empty { color: #6884a5; padding: 8px 0; }

.modal-actions {
  display: flex; gap: 1rem; justify-content: flex-end;
  padding-top: 1rem; border-top: 1px solid #e9ecef; margin-top: 1rem;
}
</style>
