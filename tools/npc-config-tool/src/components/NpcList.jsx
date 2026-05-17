/**
 * NPC 列表组件
 * 左侧显示所有已配置的 NPC
 */

import React from 'react'
import { User, Clock } from 'lucide-react'

export default function NpcList({ agents, selectedId, onSelect }) {
  if (!agents.length) {
    return (
      <div className="text-center text-slate-500 py-8 text-sm">
        暂无 NPC，点击上方按钮创建
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {agents.map(agent => (
        <button
          key={agent.id}
          onClick={() => onSelect(agent.id)}
          className={`w-full text-left p-3 rounded-lg transition-colors ${
            selectedId === agent.id 
              ? 'bg-blue-600/20 border border-blue-500' 
              : 'hover:bg-slate-700 border border-transparent'
          }`}
        >
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-slate-400" />
            <span className="font-medium truncate">{agent.name || agent.id}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
            <Clock className="w-3 h-3" />
            {agent.updated_at ? formatTime(agent.updated_at) : '未知'}
          </div>
        </button>
      ))}
    </div>
  )
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
