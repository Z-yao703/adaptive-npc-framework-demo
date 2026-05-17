/**
 * 世界背景配置面板
 * 配置世界的背景信息、通用知识和主题分类
 */

import React from 'react'
import { Plus, X, Globe } from 'lucide-react'

export default function WorldConfigPanel({ config, onChange }) {
  // 添加描述条目
  const addDescription = () => {
    const newDesc = [...(config.description || []), '']
    onChange({ ...config, description: newDesc })
  }

  // 更新描述条目
  const updateDescription = (index, value) => {
    const newDesc = [...(config.description || [])]
    newDesc[index] = value
    onChange({ ...config, description: newDesc })
  }

  // 删除描述条目
  const removeDescription = (index) => {
    const newDesc = (config.description || []).filter((_, i) => i !== index)
    onChange({ ...config, description: newDesc })
  }

  // 添加类别
  const addCategory = () => {
    const newCategories = [...(config.categories || []), { name: '', items: [''] }]
    onChange({ ...config, categories: newCategories })
  }

  // 更新类别名称
  const updateCategoryName = (index, value) => {
    const newCategories = [...(config.categories || [])]
    newCategories[index] = { ...newCategories[index], name: value }
    onChange({ ...config, categories: newCategories })
  }

  // 删除类别
  const removeCategory = (index) => {
    const newCategories = (config.categories || []).filter((_, i) => i !== index)
    onChange({ ...config, categories: newCategories })
  }

  // 添加信息条目
  const addItem = (catIndex) => {
    const newCategories = [...(config.categories || [])]
    newCategories[catIndex] = {
      ...newCategories[catIndex],
      items: [...newCategories[catIndex].items, '']
    }
    onChange({ ...config, categories: newCategories })
  }

  // 更新信息条目
  const updateItem = (catIndex, itemIndex, value) => {
    const newCategories = [...(config.categories || [])]
    newCategories[catIndex] = {
      ...newCategories[catIndex],
      items: [...newCategories[catIndex].items]
    }
    newCategories[catIndex].items[itemIndex] = value
    onChange({ ...config, categories: newCategories })
  }

  // 删除信息条目
  const removeItem = (catIndex, itemIndex) => {
    const newCategories = [...(config.categories || [])]
    newCategories[catIndex] = {
      ...newCategories[catIndex],
      items: newCategories[catIndex].items.filter((_, i) => i !== itemIndex)
    }
    onChange({ ...config, categories: newCategories })
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <h2 className="text-lg font-semibold flex items-center gap-2">
        <Globe className="w-5 h-5 text-blue-500" />
        世界背景配置
      </h2>

      {/* 基本信息区块 */}
      <div className="bg-slate-900 rounded-lg p-4 space-y-4">
        <h3 className="text-md font-semibold text-slate-300">基本信息</h3>
        
        {/* ID - 只读 */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">ID</label>
          <input
            type="text"
            value={config.id || ''}
            disabled
            className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-slate-500"
          />
        </div>

        {/* 名称 */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">名称</label>
          <input
            type="text"
            value={config.name || ''}
            onChange={(e) => onChange({ ...config, name: e.target.value })}
            placeholder="输入世界背景名称..."
            className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
          />
        </div>

        {/* 世界描述 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-slate-400">世界描述</label>
            <button onClick={addDescription} className="btn btn-secondary text-xs flex items-center gap-1">
              <Plus className="w-3 h-3" />
              添加描述条目
            </button>
          </div>
          <div className="space-y-2">
            {(config.description || []).map((desc, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="text"
                  value={desc}
                  onChange={(e) => updateDescription(index, e.target.value)}
                  placeholder={`描述条目 ${index + 1}...`}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-sm"
                />
                <button onClick={() => removeDescription(index)} className="p-2 text-red-400 hover:bg-slate-700 rounded">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 世界信息区块 */}
      <div className="bg-slate-900 rounded-lg p-4 space-y-4">
        <h3 className="text-md font-semibold text-slate-300">世界信息</h3>
        
        {/* 通用信息 */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">通用信息</label>
          <textarea
            value={config.general_info || ''}
            onChange={(e) => onChange({ ...config, general_info: e.target.value })}
            placeholder="输入世界的通用知识..."
            rows={6}
            className="w-full px-3 py-3 rounded-lg resize-none font-mono text-sm bg-slate-700 border border-slate-600"
          />
        </div>

        {/* 主题分类 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-slate-400">主题分类</label>
            <button onClick={addCategory} className="btn btn-secondary text-xs flex items-center gap-1">
              <Plus className="w-3 h-3" />
              添加类别
            </button>
          </div>
          <div className="space-y-3">
            {(config.categories || []).map((cat, catIndex) => (
              <div key={catIndex} className="bg-slate-800 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <input
                    type="text"
                    value={cat.name}
                    onChange={(e) => updateCategoryName(catIndex, e.target.value)}
                    placeholder="类别名称..."
                    className="flex-1 px-3 py-1 rounded bg-slate-700 border border-slate-600 text-sm"
                  />
                  <button onClick={() => removeCategory(catIndex)} className="p-1 text-red-400 hover:bg-slate-700 rounded">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="space-y-1 ml-4">
                  {(cat.items || []).map((item, itemIndex) => (
                    <div key={itemIndex} className="flex gap-2">
                      <input
                        type="text"
                        value={item}
                        onChange={(e) => updateItem(catIndex, itemIndex, e.target.value)}
                        placeholder={`信息 ${itemIndex + 1}...`}
                        className="flex-1 px-2 py-1 rounded bg-slate-700 border border-slate-600 text-xs"
                      />
                      <button onClick={() => removeItem(catIndex, itemIndex)} className="p-1 text-red-400 hover:bg-slate-700 rounded">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  <button onClick={() => addItem(catIndex)} className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 mt-1">
                    <Plus className="w-3 h-3" />
                    添加信息
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
