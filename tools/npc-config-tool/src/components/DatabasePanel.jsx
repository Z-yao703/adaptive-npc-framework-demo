// 数据库管理面板
// 用于管理 NPC 短期记忆数据库

import React, { useState, useEffect } from 'react'
import { 
  Database, Trash2, Eye, Download, RefreshCw, 
  BarChart3, MessageSquare, X, Check
} from 'lucide-react'

const DatabasePanel = ({ selectedNpc }) => {
  const [memoryStats, setMemoryStats] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const [confirmClear, setConfirmClear] = useState(false)

  // 获取记忆统计
  const fetchMemoryStats = async () => {
    if (!selectedNpc?.id) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(
        `http://localhost:8000/api/short_term_memory/${selectedNpc.id}?limit=100`
      )
      
      if (response.ok) {
        const data = await response.json()
        setMemoryStats(data.stats)
        setHistory(data.history || [])
      } else {
        throw new Error('获取记忆失败')
      }
    } catch (err) {
      console.error('获取记忆统计失败:', err)
      setError('获取记忆失败，可能服务未启动')
    } finally {
      setLoading(false)
    }
  }

  // 清除记忆
  const handleClearMemory = async () => {
    if (!selectedNpc?.id) return
    
    if (!confirmClear) {
      setConfirmClear(true)
      return
    }

    setLoading(true)
    try {
      const response = await fetch(
        `http://localhost:8000/api/short_term_memory/${selectedNpc.id}`,
        { method: 'DELETE' }
      )

      if (response.ok) {
        alert('记忆已清除！')
        setConfirmClear(false)
        fetchMemoryStats()
      } else {
        throw new Error('清除失败')
      }
    } catch (err) {
      console.error('清除记忆失败:', err)
      alert('清除失败')
    } finally {
      setLoading(false)
    }
  }

  // 导出记忆
  const handleExportMemory = () => {
    if (!history.length) {
      alert('没有可导出的记忆')
      return
    }

    const exportData = {
      npc_id: selectedNpc.id,
      npc_name: selectedNpc.name || selectedNpc.meta?.name,
      export_time: new Date().toISOString(),
      stats: memoryStats,
      history: history
    }

    const blob = new Blob(
      [JSON.stringify(exportData, null, 2)],
      { type: 'application/json' }
    )
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `memory_${selectedNpc.id}_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // 组件加载时获取数据
  useEffect(() => {
    if (selectedNpc?.id) {
      fetchMemoryStats()
    }
  }, [selectedNpc])

  if (!selectedNpc?.id) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <Database size={48} style={{ opacity: 0.3 }} />
          <p>请先选择一个 NPC</p>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {/* 标题栏 */}
      <div style={styles.header}>
        <Database size={20} />
        <span>数据库管理</span>
        <button 
          style={styles.refreshBtn}
          onClick={fetchMemoryStats}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={styles.error}>
          {error}
        </div>
      )}

      {/* 统计卡片 */}
      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <BarChart3 size={24} style={{ color: '#4cc9f0' }} />
          <div style={styles.statContent}>
            <div style={styles.statValue}>{memoryStats?.total_entries || 0}</div>
            <div style={styles.statLabel}>总对话数</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <Users size={24} style={{ color: '#f472b6' }} />
          <div style={styles.statContent}>
            <div style={styles.statValue}>{memoryStats?.unique_players || 0}</div>
            <div style={styles.statLabel}>互动玩家</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <MessageSquare size={24} style={{ color: '#a78bfa' }} />
          <div style={styles.statContent}>
            <div style={styles.statValue}>{memoryStats?.max_round || 0}</div>
            <div style={styles.statLabel}>最大轮数</div>
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div style={styles.actions}>
        <button 
          style={styles.actionBtn}
          onClick={() => setShowHistory(!showHistory)}
        >
          <Eye size={16} />
          {showHistory ? '隐藏历史' : '查看历史'}
        </button>

        <button 
          style={styles.actionBtn}
          onClick={handleExportMemory}
        >
          <Download size={16} />
          导出数据
        </button>

        <button 
          style={{
            ...styles.actionBtn,
            ...(confirmClear ? styles.confirmBtn : styles.dangerBtn)
          }}
          onClick={handleClearMemory}
          onMouseLeave={() => setConfirmClear(false)}
        >
          <Trash2 size={16} />
          {confirmClear ? '确认清空?' : '清空记忆'}
        </button>
      </div>

      {/* 历史记录 */}
      {showHistory && (
        <div style={styles.historyContainer}>
          <div style={styles.historyTitle}>
            对话历史（最近 {history.length} 条）
          </div>
          
          <div style={styles.historyList}>
            {history.length === 0 ? (
              <div style={styles.emptyHistory}>暂无对话记录</div>
            ) : (
              history.map((chat, index) => (
                <div key={index} style={styles.historyItem}>
                  <div style={styles.roundBadge}>第 {chat.round} 轮</div>
                  
                  <div style={styles.chatPair}>
                    <div style={styles.playerMsg}>
                      <span style={styles.speakerLabel}>玩家：</span>
                      {chat.player_message || '(无消息)'}
                    </div>
                    
                    <div style={styles.npcMsg}>
                      <span style={styles.speakerLabel}>NPC：</span>
                      {chat.npc_response || '(等待回复)'}
                    </div>
                  </div>
                  
                  <div style={styles.timestamp}>
                    {new Date(chat.timestamp).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* 提示信息 */}
      <div style={styles.tips}>
        <p>💡 提示：数据库会在玩家首次对话时自动创建</p>
        <p>💡 每个 NPC 的对话记忆完全隔离，互不影响</p>
      </div>
    </div>
  )
}

// 样式
const styles = {
  container: {
    padding: '16px',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    overflow: 'auto'
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#e2e8f0'
  },
  refreshBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    padding: '4px',
    borderRadius: '4px'
  },
  error: {
    padding: '12px',
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '8px',
    color: '#fca5a5',
    fontSize: '14px'
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    color: '#64748b'
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px'
  },
  statCard: {
    background: 'rgba(30, 41, 59, 0.8)',
    borderRadius: '12px',
    padding: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    border: '1px solid rgba(75, 201, 240, 0.2)'
  },
  statContent: {
    display: 'flex',
    flexDirection: 'column'
  },
  statValue: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#e2e8f0'
  },
  statLabel: {
    fontSize: '12px',
    color: '#94a3b8'
  },
  actions: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap'
  },
  actionBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    background: 'rgba(75, 201, 240, 0.1)',
    border: '1px solid rgba(75, 201, 240, 0.3)',
    borderRadius: '8px',
    color: '#4cc9f0',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  dangerBtn: {
    background: 'rgba(239, 68, 68, 0.1)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    color: '#f87171'
  },
  confirmBtn: {
    background: 'rgba(239, 68, 68, 0.3)',
    borderColor: '#f87171',
    color: '#fff',
    fontWeight: 'bold'
  },
  historyContainer: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(30, 41, 59, 0.5)',
    borderRadius: '12px',
    border: '1px solid rgba(75, 201, 240, 0.2)',
    overflow: 'hidden'
  },
  historyTitle: {
    padding: '12px 16px',
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#e2e8f0',
    borderBottom: '1px solid rgba(75, 201, 240, 0.1)'
  },
  historyList: {
    flex: 1,
    overflow: 'auto',
    padding: '12px'
  },
  emptyHistory: {
    padding: '32px',
    textAlign: 'center',
    color: '#64748b'
  },
  historyItem: {
    marginBottom: '16px',
    padding: '12px',
    background: 'rgba(15, 23, 42, 0.8)',
    borderRadius: '8px',
    border: '1px solid rgba(75, 201, 240, 0.1)'
  },
  roundBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    background: 'rgba(75, 201, 240, 0.2)',
    borderRadius: '4px',
    fontSize: '12px',
    color: '#4cc9f0',
    marginBottom: '8px'
  },
  chatPair: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '8px'
  },
  playerMsg: {
    fontSize: '14px',
    color: '#93c5fd'
  },
  npcMsg: {
    fontSize: '14px',
    color: '#e5eefc'
  },
  speakerLabel: {
    fontWeight: 'bold',
    marginRight: '4px'
  },
  timestamp: {
    fontSize: '11px',
    color: '#64748b'
  },
  tips: {
    padding: '12px',
    background: 'rgba(75, 201, 240, 0.05)',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#94a3b8'
  }
}

// Users 图标需要从 lucide-react 导入
import { Users } from 'lucide-react'

export default DatabasePanel
