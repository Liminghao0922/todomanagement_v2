<template>
  <div class="copilot-shell">
    <button class="copilot-trigger" @click="toggleDrawer" aria-label="Open AI Assistant">
      <span class="dot" />
      Copilot
    </button>

    <transition name="fade">
      <div v-if="isOpen" class="drawer-overlay" @click="closeDrawer" />
    </transition>

    <aside class="copilot-drawer" :class="{ open: isOpen }" aria-label="AI Assistant drawer">
      <header class="drawer-header">
        <div>
          <h3>AI Assistant</h3>
          <p>Ask Foundry or use quick prompts</p>
        </div>
        <div class="header-actions">
          <button class="icon-btn" :class="{ active: showHistory }" :title="showHistory ? 'Back to chat' : 'Conversation history'" @click="showHistory = !showHistory">🕘</button>
          <button class="icon-btn" title="New conversation" @click="startNewConversation">✏️</button>
          <button class="icon-btn" @click="closeDrawer" aria-label="Close AI Assistant">✕</button>
        </div>
      </header>

      <!-- History panel (replaces chat area when open) -->
      <section v-if="showHistory" class="history-panel">
        <p class="section-label">Previous Conversations</p>
        <div v-if="historyLoading" class="history-loading">Loading…</div>
        <div v-else-if="historyList.length === 0" class="history-empty">No saved conversations yet.</div>
        <ul v-else class="history-list">
          <li
            v-for="item in historyList"
            :key="item.id"
            class="history-item"
            @click="openHistoryConversation(item)"
          >
            <span class="history-title">{{ item.title }}</span>
            <span class="history-date">{{ new Date(item.updatedAt).toLocaleDateString() }}</span>
            <button class="history-delete" title="Delete" @click="removeConversation(item, $event)">🗑</button>
          </li>
        </ul>
      </section>

      <section v-if="!showHistory" class="quick-prompts">
        <p class="section-label">Common prompts</p>
        <div class="chips">
          <button
            v-for="prompt in quickPrompts"
            :key="prompt"
            class="chip"
            :disabled="loadingChat"
            @click="handleQuickPrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </section>

      <section v-if="!showHistory" class="chat-thread" aria-live="polite">
        <div v-if="messages.length === 0" class="empty-chat">
          <p>Start with a quick prompt or type your own request.</p>
        </div>
        <div v-for="message in messages" :key="message.id" class="message" :class="message.role">
          <p class="role-label">{{ message.role === 'user' ? 'You' : 'Assistant' }}</p>
          <div v-if="message.role === 'assistant'" class="content md-body" v-html="renderMarkdown(message.content)" />
          <p v-else class="content">{{ message.content }}</p>
        </div>
      </section>

      <section v-if="!showHistory" class="composer">
        <textarea
          v-model="chatInput"
          class="assistant-input"
          rows="3"
          placeholder="Ask Copilot-style assistant..."
          @keydown.ctrl.enter.prevent="handleChat()"
        />
        <div class="composer-actions">
          <span class="hint">Ctrl+Enter to send</span>
          <button class="btn btn-primary" :disabled="loadingChat || !chatInput.trim()" @click="handleChat()">
            {{ loadingChat ? 'Thinking...' : 'Send' }}
          </button>
        </div>
        <p v-if="chatError" class="error">{{ chatError }}</p>
      </section>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { chatWithFoundry } from '@/api/ai'
import {
  listConversations,
  getConversation,
  deleteConversation,
  type ConversationSummary,
} from '@/api/conversations'
import { useAuthStore } from '@/stores/authStore'

// ── Markdown ──────────────────────────────────────────────
const renderMarkdown = (text: string): string => {
  const raw = marked.parse(text, { async: false }) as string
  return DOMPurify.sanitize(raw)
}

// ── Types ─────────────────────────────────────────────────
type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

// ── State ─────────────────────────────────────────────────
const authStore = useAuthStore()

const isOpen = ref(false)
const showHistory = ref(false)

// Chat
const loadingChat = ref(false)
const chatInput = ref('')
const chatError = ref('')
const messages = ref<ChatMessage[]>([])
const conversationId = ref<string | undefined>(undefined)
const conversationDocId = ref<string | undefined>(undefined)

// History panel
const historyLoading = ref(false)
const historyList = ref<ConversationSummary[]>([])

// ── Quick prompts ─────────────────────────────────────────
const quickPrompts = [
  'What should I prioritize today?',
  'Summarize my top risks for this week.',
  'Break down my biggest task into subtasks.',
  'Suggest 5 high-impact todos for this project.',
  'Which todos should I delegate?',
  'Give me a realistic execution plan for this week.',
]

// ── Drawer ────────────────────────────────────────────────
const toggleDrawer = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) loadHistory()
}

const closeDrawer = () => {
  isOpen.value = false
  showHistory.value = false
  conversationId.value = undefined
  conversationDocId.value = undefined
  messages.value = []
}

// ── History ───────────────────────────────────────────────
const loadHistory = async () => {
  historyLoading.value = true
  try {
    historyList.value = await listConversations()
  } catch {
    // Silently ignore if API is unavailable
  } finally {
    historyLoading.value = false
  }
}

const openHistoryConversation = async (summary: ConversationSummary) => {
  historyLoading.value = true
  try {
    const detail = await getConversation(summary.id)
    messages.value = detail.messages.map((m, i) => ({
      id: `${m.role}-${i}`,
      role: m.role,
      content: m.content,
    }))
    conversationId.value = detail.conversationId
    conversationDocId.value = detail.id
    showHistory.value = false
    await nextTick()
  } catch {
    // ignore
  } finally {
    historyLoading.value = false
  }
}

const removeConversation = async (summary: ConversationSummary, event: Event) => {
  event.stopPropagation()
  try {
    await deleteConversation(summary.id)
    historyList.value = historyList.value.filter((c) => c.id !== summary.id)
  } catch {
    // ignore
  }
}

const startNewConversation = () => {
  conversationId.value = undefined
  conversationDocId.value = undefined
  messages.value = []
  chatError.value = ''
  showHistory.value = false
}

// ── Chat ──────────────────────────────────────────────────
const pushMessage = (role: 'user' | 'assistant', content: string) => {
  messages.value.push({
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
  })
}

const handleChat = async (preset?: string) => {
  const message = (preset || chatInput.value).trim()
  if (!message) return

  if (!authStore.userId) {
    chatError.value = 'Please login first so the assistant can read your todos and projects.'
    pushMessage('assistant', `Error: ${chatError.value}`)
    return
  }

  loadingChat.value = true
  chatError.value = ''
  pushMessage('user', message)

  try {
    const result = await chatWithFoundry(
      message,
      authStore.userId,
      conversationId.value,
      conversationDocId.value,
    )
    if (result.error) {
      chatError.value = result.error
      pushMessage('assistant', `Error: ${result.error}`)
      return
    }
    const answer = result.answer || result.content || 'No response content returned.'
    pushMessage('assistant', answer)
    if (result.conversationId) conversationId.value = result.conversationId
    if (result.conversationDocId) {
      conversationDocId.value = result.conversationDocId
      // Refresh sidebar list with the new/updated entry
      loadHistory()
    }
    chatInput.value = ''
  } catch (err: any) {
    chatError.value = err?.message || 'Failed to query Foundry chat'
    pushMessage('assistant', `Error: ${chatError.value}`)
  } finally {
    loadingChat.value = false
  }
}

const handleQuickPrompt = async (prompt: string) => {
  chatInput.value = prompt
  await handleChat(prompt)
}
</script>

<style scoped>
.copilot-shell {
  position: relative;
  z-index: 30;
}

.copilot-trigger {
  position: fixed;
  right: 18px;
  top: 140px;
  z-index: 34;
  border: none;
  border-radius: 999px;
  padding: 10px 14px;
  color: #fff;
  font-weight: 600;
  background: linear-gradient(120deg, #0f3d91 0%, #0078d4 55%, #00a4ef 100%);
  box-shadow: 0 10px 30px rgba(10, 70, 160, 0.34);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8ef7ff;
  box-shadow: 0 0 0 4px rgba(142, 247, 255, 0.2);
}

.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(8, 16, 34, 0.34);
  backdrop-filter: blur(2px);
  z-index: 31;
}

.copilot-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: min(680px, 92vw);
  height: 100vh;
  background: #f4f8ff;
  border-left: 1px solid #d7e3f4;
  box-shadow: -12px 0 36px rgba(15, 40, 90, 0.24);
  z-index: 32;
  display: grid;
  grid-template-rows: auto auto 1fr auto auto;
  transform: translateX(102%);
  transition: transform 0.24s ease;
}

.copilot-drawer.open {
  transform: translateX(0);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #d7e3f4;
  background: linear-gradient(160deg, #e8f1ff 0%, #f7fbff 100%);
}

.drawer-header h3 {
  margin: 0;
  color: #173a67;
}

.drawer-header p {
  margin: 2px 0 0;
  color: #5d7394;
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 4px;
  align-items: center;
}

.icon-btn {
  border: none;
  background: #fff;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.icon-btn.active {
  background: #ddeeff;
}

/* ── History panel ── */
.history-panel {
  overflow-y: auto;
  padding: 14px 16px;
  grid-row: 2 / -1;
}

.history-loading,
.history-empty {
  color: #6884a5;
  font-size: 13px;
  margin-top: 8px;
}

.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #d5e3f5;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: background 0.15s;
}

.history-item:hover {
  background: #eef5ff;
}

.history-title {
  flex: 1;
  font-size: 13px;
  color: #1f3757;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-date {
  font-size: 11px;
  color: #8ca5c0;
  white-space: nowrap;
}

.history-delete {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  opacity: 0.5;
  padding: 0 2px;
}

.history-delete:hover {
  opacity: 1;
}

.quick-prompts,
.composer {
  padding: 14px 16px;
}

.section-label {
  margin: 0 0 10px;
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #557197;
  font-weight: 700;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  border: 1px solid #c7daf3;
  background: #ffffff;
  color: #254d7f;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}

.chat-thread {
  overflow: auto;
  padding: 0 16px 8px;
}

.empty-chat {
  margin-top: 12px;
  color: #6884a5;
  background: #edf4ff;
  border: 1px dashed #bad1ef;
  border-radius: 10px;
  padding: 12px;
}

.message {
  margin-top: 10px;
  border-radius: 12px;
  padding: 10px;
}

.message.user {
  background: #0f3d91;
  color: #f7fbff;
  margin-left: 24px;
}

.message.assistant {
  background: #ffffff;
  border: 1px solid #d5e3f5;
  color: #1f3757;
  margin-right: 24px;
}

.role-label {
  margin: 0 0 6px;
  font-size: 11px;
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.content {
  margin: 0;
  white-space: pre-wrap;
}

/* Markdown rendered content */
.md-body {
  white-space: normal;
  line-height: 1.6;
  font-size: 13.5px;
}
.md-body :deep(h1),
.md-body :deep(h2),
.md-body :deep(h3) {
  margin: 10px 0 4px;
  font-weight: 700;
  color: #173a67;
}
.md-body :deep(h3) { font-size: 14px; }
.md-body :deep(h2) { font-size: 15px; }
.md-body :deep(p) { margin: 6px 0; }
.md-body :deep(strong) { color: #0f3d91; }
.md-body :deep(ul),
.md-body :deep(ol) {
  padding-left: 18px;
  margin: 6px 0;
}
.md-body :deep(li) { margin: 3px 0; }
.md-body :deep(code) {
  background: #e8f0fb;
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 12px;
}
.md-body :deep(pre) {
  background: #e8f0fb;
  border-radius: 6px;
  padding: 8px 12px;
  overflow-x: auto;
  margin: 8px 0;
}
.md-body :deep(blockquote) {
  border-left: 3px solid #0078d4;
  margin: 6px 0;
  padding: 4px 10px;
  background: #f0f6ff;
  border-radius: 0 6px 6px 0;
}

.assistant-input {
  width: 100%;
  border: 1px solid #c7d6e6;
  border-radius: 10px;
  padding: 10px;
  resize: vertical;
  background: #fff;
}

.composer-actions {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  color: #5d7394;
  font-size: 12px;
}

.error {
  color: #b42318;
  margin-top: 8px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .copilot-trigger {
    right: 12px;
    top: auto;
    bottom: 18px;
  }

  .copilot-drawer {
    width: 100vw;
  }
}
</style>
