/**
 * 世界背景列表组件
 * 左侧显示所有已配置的世界背景
 */

import React from 'react'
import { Globe, Clock } from 'lucide-react'

export default function WorldList({ worlds, selectedId, onSelect }) {
  if (!worlds || !worlds.length) {
    return (
      <div className="text-center text-slate-500 py-8 text-sm">
        暂无世界背景
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {worlds.map(world => (
        <button
          key={world.id}
          onClick={() => onSelect(world.id)}
          className={`w-full text-left p-3 rounded-lg transition-colors ${
            selectedId === world.id 
              ? 'bg-blue-600/20 border border-blue-500' 
              : 'hover:bg-slate-700 border border-transparent'
          }`}
        >
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-slate-400" />
            <span className="font-medium truncate">{world.name || world.id}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
            <Clock className="w-3 h-3" />
            {world.updated_at ? formatTime(world.updated_at) : '未知'}
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
