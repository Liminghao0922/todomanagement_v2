<template>
  <section class="ai-assistant">
    <h3>AI Assistant</h3>
    <p class="hint">Use Foundry chat for planning, or paste meeting notes to extract action items.</p>
    <textarea
      v-model="chatInput"
      class="assistant-input"
      rows="3"
      placeholder="Example: What should I prioritize this week?"
    />
    <div class="actions">
      <button class="btn btn-primary" :disabled="loadingChat || !chatInput.trim()" @click="handleChat">
        {{ loadingChat ? 'Thinking...' : 'Ask Foundry' }}
      </button>
    </div>
    <p v-if="chatError" class="error">{{ chatError }}</p>
    <div v-if="chatAnswer" class="answer-box">
      {{ chatAnswer }}
    </div>

    <hr class="divider" />
    <textarea
      v-model="meetingText"
      class="assistant-input"
      rows="4"
      placeholder="Example: Follow up with vendor by Thursday, prepare release notes..."
    />
    <div class="actions">
      <button class="btn btn-primary" :disabled="loading || !meetingText.trim()" @click="handleExtract">
        {{ loading ? 'Analyzing...' : 'Extract Action Items' }}
      </button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <ul v-if="items.length" class="items">
      <li v-for="item in items" :key="item.title + item.priority">
        <strong>{{ item.title }}</strong>
        <span v-if="item.priority">({{ item.priority }})</span>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { chatWithFoundry, extractActionItems } from '@/api/ai'

const loading = ref(false)
const loadingChat = ref(false)
const chatInput = ref('')
const chatAnswer = ref('')
const chatError = ref('')
const meetingText = ref('')
const items = ref<Array<{ title: string; priority?: string; owner?: string }>>([])
const error = ref('')

const handleChat = async () => {
  loadingChat.value = true
  chatError.value = ''
  chatAnswer.value = ''
  try {
    const result = await chatWithFoundry(chatInput.value)
    if (result.error) {
      chatError.value = result.error
      return
    }
    chatAnswer.value = result.answer || result.content || 'No response content returned.'
  } catch (err: any) {
    chatError.value = err?.message || 'Failed to query Foundry chat'
  } finally {
    loadingChat.value = false
  }
}

const handleExtract = async () => {
  loading.value = true
  error.value = ''
  items.value = []
  try {
    const result = await extractActionItems(meetingText.value)
    if (result.error) {
      error.value = result.error
      return
    }
    items.value = result.action_items || []
  } catch (err: any) {
    error.value = err?.message || 'Failed to extract action items'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ai-assistant {
  border: 1px solid #dbe4ee;
  background: #f9fbff;
  border-radius: 12px;
  padding: 16px;
  margin: 12px 0 20px;
}

.hint {
  color: #5c6f84;
  margin-bottom: 8px;
}

.assistant-input {
  width: 100%;
  border: 1px solid #c7d6e6;
  border-radius: 10px;
  padding: 10px;
  resize: vertical;
}

.actions {
  margin-top: 10px;
}

.divider {
  margin: 14px 0;
  border: 0;
  border-top: 1px solid #dbe4ee;
}

.error {
  color: #b42318;
  margin-top: 8px;
}

.answer-box {
  margin-top: 8px;
  background: #eff6ff;
  border: 1px solid #cfe3ff;
  border-radius: 10px;
  padding: 10px;
  color: #123250;
  white-space: pre-wrap;
}

.items {
  margin-top: 10px;
  padding-left: 18px;
}
</style>
