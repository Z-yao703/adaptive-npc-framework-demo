// NPC 配置工具 - 主业务组件
// 智能NPC框架的可视化配置界面

import React, { useState, useEffect, useCallback } from 'react'
import {
  Users, Plus, Settings, Save, Trash2, Play, RefreshCw,
  User, MessageSquare, Eye, Zap, Database, Wifi
} from 'lucide-react' // 图标
import NpcList from './components/NpcList'  // （左侧显示）所有已配置 NPC 列表
import BasicInfo from './components/BasicInfo'  // （右侧显示）1.NPC 基本信息
import PersonalityPanel from './components/PersonalityPanel' // （右侧显示）2.人格设定
import SensorPanel from './components/SensorPanel'  // （右侧显示）3.感官配置
import ActionEditor from './components/ActionEditor'  // （右侧显示）4.动作编辑
import DebugPanel from './components/DebugPanel'  // （右侧显示）5.调试面板
import DatabasePanel from './components/DatabasePanel'  // （右侧显示）6.数据库管理
import * as api from './services/apiService'  // 接口服务（负责和后端服务器通信的工具函数）
import WorldList from './components/WorldList'  // 世界背景列表组件
import WorldConfigPanel from './components/WorldConfigPanel'  // 世界背景配置面板

// 默认 NPC 配置 (v2 简化版)
const DEFAULT_CONFIG = {
  id: '',
  version: "2.0",
  meta: {
    name: '',
    role: 'villager',
    tags: []
  },
  presentation: {
    sprite: '',
    render_cfg: {
      frameWidth: 48,
      frameHeight: 64,
      scale: 2,
      animations: {
        idle_down: [0, 1],
        idle_left: [2, 3],
        idle_right: [4, 5],
        idle_up: [6, 7],
        walk_down: [8, 12],
        walk_left: [13, 17],
        walk_right: [18, 22],
        walk_up: [23, 27]
      }
    }
  },
  persona: {
    identity: '',
    speaking_style: 'normal',
    greeting: '',
    taboos: [],
    world_id: '',
    allowed_categories: []
  },
  knowledge: {
    world_facts: [],
    topics: []
  },
  sensors: {
    detect_player: true,
    database_binding: 'none'
  },
  actions: [],
  quests: []
}

// 默认世界背景配置
const DEFAULT_WORLD_CONFIG = {
  id: '',
  name: '',
  description: [],
  general_info: '',
  categories: []
}

// 主业务组件 NpcConfigTool
export default function NpcConfigTool() {
  // npc相关状态
  const [agents, setAgents] = useState([]) // 所有已配置的 NPC 列表
  const [selectedAgentId, setSelectedAgentId] = useState(null)  // 当前选中的 NPC 的 ID（初始为 null = 没选中）
  const [config, setConfig] = useState(DEFAULT_CONFIG)  // 当前选中的 NPC 的配置
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [connected, setConnected] = useState(false)
  const [activeTab, setActiveTab] = useState('basic')  // 当前选中的标签页名称（默认显示 'basic' 基本信息）息
  const [toast, setToast] = useState(null)  //toast = 提示消息（null 表示没有提示）

  // 世界背景相关状态
  const [worlds, setWorlds] = useState([])  // 世界背景列表
  const [selectedWorldId, setSelectedWorldId] = useState(null)  // 当前选中的世界背景 ID
  const [worldConfig, setWorldConfig] = useState(DEFAULT_WORLD_CONFIG)  // 当前世界背景配置
  const [activePanel, setActivePanel] = useState('npc')  // 'npc' | 'world' 当前激活的面板

  // 加载 NPC 列表
  const loadAgents = useCallback(async () => {
    setLoading(true)
    try {
      const list = await api.listAgents()  // 调用 api.listAgents() 获取所有已配置的 NPC 列表
      setAgents(list)
    } catch (err) {
      showToast('加载列表失败: ' + err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  // 加载选中 NPC 的配置
  const loadAgentConfig = useCallback(async (agentId) => {
    // 检查这个ID是否在 agents 列表中
    const agentExists = agents.some(agent => agent.id === agentId)
    
    // 如果ID不在列表中，说明是新建的临时ID，不加载
    if (!agentExists) {
      return
    }
    
    try {
      const cfg = await api.getAgent(agentId)  // 调用 api.getAgent(agentId) 获取指定 ID 的 NPC 配置
      setConfig(cfg)
    } catch (err) {
      showToast('加载配置失败', 'error')
    }
  }, [agents])  // 添加 agents 作为依赖

  // 加载世界背景列表
  const loadWorlds = useCallback(async () => {
    setLoading(true)
    try {
      const list = await api.listWorlds()
      setWorlds(list)
    } catch (err) {
      showToast('加载世界背景列表失败: ' + err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  // 初始化，打开页面时自动触发一次
  useEffect(() => {
    loadAgents()  // 加载所有已配置的 NPC 列表
    loadWorlds()  // 加载所有世界背景列表
  }, [loadAgents, loadWorlds])

  // 选择 NPC，当 selectedAgentId 变化时执行
  useEffect(() => {
    if (selectedAgentId) {
      loadAgentConfig(selectedAgentId) // 有选中 ID → 加载该 NPC 详情
    } else {
      setConfig({ ...DEFAULT_CONFIG, id: '' })  // 无选中 ID → 重置配置
    }
  }, [selectedAgentId, loadAgentConfig])

  // 创建新 NPC
  const handleCreateNew = () => {
    const newId = `npc_${Date.now()}`  // 生成新 ID（基于当前时间戳）
    setConfig({ ...DEFAULT_CONFIG, id: newId })
    setSelectedAgentId(newId)  // 设置为新建ID（不在列表中，避免高亮已存在的NPC）
  }

  // 保存配置
  const handleSave = async () => {
    if (!config.id) {
      showToast('请输入 NPC ID', 'error')
      return
    }
    setSaving(true)
    try {
      await api.saveAgent(config)  // 调用 api.saveAgent(config) 保存到后端
      showToast('保存成功！配置已热更新到运行中的 NPC', 'success')
      await loadAgents()  // 刷新列表（可能有新增）
      setSelectedAgentId(config.id)  // 选中刚保存的 NPC
    } catch (err) {
      showToast('保存失败: ' + err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  // 删除 NPC
  const handleDelete = async () => {
    if (!selectedAgentId) return
    if (!confirm('确定要删除这个 NPC 吗？')) return

    try {
      await api.deleteAgent(selectedAgentId)  // 调用 api.deleteAgent(selectedAgentId) 删除 NPC
      showToast('删除成功', 'success')
      setSelectedAgentId(null)  // 清空选中
      await loadAgents()  // 刷新列表
    } catch (err) {
      showToast('删除失败', 'error')
    }
  }

  // ==================== 世界背景相关处理函数 ====================

  // 创建新世界背景
  const handleCreateWorld = () => {
    const newId = `world_${Date.now()}`
    setWorldConfig({ ...DEFAULT_WORLD_CONFIG, id: newId })
    setSelectedWorldId(null)
    setActivePanel('world')
  }

  // 保存世界背景
  const handleSaveWorld = async () => {
    if (!worldConfig.id || !worldConfig.name) {
      showToast('请填写世界背景ID和名称', 'error')
      return
    }
    setSaving(true)
    try {
      await api.saveWorld(worldConfig)
      showToast('世界背景保存成功！', 'success')
      await loadWorlds()
      setSelectedWorldId(worldConfig.id)
    } catch (err) {
      showToast('保存失败: ' + err.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  // 删除世界背景
  const handleDeleteWorld = async () => {
    if (!selectedWorldId) return
    if (!confirm('确定要删除这个世界背景吗？')) return

    try {
      await api.deleteWorld(selectedWorldId)
      showToast('删除成功', 'success')
      setSelectedWorldId(null)
      setWorldConfig(DEFAULT_WORLD_CONFIG)
      setActivePanel('npc')
      await loadWorlds()
    } catch (err) {
      showToast('删除失败', 'error')
    }
  }

  // 选中世界背景
  const handleSelectWorld = async (worldId) => {
    try {
      const cfg = await api.getWorld(worldId)
      setWorldConfig(cfg)
      setSelectedWorldId(worldId)
      setActivePanel('world')
    } catch (err) {
      showToast('加载世界背景失败', 'error')
    }
  }

  // 选中NPC
  const handleSelectAgent = (agentId) => {
    setSelectedAgentId(agentId)
    setActivePanel('npc')
  }

  // 初始化 NPC 运行时
  const handleInit = async () => {
    if (!selectedAgentId) return  // 必须先选中一个 NPC
    try {
      await api.initAgent(selectedAgentId)  // 调用 api.initAgent(selectedAgentId) 初始化 NPC 运行时
      setConnected(true)  // 标记为"已连接"
      showToast('NPC 已初始化，可以接收游戏状态', 'success')
    } catch (err) {
      showToast('初始化失败', 'error')
    }
  }

  // 通用的配置更新函数（子组件调用它来修改数据）
  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  // 显示一条 Toast 临时提示（3秒后自动消失）
  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  // Tab 配置， 定义右侧的选项卡
  const tabs = [
    { id: 'basic', label: '基本信息', icon: User },
    { id: 'personality', label: '人格设定', icon: MessageSquare },
    { id: 'sensors', label: '感官配置', icon: Eye },
    { id: 'actions', label: '动作编辑', icon: Zap },
    { id: 'debug', label: '调试', icon: Settings },
    { id: 'database', label: '数据库', icon: Database },
  ]

  // 函数的 return 部分，描述 UI 结构
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* 顶部栏 */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          {/* 左侧：标题 */}
          <div className="flex items-center gap-3">
            <Users className="w-8 h-8 text-blue-500" />   {/* 蓝色用户图标 */}
            <div>
              <h1 className="text-xl font-bold">NPC 配置工具</h1>
              <p className="text-sm text-slate-400">Adaptive NPC Framework</p>
            </div>
          </div>
          {/* 右侧：连接状态 + 初始化按钮 */}
          <div className="flex items-center gap-4">
            {/* 连接状态指示器（绿色=已连，灰色=未连） */}
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${connected ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'
              }`}>
              <Wifi className="w-4 h-4" />
              {connected ? '已连接' : '未连接'}
            </div>
            {/* 初始化按钮 */}
            <button onClick={handleInit} className="btn btn-secondary flex items-center gap-2">
              <Play className="w-4 h-4" />
              初始化
            </button>
          </div>
        </div>
      </header>

      {/* 主体区域：左侧列表 + 右侧内容 */}
      <div className="flex h-[calc(100vh-73px)]">   {/* 高度=屏幕高度减去顶栏 */}
        {/* 左侧边栏 */}
        <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
          <div className="p-4 border-b border-slate-700">
            {/* 新建 NPC 按钮 */}
            <button
              onClick={handleCreateNew}
              className="w-full btn btn-primary flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              新建 NPC
            </button>
          </div>
          {/* NPC 列表 */}
          <div className="flex-1 overflow-auto p-2">
            <NpcList
              agents={agents}  // 传入数据：所有NPC
              selectedId={selectedAgentId} // 传入数据：当前选中谁
              onSelect={handleSelectAgent}  // 传出事件：选中某个 NPC 时调用
            />
          </div>

          {/* 分隔线 */}
          <hr className="border-slate-700 mx-2" />

          <div className="p-4 border-t border-slate-700">
            {/* 新建世界背景按钮 */}
            <button
              onClick={handleCreateWorld}
              className="w-full btn btn-primary flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              新建世界背景
            </button>
          </div>
          {/* 世界背景列表 */}
          <div className="flex-1 overflow-auto p-2">
            <WorldList
              worlds={worlds}
              selectedId={selectedWorldId}
              onSelect={handleSelectWorld}
            />
          </div>
        </aside>

        {/* 右侧边栏-主内容区 */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* 根据 activePanel 切换显示 */}
          {activePanel === 'npc' && (
            // 显示 NPC 配置面板
            config.id ? (
              <>
                {/* Tab 导航 */}
                <nav className="flex gap-1 px-4 pt-4 bg-slate-900">
                  {tabs.map(tab => (  // 遍历 tabs 数组，生成对应数量的按钮
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}  // 点击切换 tab
                      className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${activeTab === tab.id
                        ? 'bg-slate-800 text-blue-400 border-b-2 border-blue-500'  // 当前激活的tab-高亮样式
                        : 'text-slate-400 hover:text-slate-200' // 普通样式
                        }`}
                    >
                      <tab.icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  ))}
                </nav>
                {/* Tab 内容 */}
                <div className="flex-1 bg-slate-800 p-6 overflow-auto">
                  {activeTab === 'basic' && (  // 渲染基本信息组件
                    <BasicInfo config={config} onChange={updateConfig} />
                  )}
                  {activeTab === 'personality' && (  // 渲染人格设定组件
                    <PersonalityPanel config={config} onChange={updateConfig} worlds={worlds} />
                  )}
                  {activeTab === 'sensors' && (  // 渲染感官配置组件
                    <SensorPanel
                      value={config.sensors}
                      onChange={(newSensors) => updateConfig('sensors', newSensors)}
                    />
                  )}
                  {activeTab === 'actions' && (  // 渲染动作编辑组件
                    <ActionEditor
                      value={config.actions}
                      onChange={(newActions) => updateConfig('actions', newActions)}
                    />
                  )}
                  {activeTab === 'debug' && (  // 渲染调试组件
                    <DebugPanel
                      config={config}
                      connected={connected}
                      onInit={handleInit}
                    />
                  )}
                  {activeTab === 'database' && (  // 渲染数据库管理组件
                    <DatabasePanel selectedNpc={config} />
                  )}
                </div>
                {/* 底部操作栏 - NPC */}
                <footer className="bg-slate-800 border-t border-slate-700 px-6 py-4 flex items-center justify-between">
                  {/* 左侧：删除按钮 */}
                  <button
                    onClick={handleDelete}
                    className="btn btn-danger flex items-center gap-2"
                    disabled={!selectedAgentId}
                  >
                    <Trash2 className="w-4 h-4" />
                    删除
                  </button>
                  {/* 右侧：保存按钮 */}
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn btn-primary flex items-center gap-2"
                  >
                    {saving ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />  // 旋转动画
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    {saving ? '保存中...' : '保存配置'}
                  </button>
                </footer>
              </>
            ) : (
              // 如果没有选中任何 NPC（config.id 为空），显示这个空状态
              <div className="flex-1 flex items-center justify-center text-slate-500">
                <div className="text-center">
                  <Users className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>选择一个 NPC 或创建新的</p>
                </div>
              </div>
            )
          )}

          {activePanel === 'world' && (
            // 显示世界背景配置面板
            worldConfig.id ? (
              <>
                {/* 世界背景配置面板 */}
                <div className="flex-1 bg-slate-800 p-6 overflow-auto">
                  <WorldConfigPanel
                    config={worldConfig}
                    onChange={setWorldConfig}
                  />
                </div>
                {/* 底部操作栏 - 世界背景 */}
                <footer className="bg-slate-800 border-t border-slate-700 px-6 py-4 flex items-center justify-between">
                  {/* 左侧：删除按钮 */}
                  <button
                    onClick={handleDeleteWorld}
                    className="btn btn-danger flex items-center gap-2"
                    disabled={!selectedWorldId}
                  >
                    <Trash2 className="w-4 h-4" />
                    删除世界背景
                  </button>
                  {/* 右侧：保存按钮 */}
                  <button
                    onClick={handleSaveWorld}
                    disabled={saving}
                    className="btn btn-primary flex items-center gap-2"
                  >
                    {saving ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    {saving ? '保存中...' : '保存世界背景'}
                  </button>
                </footer>
              </>
            ) : (
              // 如果没有选中任何世界背景
              <div className="flex-1 flex items-center justify-center text-slate-500">
                <div className="text-center">
                  <Globe className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>选择一个世界背景或创建新的</p>
                </div>
              </div>
            )
          )}
        </main>
      </div>

      {/* Toast 临时提示（右下角弹出，3秒消失）*/}
      {toast && (
        // 错误→红色  成功→绿色   其他→蓝色（info）
        <div className={`fixed bottom-6 right-6 px-4 py-3 rounded-lg shadow-lg ${toast.type === 'error' ? 'bg-red-600' :
          toast.type === 'success' ? 'bg-green-600' : 'bg-blue-600'
          }`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
