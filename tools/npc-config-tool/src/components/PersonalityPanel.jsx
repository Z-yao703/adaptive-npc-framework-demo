/**
 * 人格设定面板 (v2 格式)
 * 配置 NPC 的性格特点、说话风格和知识限制
 */

import React, { useState, useEffect } from 'react'
import { MessageSquare, Plus, X, Globe, User } from 'lucide-react'
import * as api from '../services/apiService'

// 预设性格标签
const PERSONALITY_TAGS = [
  '友好', '冷漠', '暴躁', '慈祥', '古板', '贪财', '忠诚',
  '狡猾', '胆小', '勇敢', '固执', '幽默', '神秘', '高傲'
]

export default function PersonalityPanel({ config, onChange, worlds }) {
  const [customTag, setCustomTag] = useState('')
  const [selectedWorld, setSelectedWorld] = useState(null)

  // 更新 persona 下的字段
  const updatePersona = (key, value) => {
    onChange('persona', { ...(config.persona || {}), [key]: value })
  }
  
  // 更新 meta 下的字段
  const updateMeta = (key, value) => {
    onChange('meta', { ...(config.meta || {}), [key]: value })
  }

  // 切换性格标签 - v2: meta.tags
  const toggleTag = (tag) => {
    const current = config.meta?.tags || []
    if (current.includes(tag)) {
      updateMeta('tags', current.filter(t => t !== tag))
    } else {
      updateMeta('tags', [...current, tag])
    }
  }

  // 添加自定义标签
  const addCustomTag = () => {
    if (customTag.trim()) {
      const current = config.meta?.tags || []
      if (!current.includes(customTag.trim())) {
        updateMeta('tags', [...current, customTag.trim()])
      }
      setCustomTag('')
    }
  }

  // 当 world_id 变化时，从后端加载完整的世界配置
  useEffect(() => {
    if (config.persona?.world_id) {
      api.getWorld(config.persona.world_id)
        .then(worldConfig => {
          setSelectedWorld(worldConfig)
        })
        .catch(err => {
          console.error('加载世界配置失败:', err)
          setSelectedWorld(null)
        })
    } else {
      setSelectedWorld(null)
    }
  }, [config.persona?.world_id])

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-lg font-semibold flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-blue-500" />
        人格设定与知识限制
      </h2>

      {/* 模块1：性格标签选择 */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <User className="w-4 h-4" />
          性格标签
        </h3>

        {/* 预设标签 */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            选择性格特点
          </label>
          <div className="flex flex-wrap gap-2">
            {PERSONALITY_TAGS.map(tag => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  (config.meta?.tags || []).includes(tag)
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* 自定义标签输入 */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            自定义标签
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={customTag}
              onChange={(e) => setCustomTag(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addCustomTag()}
              placeholder="输入自定义标签"
              className="flex-1 px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
            />
            <button
              onClick={addCustomTag}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 已选标签展示 */}
        {(config.meta?.tags || []).length > 0 && (
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              已选标签
            </label>
            <div className="flex flex-wrap gap-2">
              {(config.meta?.tags || []).map(tag => (
                <span
                  key={tag}
                  className="px-3 py-1 rounded-full text-sm bg-blue-600/20 text-blue-300 flex items-center gap-1"
                >
                  {tag}
                  <button
                    onClick={() => toggleTag(tag)}
                    className="hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 分隔线 */}
      <div className="border-t border-slate-700 pt-6"></div>

      {/* 模块2：NPC 知识限制（世界选择） */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <Globe className="w-4 h-4" />
          NPC 知识限制
        </h3>

        {/* 世界 ID 选择 */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            绑定世界背景
          </label>
          <select
            value={config.persona?.world_id || ''}
            onChange={(e) => updatePersona('world_id', e.target.value)}
            className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
          >
            <option value="">-- 请选择世界背景 --</option>
            {(worlds || []).map(world => (
              <option key={world.id} value={world.id}>
                {world.name || world.id}
              </option>
            ))}
          </select>
        </div>

        {/* 通用知识展示（只读） */}
        {selectedWorld && (
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              通用知识
            </label>
            <div className="w-full px-3 py-3 rounded-lg bg-slate-800 border border-slate-600 text-sm text-slate-400 min-h-[100px]">
              {selectedWorld.general_info || '（该世界暂无通用知识）'}
            </div>
          </div>
        )}

        {/* 专有知识类别选择 */}
        {selectedWorld && selectedWorld.categories && (
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              专有知识类别
            </label>
            <div className="flex flex-wrap gap-2">
              {selectedWorld.categories.map((cat, index) => (
                <button
                  key={index}
                  onClick={() => {
                    const current = config.persona?.allowed_categories || []
                    if (current.includes(cat.name)) {
                      updatePersona('allowed_categories', current.filter(c => c !== cat.name))
                    } else {
                      updatePersona('allowed_categories', [...current, cat.name])
                    }
                  }}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    (config.persona?.allowed_categories || []).includes(cat.name)
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 分隔线 */}
      <div className="border-t border-slate-700 pt-6"></div>

      {/* 模块3：说话风格 - v2: persona.speaking_style */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          说话风格
        </h3>
        <select
          value={config.persona?.speaking_style || 'normal'}
          onChange={(e) => updatePersona('speaking_style', e.target.value)}
          className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
        >
          <option value="normal">正常</option>
          <option value="formal">正式/文雅</option>
          <option value="casual">随意/口语化</option>
          <option value="archaic">古风/文言</option>
          <option value="playful">俏皮</option>
        </select>
      </div>
      
      {/* 分隔线 */}
      <div className="border-t border-slate-700 pt-6"></div>
      
      {/* 模块4：打招呼用语 - v2: persona.greeting */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          打招呼用语
        </h3>
        <input
          type="text"
          value={config.persona?.greeting || ''}
          onChange={(e) => updatePersona('greeting', e.target.value)}
          placeholder="如: 你好，欢迎来到我们村子！"
          className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
        />
        <p className="mt-1 text-xs text-slate-500">
          玩家第一次靠近 NPC 时，NPC 会说的第一句话
        </p>
      </div>
    </div>
  )
}
