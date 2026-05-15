<template>
  <div class="project-graph-page">
    <div class="graph-header">
      <button @click="goBack" class="btn btn-secondary">← Back</button>
      <h1>🕸️ {{ projectName }} - Task Timeline</h1>
      <div style="width: 80px"></div>
    </div>

    <div class="graph-toolbar">
      <button type="button" class="btn btn-secondary" @click="relayoutGraph" :disabled="graphLoading">Re-layout</button>
      <button type="button" class="btn btn-secondary" @click="fitGraph" :disabled="graphLoading">Fit</button>
    </div>

    <p class="graph-guidance">📅 Left to right timeline: earlier tasks on the left, later tasks on the right. Today is marked with a red line.</p>

    <div class="graph-legend" aria-label="Status legend">
      <span class="legend-title">Legend:</span>
      <span class="legend-item"><span class="legend-dot status-completed"></span>Completed</span>
      <span class="legend-item"><span class="legend-dot status-in-progress"></span>In Progress</span>
      <span class="legend-item"><span class="legend-dot status-pending"></span>Not Started</span>
      <span class="legend-item"><span class="legend-dot status-overdue"></span>Overdue</span>
    </div>

    <div v-if="graphWarnings.length" class="graph-warnings">
      <h4>⚠️ Schedule Consistency Hints</h4>
      <ul>
        <li v-for="(warning, index) in graphWarnings" :key="`warn-${index}`">
          <template v-for="(seg, segIdx) in renderWarning(warning)" :key="`warn-${index}-seg-${segIdx}`">
            <a
              v-if="seg.type === 'todo'"
              :href="`/todos/${seg.id}/edit`"
              target="_blank"
              rel="noopener"
              class="warning-todo-link"
            >{{ seg.text }}</a>
            <span v-else>{{ seg.text }}</span>
          </template>
        </li>
      </ul>
    </div>

    <div v-if="graphLoading" class="loading">⏳ Building graph...</div>
    <div v-else-if="graphError" class="error-box">⚠️ {{ graphError }}</div>
    <div v-else>
      <div class="timeline-wrapper">
        <div class="timeline-axis">
          <div class="axis-line"></div>
          <div class="axis-inner" :style="axisTransformStyle">
            <div
              v-for="(date, idx) in timelineLabels"
              :key="`label-${idx}`"
              class="axis-label"
              :style="{ left: `${date.x}px` }"
            >
              <div class="label-text">{{ date.label }}</div>
              <div v-if="date.isToday" class="today-marker" title="Today"></div>
            </div>
          </div>
        </div>
        <div ref="graphContainer" class="graph-canvas"></div>

        <!-- Hover Tooltip -->
        <div
          v-if="hoveredTodo"
          class="node-tooltip"
          :style="{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }"
          @mouseenter="cancelHideTooltip"
          @mouseleave="scheduleHideTooltip"
        >
          <div class="tooltip-header">
            <span class="tooltip-status" :class="`status-${hoveredTodo._displayStatus}`">
              {{ statusIcon(hoveredTodo._displayStatus) }} {{ statusLabel(hoveredTodo._displayStatus) }}
            </span>
          </div>
          <h4 class="tooltip-title">{{ hoveredTodo.title }}</h4>
          <p v-if="hoveredTodo.description" class="tooltip-desc">
            {{ truncate(hoveredTodo.description, 120) }}
          </p>
          <div class="tooltip-meta">
            <span v-if="hoveredTodo.plannedStartDate">
              📅 {{ formatDate(hoveredTodo.plannedStartDate) }}
              <template v-if="hoveredTodo.plannedEndDate">
                → {{ formatDate(hoveredTodo.plannedEndDate) }}
              </template>
            </span>
          </div>
          <button class="btn btn-primary btn-sm" @click="openDetailModal(hoveredTodo)">View Details</button>
        </div>

        <!-- Detail Modal -->
        <div v-if="detailTodo" class="modal-overlay" @click="closeDetailModal">
          <div class="modal-content" @click.stop>
            <div class="modal-header">
              <h3>
                <span class="tooltip-status" :class="`status-${detailTodo._displayStatus}`">
                  {{ statusIcon(detailTodo._displayStatus) }}
                </span>
                {{ detailTodo.title }}
              </h3>
              <button @click="closeDetailModal" class="btn-close">✕</button>
            </div>
            <div class="detail-body">
              <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span :class="`status-pill status-${detailTodo._displayStatus}`">
                  {{ statusLabel(detailTodo._displayStatus) }}
                </span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Priority:</span>
                <span>{{ detailTodo.priority }}</span>
              </div>
              <div v-if="detailTodo.description" class="detail-row">
                <span class="detail-label">Description:</span>
                <p class="detail-text">{{ detailTodo.description }}</p>
              </div>
              <div v-if="detailTodo.plannedStartDate" class="detail-row">
                <span class="detail-label">Planned:</span>
                <span>
                  {{ formatDate(detailTodo.plannedStartDate) }}
                  <template v-if="detailTodo.plannedEndDate">
                    → {{ formatDate(detailTodo.plannedEndDate) }}
                  </template>
                </span>
              </div>
              <div v-if="detailTodo.dueDate" class="detail-row">
                <span class="detail-label">Due:</span>
                <span>{{ formatDate(detailTodo.dueDate) }}</span>
              </div>
              <div v-if="detailTodo.estimatedHours" class="detail-row">
                <span class="detail-label">Est. Hours:</span>
                <span>{{ detailTodo.estimatedHours }}h</span>
              </div>
              <div v-if="detailTodo.complexity" class="detail-row">
                <span class="detail-label">Complexity:</span>
                <span>{{ detailTodo.complexity }}</span>
              </div>
              <div v-if="detailTodo.tags && detailTodo.tags.length" class="detail-row">
                <span class="detail-label">Tags:</span>
                <span>{{ detailTodo.tags.join(', ') }}</span>
              </div>
            </div>
            <div class="modal-actions">
              <button class="btn btn-secondary" @click="closeDetailModal">Close</button>
              <button class="btn btn-primary" @click="goToTodoEdit(detailTodo.id)">Edit in Todos</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { getProjectById } from '@/api/projects'
import { getTodos } from '@/api/todos'
import cytoscape from 'cytoscape'
import type { Project } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const projectId = route.params.id as string
const projectName = ref('')
const graphLoading = ref(false)
const graphError = ref('')
const graphWarnings = ref<string[]>([])
const graphContainer = ref<HTMLElement | null>(null)
const timelineLabels = ref<Array<{ x: number; label: string; isToday: boolean }>>([])
const panX = ref(0)
const zoom = ref(1)

// Tooltip & detail modal state
const hoveredTodo = ref<any | null>(null)
const tooltipPos = ref({ x: 0, y: 0 })
const detailTodo = ref<any | null>(null)
let hideTooltipTimer: number | null = null
const todoMap = new Map<string, any>()

const axisTransformStyle = computed(() => ({
  transform: `translateX(${panX.value}px) scaleX(${zoom.value})`,
  transformOrigin: '0 0',
}))

// Status helpers
const computeDisplayStatus = (todo: any): 'completed' | 'overdue' | 'in-progress' | 'pending' => {
  if (todo.status === 'completed') return 'completed'
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const dueRaw = todo.dueDate || todo.plannedEndDate
  const due = dueRaw ? parseDateValue(dueRaw) : null
  if (due && due < today) return 'overdue'
  if (todo.status === 'in-progress') return 'in-progress'
  return 'pending'
}

const statusIcon = (status: string): string => {
  switch (status) {
    case 'completed': return '✓'
    case 'overdue': return '⚠'
    case 'in-progress': return '▶'
    default: return '○'
  }
}

const statusLabel = (status: string): string => {
  switch (status) {
    case 'completed': return 'Completed'
    case 'overdue': return 'Overdue'
    case 'in-progress': return 'In Progress'
    default: return 'Not Started'
  }
}

const formatDate = (value: unknown): string => {
  const d = parseDateValue(value)
  if (!d) return ''
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const truncate = (text: string, length: number): string =>
  text && text.length > length ? text.slice(0, length) + '…' : text || ''

const cancelHideTooltip = () => {
  if (hideTooltipTimer !== null) {
    window.clearTimeout(hideTooltipTimer)
    hideTooltipTimer = null
  }
}

const scheduleHideTooltip = () => {
  cancelHideTooltip()
  hideTooltipTimer = window.setTimeout(() => {
    hoveredTodo.value = null
  }, 200)
}

const openDetailModal = (todo: any) => {
  detailTodo.value = todo
  hoveredTodo.value = null
  cancelHideTooltip()
}

const closeDetailModal = () => {
  detailTodo.value = null
}

const goToTodoEdit = (todoId: string) => {
  router.push(`/todos/${todoId}/edit`)
}

let graphInstance: cytoscape.Core | null = null
let graphProjectNodeId = ''
const CANVAS_LEFT_MARGIN = 260

const goBack = () => {
  router.back()
}

const getRelationIds = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return []
  }
  return value.filter((v): v is string => typeof v === 'string' && v.length > 0)
}

const parseDateValue = (value: unknown): Date | null => {
  if (!value || typeof value !== 'string') {
    return null
  }
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

const dateOnly = (value: Date): string => value.toISOString().split('T')[0]

const shortLabel = (text: string): string => {
  if (!text) {
    return 'Untitled Task'
  }
  return text.length > 36 ? `${text.slice(0, 33)}...` : text
}

// Build a markdown-style todo reference like [Title](todo:abc-123) for use in warnings.
const todoRef = (id: string, title: string): string => {
  const safeTitle = shortLabel(title).replace(/[\[\]]/g, '')
  return `[${safeTitle}](todo:${id})`
}

type WarningSegment = { type: 'text'; text: string } | { type: 'todo'; id: string; text: string }

// Parse a warning string into renderable segments. Recognizes [label](todo:id) tokens.
const renderWarning = (warning: string): WarningSegment[] => {
  const segments: WarningSegment[] = []
  const pattern = /\[([^\]]+)\]\(todo:([^)]+)\)/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = pattern.exec(warning)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', text: warning.slice(lastIndex, match.index) })
    }
    segments.push({ type: 'todo', id: match[2], text: match[1] })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < warning.length) {
    segments.push({ type: 'text', text: warning.slice(lastIndex) })
  }
  return segments
}

const getPlannedWindow = (todo: any): { start: Date; end: Date } | null => {
  const start = parseDateValue(todo.plannedStartDate)
  if (!start) {
    return null
  }

  const end = parseDateValue(todo.plannedEndDate) || new Date(start)
  if (end < start) {
    return { start: end, end: start }
  }
  return { start, end }
}

const loadProjectTodos = async (pId: string) => {
  if (!authStore.userId) {
    return []
  }

  const all: any[] = []
  const pageSize = 200
  let offset = 0
  let total = 0

  do {
    const page = await getTodos(authStore.userId, pageSize, offset, { projectId: pId })
    all.push(...(page.items || []))
    total = page.total || 0
    offset += pageSize
  } while (offset < total)

  return all
}

const buildPlanFromDependencies = (projectTodos: any[]) => {
  const todoIds = new Set<string>(projectTodos.map(t => t.id))
  const incomingOriginal = new Map<string, number>()
  const incomingMutable = new Map<string, number>()
  const outgoing = new Map<string, Set<string>>()
  const depth = new Map<string, number>()
  const edges: Array<{ from: string; to: string; kind: 'BLOCKED_BY' | 'SUBTASK' | 'PRECEDES' }> = []

  for (const todo of projectTodos) {
    incomingOriginal.set(todo.id, 0)
    incomingMutable.set(todo.id, 0)
    outgoing.set(todo.id, new Set<string>())
    depth.set(todo.id, 1)
  }

  const addEdge = (fromId: string, toId: string, kind: 'BLOCKED_BY' | 'SUBTASK' | 'PRECEDES') => {
    if (!todoIds.has(fromId) || !todoIds.has(toId) || fromId === toId) {
      return
    }
    const nextSet = outgoing.get(fromId)
    if (!nextSet || nextSet.has(toId)) {
      return
    }
    nextSet.add(toId)
    incomingOriginal.set(toId, (incomingOriginal.get(toId) || 0) + 1)
    incomingMutable.set(toId, (incomingMutable.get(toId) || 0) + 1)
    edges.push({ from: fromId, to: toId, kind })
  }

  for (const todo of projectTodos) {
    for (const blockerId of getRelationIds(todo.blockedBy)) {
      addEdge(blockerId, todo.id, 'BLOCKED_BY')
    }
    for (const parentId of getRelationIds(todo.subtaskOf)) {
      addEdge(parentId, todo.id, 'SUBTASK')
    }
    for (const nextId of getRelationIds(todo.precedes)) {
      addEdge(todo.id, nextId, 'PRECEDES')
    }
  }

  const queue: string[] = []
  for (const [todoId, incomingCount] of incomingMutable.entries()) {
    if (incomingCount === 0) {
      queue.push(todoId)
    }
  }

  let visited = 0
  while (queue.length > 0) {
    const current = queue.shift()!
    visited += 1
    const currentDepth = depth.get(current) || 1
    const nextSet = outgoing.get(current)
    if (!nextSet) {
      continue
    }
    for (const nextId of nextSet.values()) {
      depth.set(nextId, Math.max(depth.get(nextId) || 1, currentDepth + 1))
      const nextIncoming = (incomingMutable.get(nextId) || 0) - 1
      incomingMutable.set(nextId, nextIncoming)
      if (nextIncoming === 0) {
        queue.push(nextId)
      }
    }
  }

  if (visited < projectTodos.length) {
    const maxDepth = Math.max(...Array.from(depth.values()), 1)
    for (const todo of projectTodos) {
      if ((incomingMutable.get(todo.id) || 0) > 0) {
        depth.set(todo.id, maxDepth + 1)
      }
    }
  }

  const roots = new Set<string>()
  for (const [todoId, incomingCount] of incomingOriginal.entries()) {
    if (incomingCount === 0) {
      roots.add(todoId)
    }
  }

  const windows = new Map<string, { start: Date; end: Date; title: string }>()
  const warnings: string[] = []
  for (const todo of projectTodos) {
    const window = getPlannedWindow(todo)
    if (!window) {
      warnings.push(`Missing planned start date: ${todoRef(todo.id, todo.title || 'Untitled Task')}`)
      continue
    }
    windows.set(todo.id, { ...window, title: todo.title || 'Untitled Task' })
  }

  const minStart = Array.from(windows.values()).reduce<Date | null>((acc, item) => {
    if (!acc || item.start < acc) {
      return item.start
    }
    return acc
  }, null)

  const dayOffset = new Map<string, number>()
  for (const todo of projectTodos) {
    const window = windows.get(todo.id)
    if (!window || !minStart) {
      dayOffset.set(todo.id, 0)
      continue
    }
    const diffMs = window.start.getTime() - minStart.getTime()
    dayOffset.set(todo.id, Math.max(0, Math.floor(diffMs / (24 * 60 * 60 * 1000))))
  }

  for (const edge of edges) {
    const fromWin = windows.get(edge.from)
    const toWin = windows.get(edge.to)
    if (fromWin && toWin && toWin.start < fromWin.end) {
      warnings.push(
        `${edge.kind}: ${todoRef(edge.to, toWin.title)} starts (${dateOnly(toWin.start)}) before ${todoRef(edge.from, fromWin.title)} ends (${dateOnly(fromWin.end)}).`
      )
      continue
    }

    const fromTodo = projectTodos.find(t => t.id === edge.from)
    const toTodo = projectTodos.find(t => t.id === edge.to)
    const fromDue = parseDateValue(fromTodo?.dueDate)
    const toDue = parseDateValue(toTodo?.dueDate)
    if (fromDue && toDue && toDue < fromDue) {
      warnings.push(
        `${edge.kind}: ${todoRef(edge.to, toTodo?.title || 'Untitled Task')} due date is earlier than prerequisite ${todoRef(edge.from, fromTodo?.title || 'Untitled Task')}.`
      )
    }
  }

  return {
    depth,
    dayOffset,
    roots,
    warnings: warnings.slice(0, 12),
    minStart,
    maxDayOffset: Math.max(...Array.from(dayOffset.values()), 0),
  }
}

const buildTimelineLabels = (minStart: Date | null, maxDayOffset: number) => {
  if (!minStart) {
    return []
  }

  const labels: Array<{ x: number; label: string; isToday: boolean }> = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  for (let day = 0; day <= maxDayOffset + 2; day++) {
    const d = new Date(minStart)
    d.setDate(d.getDate() + day)
    d.setHours(0, 0, 0, 0)

    const isToday = d.getTime() === today.getTime()
    const x = CANVAS_LEFT_MARGIN + day * 190
    const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

    labels.push({ x, label, isToday })
  }

  return labels
}

const applyTimelineLayout = (plan: any) => {
  if (!graphInstance) {
    return
  }

  const cy = graphInstance
  const centerY = cy.height() / 2
  const positions: Record<string, { x: number; y: number }> = {}

  const projectNode = cy.$id(graphProjectNodeId)
  if (projectNode.nonempty()) {
    positions[projectNode.id()] = { x: 80, y: centerY }
  }

  const buckets = new Map<number, cytoscape.NodeSingular[]>()
  cy.nodes('.todo-node').forEach(node => {
    const offset = Number(node.data('dayOffset') || 0)
    const depthValue = Number(node.data('depth') || 1)
    const key = (offset * 10) + depthValue
    if (!buckets.has(key)) {
      buckets.set(key, [])
    }
    buckets.get(key)!.push(node)
  })

  const sortedKeys = Array.from(buckets.keys()).sort((a, b) => a - b)
  for (const key of sortedKeys) {
    const nodes = buckets.get(key) || []
    nodes.sort((a, b) => String(a.data('label')).localeCompare(String(b.data('label'))))
    const offset = Number(nodes[0]?.data('dayOffset') || 0)
    const x = CANVAS_LEFT_MARGIN + (offset * 190)
    const count = Math.max(nodes.length, 1)
    const spacing = 100
    const totalHeight = (count - 1) * spacing
    const startY = centerY - (totalHeight / 2)

    for (let i = 0; i < nodes.length; i += 1) {
      positions[nodes[i].id()] = {
        x,
        y: startY + (i * spacing),
      }
    }
  }

  cy.nodes().unlock()
  if (projectNode.nonempty()) {
    projectNode.lock()
  }

  cy.layout({
    name: 'preset',
    positions,
    fit: true,
    padding: 70,
    animate: true,
    animationDuration: 280,
  }).run()
}

const buildGraph = (projectTodos: any[]) => {
  if (!graphContainer.value) {
    return
  }

  const plan = buildPlanFromDependencies(projectTodos)
  graphWarnings.value = plan.warnings

  timelineLabels.value = buildTimelineLabels(plan.minStart, plan.maxDayOffset)

  const elements: cytoscape.ElementDefinition[] = []
  const edgeIds = new Set<string>()

  const projectNodeId = `project-${projectId}`
  graphProjectNodeId = projectNodeId
  elements.push({
    data: {
      id: projectNodeId,
      label: projectName.value,
      depth: 0,
      dayOffset: 0,
    },
    classes: 'project-node',
  })

  const todoNodeMap = new Map<string, string>()
  todoMap.clear()
  for (const todo of projectTodos) {
    const nodeId = `todo-${todo.id}`
    todoNodeMap.set(todo.id, nodeId)
    const depthValue = plan.depth.get(todo.id) || 1
    const dayOffsetValue = plan.dayOffset.get(todo.id) || 0
    const isRoot = plan.roots.has(todo.id)
    const displayStatus = computeDisplayStatus(todo)
    const icon = statusIcon(displayStatus)

    // Cache for tooltip lookups
    todoMap.set(nodeId, { ...todo, _displayStatus: displayStatus })

    elements.push({
      data: {
        id: nodeId,
        label: `${icon}  ${todo.title || 'Untitled Task'}`,
        depth: depthValue,
        dayOffset: dayOffsetValue,
        todoId: todo.id,
      },
      classes: `todo-node status-${displayStatus}${isRoot ? ' root-task-node' : ''}`,
    })
  }

  const makeEdgeId = (prefix: string, fromId: string, toId: string) => `${prefix}-${fromId}-${toId}`

  for (const todo of projectTodos) {
    const sourceNodeId = todoNodeMap.get(todo.id)
    if (!sourceNodeId) {
      continue
    }

    const blockedBy = getRelationIds(todo.blockedBy)
    const precedes = getRelationIds(todo.precedes)
    const subtaskOf = getRelationIds(todo.subtaskOf)
    const isRoot = plan.roots.has(todo.id)

    if (isRoot) {
      const edgeId = makeEdgeId('project-link', projectNodeId, sourceNodeId)
      if (!edgeIds.has(edgeId)) {
        edgeIds.add(edgeId)
        elements.push({
          data: { id: edgeId, source: projectNodeId, target: sourceNodeId, label: 'ROOT' },
          classes: 'project-edge',
        })
      }
    }

    for (const parentId of subtaskOf) {
      const parentNodeId = todoNodeMap.get(parentId)
      if (!parentNodeId) {
        continue
      }
      const edgeId = makeEdgeId('subtask', parentNodeId, sourceNodeId)
      if (!edgeIds.has(edgeId)) {
        edgeIds.add(edgeId)
        elements.push({
          data: { id: edgeId, source: parentNodeId, target: sourceNodeId, label: 'SUBTASK' },
          classes: 'subtask-edge',
        })
      }
    }

    for (const blockerId of blockedBy) {
      const blockerNodeId = todoNodeMap.get(blockerId)
      if (!blockerNodeId) {
        continue
      }
      const edgeId = makeEdgeId('blocked-by', blockerNodeId, sourceNodeId)
      if (!edgeIds.has(edgeId)) {
        edgeIds.add(edgeId)
        elements.push({
          data: { id: edgeId, source: blockerNodeId, target: sourceNodeId, label: 'BLOCKED_BY' },
          classes: 'blocked-edge',
        })
      }
    }

    for (const nextId of precedes) {
      const nextNodeId = todoNodeMap.get(nextId)
      if (!nextNodeId) {
        continue
      }
      const edgeId = makeEdgeId('precedes', sourceNodeId, nextNodeId)
      if (!edgeIds.has(edgeId)) {
        edgeIds.add(edgeId)
        elements.push({
          data: { id: edgeId, source: sourceNodeId, target: nextNodeId, label: 'PRECEDES' },
          classes: 'precedes-edge',
        })
      }
    }
  }

  if (graphInstance) {
    graphInstance.destroy()
    graphInstance = null
  }

  graphInstance = cytoscape({
    container: graphContainer.value,
    elements,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': '#4f46e5',
          label: 'data(label)',
          color: '#1f2937',
          'font-size': '11px',
          'text-wrap': 'wrap',
          'text-max-width': '190px',
          'text-valign': 'center',
          'text-halign': 'center',
          'border-width': 2,
          'border-color': '#ffffff',
          width: '42px',
          height: '42px',
          'overlay-opacity': 0,
        },
      },
      {
        selector: '.project-node',
        style: {
          'background-color': '#f59e0b',
          'font-size': '14px',
          'font-weight': '700',
          width: '74px',
          height: '74px',
        },
      },
      {
        selector: '.root-task-node',
        style: {
          'border-width': 4,
          'border-color': '#1f2937',
        },
      },
      {
        selector: '.status-completed',
        style: {
          'background-color': '#10b981',
        },
      },
      {
        selector: '.status-overdue',
        style: {
          'background-color': '#ef4444',
        },
      },
      {
        selector: '.status-in-progress',
        style: {
          'background-color': '#f59e0b',
        },
      },
      {
        selector: '.status-pending',
        style: {
          'background-color': '#60a5fa',
        },
      },
      {
        selector: 'edge',
        style: {
          width: 2,
          'line-color': '#9ca3af',
          'target-arrow-color': '#9ca3af',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          label: 'data(label)',
          'font-size': '9px',
          color: '#4b5563',
          'text-background-color': '#ffffff',
          'text-background-opacity': 0.9,
          'text-background-padding': '2px',
          'overlay-opacity': 0,
        },
      },
      {
        selector: '.project-edge',
        style: {
          'line-color': '#f59e0b',
          'target-arrow-color': '#f59e0b',
        },
      },
      {
        selector: '.subtask-edge',
        style: {
          'line-color': '#3b82f6',
          'target-arrow-color': '#3b82f6',
        },
      },
      {
        selector: '.blocked-edge',
        style: {
          'line-color': '#ef4444',
          'target-arrow-color': '#ef4444',
          'line-style': 'dashed',
        },
      },
      {
        selector: '.precedes-edge',
        style: {
          'line-color': '#8b5cf6',
          'target-arrow-color': '#8b5cf6',
        },
      },
    ],
    layout: { name: 'preset' },
  })

  // Sync timeline axis with cytoscape pan/zoom
  const syncAxis = () => {
    if (!graphInstance) return
    const pan = graphInstance.pan()
    panX.value = pan.x
    zoom.value = graphInstance.zoom()
  }
  graphInstance.on('pan zoom resize', syncAxis)
  syncAxis()

  // Hover tooltip handlers
  graphInstance.on('mouseover', 'node.todo-node', (evt) => {
    const node = evt.target
    const nodeId = node.id() as string
    const todo = todoMap.get(nodeId)
    if (!todo) return
    cancelHideTooltip()
    const rendered = node.renderedPosition()
    const radius = (Number(node.renderedHeight()) || 42) / 2
    const canvasOffsetTop = graphContainer.value?.offsetTop || 0
    tooltipPos.value = { x: rendered.x, y: canvasOffsetTop + rendered.y - radius - 12 }
    hoveredTodo.value = todo
  })
  graphInstance.on('mouseout', 'node.todo-node', () => {
    scheduleHideTooltip()
  })
  graphInstance.on('tap', 'node.todo-node', (evt) => {
    const nodeId = evt.target.id() as string
    const todo = todoMap.get(nodeId)
    if (todo) openDetailModal(todo)
  })
  graphInstance.on('pan zoom', () => {
    hoveredTodo.value = null
  })

  applyTimelineLayout(plan)
  syncAxis()
}

const relayoutGraph = () => {
  if (!graphInstance) {
    return
  }
  const plan = buildPlanFromDependencies(
    graphInstance.elements().nodes('.todo-node').map(n => ({
      id: n.data('id'),
      depth: n.data('depth'),
      dayOffset: n.data('dayOffset'),
    }))
  )
  applyTimelineLayout(plan)
}

const fitGraph = () => {
  graphInstance?.fit(undefined, 40)
}

const initGraph = async () => {
  if (!projectId || !authStore.userId) return

  graphLoading.value = true
  graphError.value = ''
  graphWarnings.value = []

  try {
    const project = await getProjectById(projectId)
    if (!project) {
      graphError.value = 'Project not found'
      graphLoading.value = false
      return
    }

    projectName.value = project.name

    const projectTodos = await loadProjectTodos(projectId)
    graphLoading.value = false

    await nextTick()
    buildGraph(projectTodos)
  } catch (err) {
    console.error('Failed to build project graph:', err)
    graphError.value = 'Failed to load project graph'
    graphLoading.value = false
  }
}

onMounted(() => {
  initGraph()
})

onBeforeUnmount(() => {
  if (graphInstance) {
    graphInstance.destroy()
    graphInstance = null
  }
})
</script>

<style scoped>
.project-graph-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  background: #fafbfc;
  min-height: 100vh;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.graph-header h1 {
  margin: 0;
  font-size: 1.8rem;
  color: #333;
  flex: 1;
  text-align: center;
}

.graph-toolbar {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.btn {
  padding: 0.6rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  color: #333;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn:hover {
  background: #f0f0f0;
}

.btn-secondary {
  background: #e0e0e0;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

.graph-guidance {
  margin: 0 0 0.75rem 0;
  color: #4b5563;
  font-size: 0.9rem;
}

.graph-warnings {
  margin-bottom: 0.75rem;
  border: 1px solid #fde68a;
  background: #fffbeb;
  border-radius: 8px;
  padding: 0.75rem;
}

.graph-warnings h4 {
  margin: 0 0 0.45rem 0;
  color: #92400e;
  font-size: 0.9rem;
}

.graph-warnings ul {
  margin: 0;
  padding-left: 1.1rem;
  color: #78350f;
}

.warning-todo-link {
  color: #b45309;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}

.warning-todo-link:hover {
  color: #78350f;
  text-decoration: underline;
}

.graph-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #374151;
}

.graph-legend .legend-title {
  font-weight: 600;
  color: #1f2937;
}

.graph-legend .legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.graph-legend .legend-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #666;
  font-size: 1.1rem;
}

.error-box {
  background: #ffebee;
  color: #c62828;
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid #f44336;
}

.timeline-wrapper {
  position: relative;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  overflow: visible;
}

.timeline-axis {
  position: relative;
  height: 60px;
  background: #f8fafc;
  border-bottom: 2px solid #e5e7eb;
  overflow: hidden;
}

.axis-inner {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 1px;
  will-change: transform;
}

.axis-line {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #d1d5db;
  transform: translateY(-50%);
}

.axis-label {
  position: absolute;
  top: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0;
  transform: translateX(-50%);
}

.label-text {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 600;
  white-space: nowrap;
}

.today-marker {
  width: 2px;
  height: 100%;
  background: #ef4444;
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
}

.graph-canvas {
  width: 100%;
  height: 68vh;
  border-top: 2px solid #e5e7eb;
  background: linear-gradient(90deg, #f8fafc, #ffffff);
}

/* Hover Tooltip */
.node-tooltip {
  position: absolute;
  z-index: 50;
  width: 280px;
  transform: translate(-50%, -100%);
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
  padding: 0.85rem;
  pointer-events: auto;
}

.node-tooltip::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid #ffffff;
}

.tooltip-header {
  margin-bottom: 0.4rem;
}

.tooltip-title {
  margin: 0 0 0.4rem 0;
  font-size: 0.95rem;
  color: #111827;
  font-weight: 600;
}

.tooltip-desc {
  margin: 0 0 0.5rem 0;
  font-size: 0.8rem;
  color: #4b5563;
  line-height: 1.4;
}

.tooltip-meta {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.6rem;
}

.btn-sm {
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
}

.btn-primary {
  background: #4f46e5;
  color: #fff;
  border-color: #4338ca;
}

.btn-primary:hover {
  background: #4338ca;
}

/* Status pill / badge */
.tooltip-status,
.status-pill {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #fff;
}

.status-completed { background: #10b981; }
.status-overdue { background: #ef4444; }
.status-in-progress { background: #f59e0b; }
.status-pending { background: #60a5fa; }

/* Detail Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: #fff;
  border-radius: 12px;
  width: 90%;
  max-width: 540px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 1.5rem;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.modal-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.15rem;
  color: #1f2937;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #6b7280;
}

.btn-close:hover {
  color: #111827;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: 1.2rem;
}

.detail-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  font-size: 0.9rem;
  color: #374151;
}

.detail-label {
  font-weight: 600;
  color: #4b5563;
  min-width: 90px;
}

.detail-text {
  margin: 0;
  flex: 1;
  white-space: pre-wrap;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
}
</style>
