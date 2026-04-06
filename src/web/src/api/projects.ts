import { apiClient } from './http'
import type { Project } from '@/types'

export async function getProjects(
  userId: string,
  status?: string
): Promise<Project[]> {
  const params: Record<string, any> = { userId }
  if (status) {
    params.status = status
  }

  const response = await apiClient.get<Project[]>('/projects', { params })
  return response.data || []
}

export async function getProjectById(projectId: string): Promise<Project | null> {
  try {
    const response = await apiClient.get<Project>(`/projects/${projectId}`)
    return response.data || null
  } catch (error) {
    console.error('Error fetching project:', error)
    return null
  }
}

export interface CreateProjectRequest {
  name: string
  description?: string
  status?: 'active' | 'completed' | 'archived'
  priority?: 'low' | 'medium' | 'high'
  startDate?: string
  endDate?: string
}

export async function createProject(
  userId: string,
  project: CreateProjectRequest
): Promise<Project | null> {
  try {
    const response = await apiClient.post<Project>('/projects', 
      {
        ...project,
        userId
      },
      {
        params: { userId }
      }
    )
    return response.data || null
  } catch (error) {
    console.error('Error creating project:', error)
    throw error
  }
}

export interface UpdateProjectRequest {
  name?: string
  description?: string
  status?: 'active' | 'completed' | 'archived'
  priority?: 'low' | 'medium' | 'high'
  startDate?: string
  endDate?: string
}

export async function updateProject(
  projectId: string,
  updates: UpdateProjectRequest
): Promise<Project | null> {
  try {
    const response = await apiClient.patch<Project>(
      `/projects/${projectId}`,
      updates
    )
    return response.data || null
  } catch (error) {
    console.error('Error updating project:', error)
    throw error
  }
}

export async function deleteProject(projectId: string): Promise<boolean> {
  try {
    await apiClient.delete(`/projects/${projectId}`)
    return true
  } catch (error) {
    console.error('Error deleting project:', error)
    throw error
  }
}
