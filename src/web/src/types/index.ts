export interface Project {
  id: string
  userId: string
  name: string
  description?: string
  status: 'active' | 'completed' | 'archived'
  priority: 'low' | 'medium' | 'high'
  startDate?: Date | string
  endDate?: Date | string
  createdAt: Date | string
  updatedAt: Date | string
  todos?: Todo[]
}

export interface Todo {
  id: string
  userId: string
  title: string
  description?: string
  status: 'pending' | 'in-progress' | 'completed'
  priority: 'low' | 'medium' | 'high'
  dueDate?: Date | string
  tags: string[]
  createdAt: Date | string
  updatedAt: Date | string
  // Phase 1: AI-readiness fields
  estimatedHours?: number
  complexity?: 'simple' | 'medium' | 'complex'
  projectId?: string  // Link to Project entity
  category?: string
  // Phase 2: Execution tracking fields
  actualHours?: number
  dependencies?: string[]
  requiredSkills?: string[]
  // Completion tracking
  completedAt?: Date | string
  completedContent?: string
}

export interface VectorDoc {
  id: string
  userId: string
  content: string
  embedding: number[]
  metadata: Record<string, any>
}
