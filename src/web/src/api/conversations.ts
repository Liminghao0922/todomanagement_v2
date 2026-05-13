
import { apiClient } from './http'
import { useAuthStore } from '@/stores/authStore'

export interface ConversationSummary {
  id: string
  owner_id: string
  title: string
  conversationId: string
  createdAt: string
  updatedAt: string
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const authStore = useAuthStore()
  const res = await apiClient.get<{ items: ConversationSummary[] }>('/conversations', {
    headers: { 'x-user-id': authStore.userId ?? '' },
  })
  return res.data.items ?? []
}

export async function getConversation(docId: string): Promise<ConversationDetail> {
  const authStore = useAuthStore()
  const res = await apiClient.get<ConversationDetail>(`/conversations/${docId}`, {
    headers: { 'x-user-id': authStore.userId ?? '' },
  })
  return res.data
}

export async function deleteConversation(docId: string): Promise<void> {
  const authStore = useAuthStore()
  await apiClient.delete(`/conversations/${docId}`, {
    headers: { 'x-user-id': authStore.userId ?? '' },
  })
}
