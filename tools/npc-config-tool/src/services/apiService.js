/**
 * API 服务
 * 处理与后端的 REST API 通信
 */

const API_BASE = '/api'

// ==================== Agent 管理 ====================

export async function listAgents() {
  const res = await fetch(`${API_BASE}/agent/list`)
  if (!res.ok) throw new Error('Failed to fetch agents')
  const data = await res.json()
  return data.agents || []
}

export async function getAgent(agentId) {
  const res = await fetch(`${API_BASE}/agent/${agentId}`)
  if (!res.ok) throw new Error('Agent not found')
  return res.json()
}

export async function saveAgent(config) {
  const res = await fetch(`${API_BASE}/agent/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  })
  if (!res.ok) throw new Error('Failed to save agent')
  return res.json()
}

export async function deleteAgent(agentId) {
  const res = await fetch(`${API_BASE}/agent/${agentId}`, {
    method: 'DELETE'
  })
  if (!res.ok) throw new Error('Failed to delete agent')
  return res.json()
}

export async function initAgent(agentId) {
  const res = await fetch(`${API_BASE}/agent/${agentId}/init`, {
    method: 'POST'
  })
  if (!res.ok) throw new Error('Failed to initialize agent')
  return res.json()
}

// ==================== 运行时 ====================

export async function processState(agentId, state) {
  const res = await fetch(`${API_BASE}/agent/${agentId}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state)
  })
  if (!res.ok) throw new Error('Failed to process state')
  return res.json()
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`)
  return res.json()
}

// ==================== 世界背景管理 ====================

export async function listWorlds() {
  const res = await fetch(`${API_BASE}/world/list`)
  if (!res.ok) throw new Error('Failed to fetch worlds')
  const data = await res.json()
  return data.worlds || []
}

export async function getWorld(worldId) {
  const res = await fetch(`${API_BASE}/world/${worldId}`)
  if (!res.ok) throw new Error('World not found')
  return res.json()
}

export async function saveWorld(config) {
  const res = await fetch(`${API_BASE}/world/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  })
  if (!res.ok) throw new Error('Failed to save world')
  return res.json()
}

export async function deleteWorld(worldId) {
  const res = await fetch(`${API_BASE}/world/${worldId}`, {
    method: 'DELETE'
  })
  if (!res.ok) throw new Error('Failed to delete world')
  return res.json()
}
