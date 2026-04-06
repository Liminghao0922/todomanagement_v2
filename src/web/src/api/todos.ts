import { apiClient } from './http'
import type { Todo } from '@/types'

export interface PaginatedResult {
  items: Todo[]
  total: number
  offset: number
  pageSize: number
  nextOffset?: number
}

export async function getTodos(
  userId: string,
  pageSize: number = 10,
  offset: number = 0,
  filters?: {
    search?: string
    status?: string
    priority?: string
    dueDateStart?: string
    dueDateEnd?: string
    projectId?: string
    category?: string
    complexity?: string
  },
  autoLoad?: boolean
): Promise<PaginatedResult> {
  const params: Record<string, any> = { userId, pageSize, offset }
  if (filters?.search) {
    params.search = filters.search
  }
  if (filters?.status) {
    params.status = filters.status
  }
  if (filters?.priority) {
    params.priority = filters.priority
  }
  if (filters?.dueDateStart) {
    params.dueDateStart = filters.dueDateStart
  }
  if (filters?.dueDateEnd) {
    params.dueDateEnd = filters.dueDateEnd
  }
  if (filters?.projectId) {
    params.projectId = filters.projectId
  }
  if (filters?.category) {
    params.category = filters.category
  }
  if (filters?.complexity) {
    params.complexity = filters.complexity
  }
  if (autoLoad) {
    params.autoLoad = 'true'
  }

  const response = await apiClient.get<PaginatedResult>('/todos', {
    params,
  })
  
  return response.data || { items: [], total: 0, offset: 0, pageSize: pageSize }
}

export async function createTodo(todo: Omit<Todo, 'id' | 'createdAt' | 'updatedAt'>): Promise<Todo> {
  const response = await apiClient.post<Todo>('/todos', todo)
  return response.data
}

export async function updateTodo(id: string, updates: Partial<Todo>): Promise<Todo> {
  const response = await apiClient.patch<Todo>(`/todos/${id}`, updates)
  return response.data
}

export async function deleteTodo(id: string): Promise<void> {
  await apiClient.delete(`/todos/${id}`)
}
