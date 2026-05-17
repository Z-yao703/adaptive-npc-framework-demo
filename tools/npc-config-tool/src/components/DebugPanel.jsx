/**
 * 调试面板
 * 测试 NPC 配置，查看实时响应
 */

import React, { useState, useEffect } from 'react'
import { Settings, Play, RefreshCw, Send, Terminal, Wifi, WifiOff } from 'lucide-react'
import * as api from '../services/apiService'
import wsService from '../services/wsService'

export default function DebugPanel({ config, connected, onInit }) {
  const [testState, setTestState] = useState({
    player_position: { x: 100, y: 200 },
    player_inventory: ['apple', 'apple', 'sword'],
    distance_to_player: 50,
    weather: 'sunny',
    player_message: '你好'
  })
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState([])
  const [wsConnected, setWsConnected] = useState(false)

  // 监听 WebSocket 消息
  useEffect(() => {
    const unsubAction = wsService.on('ACTION', (data) => {
      setResponse(data.action)
      addLog('Received ACTION', data.action)
    })

    const unsubConfig = wsService.on('CONFIG_UPDATE', (data) => {
      addLog('Config hot-reload', data.config)
    })

    const unsubConnect = wsService.on('INIT_ACK', () => {
      setWsConnected(true)
      addLog('WebSocket', 'Connected to server')
    })

    return () => {
      unsubAction()
      unsubConfig()
      unsubConnect()
    }
  }, [])

  // 测试 API 调用
  const testApi = async () => {
    setLoading(true)
    setResponse(null)
    addLog('Sending state via API', testState)

    try {
      const result = await api.processState(config.id, testState)
      setResponse(result.action)
      addLog('API Response', result.action)
    } catch (err) {
      addLog('Error', err.message)
    } finally {
      setLoading(false)
    }
  }

  // 测试 WebSocket
  const testWebSocket = async () => {
    try {
      if (!wsConnected) {
        await wsService.connect(config.id)
      }
      wsService.sendStateUpdate(testState)
      addLog('WebSocket', 'State sent via WS')
    } catch (err) {
      addLog('WS Error', err.message)
    }
  }

  // 添加日志
  const addLog = (type, data) => {
    setLogs(prev => [{
      type,
      data,
      time: new Date().toLocaleTimeString()
    }, ...prev.slice(0, 49)])
  }

  // 清空日志
  const clearLogs = () => setLogs([])

  // 更新测试状态
  const updateTestState = (key, value) => {
    setTestState(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Settings className="w-5 h-5 text-slate-400" />
          调试面板
        </h2>
        <div className="flex items-center gap-2">
          {wsConnected ? (
            <span className="flex items-center gap-1 text-green-400 text-sm">
              <Wifi className="w-4 h-4" /> WebSocket 已连接
            </span>
          ) : (
            <span className="flex items-center gap-1 text-slate-500 text-sm">
              <WifiOff className="w-4 h-4" /> WebSocket 未连接
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 左侧：测试状态 */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-slate-400">测试状态数据</h3>

          <div className="panel p-4 space-y-3">
            <div>
              <label className="text-xs text-slate-500 block mb-1">玩家位置</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={testState.player_position.x}
                  onChange={(e) => updateTestState('player_position', {
                    ...testState.player_position,
                    x: parseInt(e.target.value)
                  })}
                  className="w-20 px-2 py-1 rounded text-sm"
                  placeholder="X"
                />
                <input
                  type="number"
                  value={testState.player_position.y}
                  onChange={(e) => updateTestState('player_position', {
                    ...testState.player_position,
                    y: parseInt(e.target.value)
                  })}
                  className="w-20 px-2 py-1 rounded text-sm"
                  placeholder="Y"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1">与玩家距离</label>
              <input
                type="number"
                value={testState.distance_to_player}
                onChange={(e) => updateTestState('distance_to_player', parseInt(e.target.value))}
                className="w-full px-2 py-1 rounded text-sm"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1">玩家背包 (逗号分隔)</label>
              <input
                type="text"
                value={testState.player_inventory.join(', ')}
                onChange={(e) => updateTestState('player_inventory',
                  e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                )}
                className="w-full px-2 py-1 rounded text-sm"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1">天气</label>
              <select
                value={testState.weather}
                onChange={(e) => updateTestState('weather', e.target.value)}
                className="w-full px-2 py-1 rounded text-sm"
              >
                <option value="sunny">晴天</option>
                <option value="rainy">雨天</option>
                <option value="snowy">雪天</option>
                <option value="foggy">雾天</option>
              </select>
            </div>
          </div>

          {/* 测试按钮 */}
          <div className="flex gap-2">
            <button
              onClick={testApi}
              disabled={loading || !config.id}
              className="btn btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              测试 API
            </button>
            <button
              onClick={testWebSocket}
              disabled={!config.id}
              className="btn btn-secondary flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />
              测试 WS
            </button>
          </div>
        </div>

        {/* 右侧：响应结果 */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-slate-400">NPC 响应</h3>

          {response ? (
            <div className="panel p-4">
              <pre className="text-sm text-green-400 overflow-auto">
                {JSON.stringify(response, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="panel p-4 text-center text-slate-500">
              点击上方按钮发送测试数据
            </div>
          )}
        </div>
      </div>

      {/* 日志面板 */}
      <div className="panel overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium">运行日志</span>
            <span className="text-xs text-slate-500">{logs.length} 条</span>
          </div>
          <button onClick={clearLogs} className="text-xs text-slate-500 hover:text-white">
            清空
          </button>
        </div>
        <div className="h-48 overflow-auto p-2 font-mono text-xs">
          {logs.map((log, i) => (
            <div key={i} className="py-1 border-b border-slate-800">
              <span className="text-slate-500">[{log.time}]</span>
              <span className="text-blue-400 ml-2">{log.type}:</span>
              <span className="text-slate-300 ml-2">
                {typeof log.data === 'object'
                  ? JSON.stringify(log.data).substring(0, 100) + '...'
                  : String(log.data)
                }
              </span>
            </div>
          ))}
          {!logs.length && (
            <div className="text-center text-slate-600 py-8">
              暂无日志
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
