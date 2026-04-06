import { apiClient } from './http'

export interface OwnerCreateRequest {
  id?: string  // Optional Azure AD account ID
  name: string
  email: string
}

export interface OwnerResponse {
  id: string
  name: string
  email: string
  createdAt?: string
  updatedAt?: string
}

/**
 * 创建owner（用户）
 * 如果owner已存在，直接返回现有owner
 */
export async function createOwner(ownerData: OwnerCreateRequest): Promise<OwnerResponse> {
  try {
    const response = await apiClient.post<OwnerResponse>('/owners', ownerData)
    return response.data
  } catch (error: any) {
    console.error('Error creating owner:', error)
    throw error
  }
}
