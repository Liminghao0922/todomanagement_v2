import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useAuthStore } from './stores/authStore'
import router from './router'
import App from './App.vue'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// 初始化认证
const authStore = useAuthStore()
authStore.initAuth().then(() => {
  app.mount('#app')
}).catch((err) => {
  console.error('Failed to initialize auth:', err)
  app.mount('#app')
})
