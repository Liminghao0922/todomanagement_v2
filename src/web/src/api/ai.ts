import { apiClient } from './http'

export interface ChatResponse {
  action_items?: Array<{ title: string; priority?: string; owner?: string }>
  count?: number
  answer?: string
  content?: string
  status?: string
  error?: string
}

export async function extractActionItems(meetingText: string): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/tools/extract-action-items', {
    meeting_text: meetingText,
  })
  return response.data
}

export async function chatWithFoundry(message: string): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>('/chat', { message })
  return response.data
}
