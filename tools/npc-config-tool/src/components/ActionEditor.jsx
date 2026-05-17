/**
 * 动作配置面板（v2 简化版）
 * 固定 8 个动作的启用/禁用开关，无参数编辑
 */

import React from 'react'
import { Zap } from 'lucide-react'

const FIXED_ACTIONS = [
  { id: 'GIVE_ITEM', label: '给予物品', desc: '将物品交给玩家' },
  { id: 'MOVE_TO', label: '移动到目标', desc: 'NPC 移动到指定位置' },
  { id: 'NPC_EMOTE', label: '表情动作', desc: '播放表情动画' },
  { id: 'NPC_SAY', label: '说话', desc: 'NPC 对话输出' },
  { id: 'NPC_STOP', label: '停止移动', desc: '中断当前移动' },
  { id: 'START_QUEST', label: '开始任务', desc: '发布新任务给玩家' },
  { id: 'TAKE_ITEM', label: '拿走物品', desc: '从玩家背包移除物品' },
  { id: 'UPDATE_QUEST', label: '更新任务进度', desc: '修改任务状态' },
]

export default function ActionEditor({ value, onChange }) {
  const enabledActions = value || []

  const toggleAction = (actionId) => {
    if (enabledActions.includes(actionId)) {
      onChange(enabledActions.filter(a => a !== actionId))
    } else {
      onChange([...enabledActions, actionId])
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-500" />
          动作配置
        </h2>
        <span className="text-sm text-slate-400">
          已启用 {enabledActions.length} / {FIXED_ACTIONS.length} 个
        </span>
      </div>

      {/* 动作列表 */}
      <div className="space-y-3">
        {FIXED_ACTIONS.map(action => {
          const isEnabled = enabledActions.includes(action.id)
          return (
            <div key={action.id} className="panel p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="font-medium text-sm text-slate-200">{action.label}</div>
                  <div className="text-xs text-slate-500 mt-1">{action.desc}</div>
                  <code className="text-xs text-slate-600 mt-1 block">{action.id}</code>
                </div>
                <button
                  onClick={() => toggleAction(action.id)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ml-4 ${
                    isEnabled ? 'bg-green-500' : 'bg-slate-600'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      isEnabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {enabledActions.length === 0 && (
        <div className="text-center py-8 text-slate-500 panel">
          未启用任何动作，NPC 将无法执行操作
        </div>
      )}
    </div>
  )
}
