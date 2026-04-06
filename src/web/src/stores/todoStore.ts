import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Todo } from '@/types'
import * as todoAPI from '@/api/todos'
import { useAuthStore } from './authStore'

export const useTodoStore = defineStore('todos', () => {
  // 累积加载的数据
  const todos = ref<Todo[]>([])
  const continuationToken = ref<string | undefined>(undefined)
  const currentOffset = ref(0)
  const totalCount = ref(0)
  const pageSize = ref(10)
  
  const loading = ref(false)
  const error = ref<string | null>(null)
  const authStore = useAuthStore()
  
  // Use authenticated user's ID from Azure AD account
  const userId = computed(() => authStore.account?.localAccountId || '')

  // Calculate stats from loaded todos
  const completedCount = computed(() => todos.value.filter(t => t.status === 'completed').length)
  const pendingCount = computed(() => todos.value.filter(t => t.status === 'pending').length)
  const inProgressCount = computed(() => todos.value.filter(t => t.status === 'in-progress').length)
  
  // Check if there are more items to load
  const hasMore = computed(() => currentOffset.value + pageSize.value < totalCount.value)

  const fetchTodos = async (filters?: { search?: string; status?: string; priority?: string; dueDateStart?: string; dueDateEnd?: string }) => {
    loading.value = true
    error.value = null
    todos.value = []
    currentOffset.value = 0
    totalCount.value = 0
    try {
      const result = await todoAPI.getTodos(userId.value, pageSize.value, 0, filters)
      todos.value = result.items
      currentOffset.value = 0
      totalCount.value = result.total
    } catch (err: any) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  // 加载更多
  const loadMore = async (filters?: { search?: string; status?: string; priority?: string; dueDateStart?: string; dueDateEnd?: string }) => {
    if (!hasMore.value || loading.value) return
    
    loading.value = true
    error.value = null
    try {
      const nextOffset = currentOffset.value + pageSize.value
      const result = await todoAPI.getTodos(
        userId.value,
        pageSize.value,
        nextOffset,
        filters
      )
      // 累积追加数据
      todos.value = [...todos.value, ...result.items]
      currentOffset.value = nextOffset
      totalCount.value = result.total
    } catch (err: any) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  // 带过滤和自动加载的加载
  const loadMoreWithFilters = async (filters?: { search?: string; status?: string; priority?: string; dueDateStart?: string; dueDateEnd?: string }) => {
    if (loading.value) return
    
    loading.value = true
    error.value = null
    try {
      const nextOffset = currentOffset.value + pageSize.value
      const result = await todoAPI.getTodos(
        userId.value,
        pageSize.value,
        nextOffset,
        filters,
        currentOffset.value === 0 // Only use autoLoad when starting fresh
      )
      // 累积追加数据
      todos.value = [...todos.value, ...result.items]
      currentOffset.value = nextOffset
      totalCount.value = result.total
    } catch (err: any) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  const createTodo = async (todo: Omit<Todo, 'id' | 'createdAt' | 'updatedAt'>) => {
    loading.value = true
    error.value = null
    try {
      const newTodo = await todoAPI.createTodo({
        ...todo,
        userId: userId.value,
      })
      // 新创建的 todo 总是在最前面，重新加载
      await fetchTodos()
      return newTodo
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateTodo = async (id: string, updates: Partial<Todo>) => {
    loading.value = true
    error.value = null
    try {
      const updated = await todoAPI.updateTodo(id, {
        ...updates,
        userId: userId.value,
      })
      const index = todos.value.findIndex(t => t.id === id)
      if (index !== -1) {
        todos.value[index] = updated
      }
      return updated
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteTodo = async (id: string) => {
    loading.value = true
    error.value = null
    try {
      await todoAPI.deleteTodo(id)
      todos.value = todos.value.filter(t => t.id !== id)
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const setUserId = (id: string) => {
    todos.value = []
    currentOffset.value = 0
    totalCount.value = 0
  }

  const resetTodos = () => {
    todos.value = []
    currentOffset.value = 0
    totalCount.value = 0
  }

  return {
    todos,
    loading,
    error,
    userId,
    hasMore,
    pageSize,
    currentOffset,
    totalCount,
    completedCount,
    pendingCount,
    inProgressCount,
    fetchTodos,
    loadMore,
    loadMoreWithFilters,
    createTodo,
    updateTodo,
    deleteTodo,
    setUserId,
    resetTodos,
  }
})
