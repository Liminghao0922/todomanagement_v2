import { apiClient } from './http'
import { useAuthStore } from '@/stores/authStore'

export interface ChatResponse {
  answer?: string
  content?: string
  status?: string
  error?: string
  conversationId?: string
  conversationDocId?: string
}

export async function chatWithFoundry(
  message: string,
  userId?: string,
  conversationId?: string,
  conversationDocId?: string,
): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/chat', {
    message,
    userId,
    conversationId,
    conversationDocId,
  })
  return response.data
}

export interface EstimateHoursSimilar {
  id: string
  title: string
  category?: string
  complexity?: string
  estimatedHours?: number
  actualHours: number
  similarity: number
}

export interface EstimateHoursResponse {
  found: boolean
  estimatedHours?: number
  minHours?: number
  maxHours?: number
  sampleSize?: number
  method?: string
  reasoning?: string
  message?: string
  similarTodos?: EstimateHoursSimilar[]
  error?: string
}

export async function estimateHours(payload: {
  title: string
  description?: string
  category?: string
  complexity?: string
}): Promise<EstimateHoursResponse> {
  const authStore = useAuthStore()
  const response = await apiClient.post<EstimateHoursResponse>(
    '/tools/estimate-hours',
    payload,
    { headers: { 'x-user-id': authStore.userId ?? '' } },
  )
  return response.data
}
