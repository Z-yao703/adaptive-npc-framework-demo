/**
 * 感官配置面板（v2 简化版）
 * 仅包含：detect_player 开关 + database_binding 下拉框
 */

import React from 'react'
import { Eye } from 'lucide-react'

const DATABASE_OPTIONS = [
  { value: 'none', label: '无权限' },
  { value: 'world_db', label: '世界数据库' },
  { value: 'items_db', label: '物品数据库' },
]

export default function SensorPanel({ value, onChange }) {
  const sensors = value || { detect_player: true, database_binding: 'none' }

  const updateSensor = (key, newValue) => {
    onChange({ ...sensors, [key]: newValue })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Eye className="w-5 h-5 text-green-500" />
          感官配置
        </h2>
      </div>

      {/* detect_player 开关 */}
      <div className="panel p-4">
        <div className="flex items-center justify-between">
          <div>
            <label className="text-sm font-medium text-slate-200">感知玩家位置</label>
            <p className="text-xs text-slate-500 mt-1">允许 NPC 检测玩家坐标</p>
          </div>
          <button
            onClick={() => updateSensor('detect_player', !sensors.detect_player)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              sensors.detect_player ? 'bg-green-500' : 'bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                sensors.detect_player ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* database_binding 下拉框 */}
      <div className="panel p-4">
        <label className="text-sm font-medium text-slate-200 block mb-2">数据库访问权限</label>
        <select
          value={sensors.database_binding || 'none'}
          onChange={(e) => updateSensor('database_binding', e.target.value)}
          className="w-full px-3 py-2 rounded bg-slate-700 border border-slate-600 text-slate-200 text-sm focus:border-blue-500 focus:outline-none"
        >
          {DATABASE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <p className="text-xs text-slate-500 mt-2">控制 NPC 可访问的后端数据库</p>
      </div>
    </div>
  )
}
