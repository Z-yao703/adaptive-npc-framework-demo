/**
 * WebSocket 服务
 * 处理与后端的实时通信
 */

class WsService {
  constructor() {
    this.ws = null
    this.agentId = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
  }

  connect(agentId) {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/ws/${agentId}`
      
      console.log('Connecting to WebSocket:', wsUrl)
      
      this.ws = new WebSocket(wsUrl)
      this.agentId = agentId

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.send({ type: 'INIT', agent_id: agentId })
        resolve()
      }

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this._notifyListeners(data.type, data)
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        reject(error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this._handleReconnect()
      }
    })
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
      this.agentId = null
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  sendStateUpdate(state) {
    this.send({ type: 'STATE_UPDATE', state })
  }

  // ==================== 事件监听 ====================

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, [])
    }
    this.listeners.get(eventType).push(callback)
    
    // 返回取消订阅函数
    return () => {
      const callbacks = this.listeners.get(eventType)
      const index = callbacks.indexOf(callback)
      if (index > -1) callbacks.splice(index, 1)
    }
  }

  off(eventType, callback) {
    const callbacks = this.listeners.get(eventType)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) callbacks.splice(index, 1)
    }
  }

  _notifyListeners(eventType, data) {
    const callbacks = this.listeners.get(eventType) || []
    callbacks.forEach(cb => cb(data))
    
    // 触发通配符监听器
    const wildcardCallbacks = this.listeners.get('*') || []
    wildcardCallbacks.forEach(cb => cb(data))
  }

  // ==================== 重连 ====================

  _handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.agentId) {
      this.reconnectAttempts++
      console.log(`Reconnecting... attempt ${this.reconnectAttempts}`)
      setTimeout(() => {
        this.connect(this.agentId).catch(console.error)
      }, 1000 * this.reconnectAttempts)
    }
  }
}

// 单例导出
export const wsService = new WsService()
export default wsService
