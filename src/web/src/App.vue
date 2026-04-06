<template>
  <div class="app">
    <header class="header">
      <div class="container">
        <div class="logo">📋 Todo Management</div>
        
        <!-- Navigation Menu -->
        <nav v-if="authStore.isAuthenticated" class="nav-menu">
          <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
            📝 Todos
          </router-link>
          <router-link to="/projects" class="nav-link" :class="{ active: $route.path === '/projects' }">
            📁 Projects
          </router-link>
        </nav>

        <div class="auth-section">
          <div v-if="authStore.isAuthenticated" class="user-menu">
            <span class="user-name">👤 {{ authStore.userName }}</span>
            <button class="logout-btn" @click="handleLogout" :disabled="authStore.isLoading">
              {{ authStore.isLoading ? '⏳' : '🚪' }} Logout
            </button>
          </div>
          <button v-else class="login-btn" @click="handleLogin" :disabled="authStore.isLoading">
            {{ authStore.isLoading ? '⏳ Loading...' : '🔐 Login' }}
          </button>
        </div>
      </div>
    </header>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()

const handleLogin = async () => {
  await authStore.login()
}

const handleLogout = async () => {
  await authStore.logout()
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
}

.header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 1rem 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.header .container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: #1f2937;
  white-space: nowrap;
  flex-shrink: 0;
}

.nav-menu {
  display: flex;
  gap: 1.5rem;
  flex: 1;
  justify-content: center;
}

.nav-link {
  color: #6b7280;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.3s;
}

.nav-link:hover {
  color: #1f2937;
  background: #f3f4f6;
}

.nav-link.active {
  color: #3b82f6;
  background: #eff6ff;
  border-bottom: 2px solid #3b82f6;
}

.auth-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-name {
  color: #1f2937;
  font-weight: 500;
  font-size: 0.95rem;
}

.login-btn,
.logout-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.95rem;
}

.login-btn {
  background: linear-gradient(135deg, #3b82f6, #1f2937);
  color: white;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.logout-btn {
  background: white;
  color: #1f2937;
  border: 1px solid #e5e7eb;
}

.logout-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.login-btn:disabled,
.logout-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.main {
  flex: 1;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem 1rem;
}

@media (max-width: 768px) {
  .header .container {
    flex-direction: column;
    gap: 1rem;
  }

  .auth-section {
    width: 100%;
    justify-content: center;
  }

  .login-btn,
  .logout-btn {
    width: 100%;
  }

  .user-menu {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
