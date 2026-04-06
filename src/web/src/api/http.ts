import axios, { AxiosInstance } from 'axios'

const baseURL = '/api'

// 将 snake_case 转换为 camelCase
function toCamelCase(obj: any): any {
  if (obj === null || typeof obj !== 'object' || obj instanceof Date) {
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map(item => toCamelCase(item))
  }

  const newObj: any = {}
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      // Special mapping for owner_id -> userId
      let camelKey = key
      if (key === 'owner_id') {
        camelKey = 'userId'
      } else {
        camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
      }
      newObj[camelKey] = toCamelCase(obj[key])
    }
  }
  return newObj
}

const apiClient: AxiosInstance = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器 - 转换字段名并处理错误
apiClient.interceptors.response.use(
  (response) => {
    // 转换响应数据中的字段名
    if (response.data) {
      response.data = toCamelCase(response.data)
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      console.error('Unauthorized')
    }
    return Promise.reject(error)
  }
)

export { apiClient }
