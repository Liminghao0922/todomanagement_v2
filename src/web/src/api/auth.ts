import { PublicClientApplication, Configuration, BrowserCacheLocation } from '@azure/msal-browser'

// MSAL 配置 - 需要替换为实际的 Azure Entra ID 配置
export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || '00000000-0000-0000-0000-000000000000',
    authority: import.meta.env.VITE_AZURE_AUTHORITY || 'https://login.microsoftonline.com/common',
    redirectUri: import.meta.env.VITE_AZURE_REDIRECT_URI || 'http://localhost:5173',
    postLogoutRedirectUri: '/',
  },
  cache: {
    cacheLocation: BrowserCacheLocation.LocalStorage,
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: () => {}, // 禁用日志输出
    },
  },
}

// 请求作用域
export const loginRequest = {
  scopes: ['User.Read'],
}

// 创建 MSAL 实例
export const pca = new PublicClientApplication(msalConfig)
