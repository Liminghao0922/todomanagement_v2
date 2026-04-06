import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { AccountInfo } from '@azure/msal-browser'
import { pca, loginRequest } from '@/api/auth'
import { createOwner } from '@/api/owners'

export const useAuthStore = defineStore('auth', () => {
  const account = ref<AccountInfo | null>(null)
  const ownerId = ref<string | null>(null)  // 存储创建的owner ID
  const isAuthenticated = computed(() => account.value !== null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // 登录
  const login = async () => {
    isLoading.value = true
    error.value = null
    try {
      const loginResponse = await pca.loginPopup(loginRequest)
      account.value = loginResponse.account
      
      // 登录成功后自动创建owner
      if (account.value) {
        const name = account.value.name || account.value.username || 'User'
        const email = account.value.username || account.value.name || ''
        const azureId = account.value.localAccountId || account.value.homeAccountId || ''
        
        try {
          const owner = await createOwner({
            id: azureId,  // 传入Azure AD ID
            name,
            email,
          })
          ownerId.value = owner.id
          console.log('✓ Owner created/verified successfully, ID:', owner.id)
        } catch (ownerErr: any) {
          console.error('Failed to create owner:', ownerErr)
          error.value = ownerErr.message || 'Failed to create owner'
          throw ownerErr  // 直接抛出错误，而不是继续
        }
      }
      
      return true // 登录成功
    } catch (err: any) {
      error.value = err.message || 'Login failed'
      console.error('Login error:', err)
      return false // 登录失败
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  const logout = async () => {
    isLoading.value = true
    try {
      if (account.value) {
        await pca.logoutPopup({
          postLogoutRedirectUri: '/',
          mainWindowRedirectUri: '/',
        })
      }
      account.value = null
    } catch (err: any) {
      error.value = err.message || 'Logout failed'
      console.error('Logout error:', err)
    } finally {
      isLoading.value = false
    }
  }

  // 初始化认证
  const initAuth = async () => {
    isLoading.value = true
    try {
      await pca.initialize()
      const accounts = pca.getAllAccounts()
      if (accounts.length > 0) {
        account.value = accounts[0]
      }
    } catch (err: any) {
      error.value = err.message || 'Auth initialization failed'
      console.error('Auth init error:', err)
    } finally {
      isLoading.value = false
    }
  }

  // 获取用户名
  const userName = computed(() => account.value?.name || 'User')
  
  // 获取用户ID（用于API调用）- 优先使用创建的ownerId
  const userId = computed(() => ownerId.value || account.value?.localAccountId || account.value?.homeAccountId || '')

  return {
    account,
    ownerId,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    initAuth,
    userName,
    userId,
  }
})
