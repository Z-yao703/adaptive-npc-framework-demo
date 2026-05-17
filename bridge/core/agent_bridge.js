/**
 * AgentBridge - NPC 框架前端 SDK
 * 
 * 设计原则：
 * - 回调驱动，不与任何游戏引擎耦合
 * - 游戏开发者只需提供 observe() 和 onAction() 两个函数
 * - 所有 Action 路由由开发者自己决定
 * 
 * 使用示例：
 * ```javascript
 * const agent = new AgentBridge({
 *     agentId: "village_chief",
 *     observe: () => ({
 *         player: { x: player.x, y: player.y },
 *         inventory: player.items
 *     }),
 *     onAction: (action) => {
 *         switch (action.type) {
 *             case "NPC_SAY":
 *                 ui.showBubble(action.params.npc_id, action.params.text);
 *                 break;
 *             case "MOVE_TO":
 *                 gameScene.moveNPC(action.params);
 *                 break;
 *         }
 *     }
 * });
 * 
 * // 在游戏循环中定期更新状态
 * game.events.on('update', () => {
 *     agent.tick();
 * });
 * ```
 */

// =========================================
// 与单个 NPC 实例的生命周期和状态强相关
// =========================================
class AgentBridge {
    // @param {参数类型} 参数名 参数说明
    /**
     * @param {Object} config 配置对象
     * @param {string} config.agentId NPC 标识符
     * @param {Function} config.observe 状态观察函数，返回当前游戏状态
     * @param {Function} config.onAction Action 执行回调
     * @param {string} [config.serverUrl] 服务器地址，默认使用当前页面地址
     */

    // ============处理 WebSocket 连接的建立和接收服务器消息（被动响应）==============
    /**
     * AgentBridge 类构造函数 => _connect()
     */
    constructor(config) {
        this.agentId = config.agentId;
        this.observe = config.observe || (() => ({})); // 游戏 → 服务器 定义感知的权利交给开发者
        this.onAction = config.onAction || ((action) => {
            console.warn('[AgentBridge] No action handler configured:', action);
        }); // 服务器 → 游戏 有限类型的动作 框架进行标准化实现
        // 拼接获得完整的 WebSocket 服务器地址
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const defaultPath = this.agentId ? `/ws/${encodeURIComponent(this.agentId)}` : '/ws';
        this.serverUrl = config.serverUrl || `${protocol}//${window.location.host}${defaultPath}`;
        // 初始化连接状态并开始连接
        this.socket = null;
        this.isConnected = false;
        this.messageQueue = [];
        this._intentionalClose = false;
        this._connect();
    }
    /**
     * 建立 WebSocket 连接（onopen/onmessage =>  _handleMessage(msg)/onerror/onclose）
     */
    _connect() {
        this.socket = new WebSocket(this.serverUrl);
        // WebSocket 事件监听器，由浏览器在特定时机自动调用
        // 监听 连接成功
        this.socket.onopen = () => {
            this.isConnected = true;
            console.log(`AgentBridge connected: ${this.agentId}`);
            while (this.messageQueue.length > 0) {
                const msg = this.messageQueue.shift(); // 按顺序取出队列中的消息
                this.socket.send(JSON.stringify(msg)); // 序列化，对象 → JSON 字符串（用于发送）
            }
        };
        // 监听 收到消息
        this.socket.onmessage = (event) => {
            const msg = JSON.parse(event.data); // 反序列化，JSON 字符串 → 对象（用于接收）
            console.log('AgentBridge received:', msg.type, msg);
            this._handleMessage(msg);
        };
        // 监听 出错
        this.socket.onerror = (error) => {
            console.error(`AgentBridge error: ${this.agentId}`, error);
        };
        // 监听 连接关闭
        this.socket.onclose = () => {
            this.isConnected = false;
            console.log(`AgentBridge disconnected: ${this.agentId}`);
            if (this._intentionalClose) {
                console.log(`AgentBridge ${this.agentId} 主动断开，不重连`);
                return;
            }
            setTimeout(() => {
                console.log(`Reconnecting: ${this.agentId}...`);
                this._connect();
            }, 3000);
        };
    }
    /**
     * 处理收到的消息（INIT_ACK/ACTIONS/PONG）
     */
    _handleMessage(msg) {
        switch (msg.type) {
            case 'INIT_ACK':
                // INITialization ACKnowledgement，初始化确认 = NPC 已就位
                console.log(`Agent initialized: ${msg.agent_id}`);
                break;
            case 'ACTIONS':
                // 标准 Action 列表，逐个执行 = NPC 要执行这些动作
                if (msg.actions && Array.isArray(msg.actions)) {
                    // forEach 遍历数组，把每个 action 交给 this.onAction(action) 处理
                    msg.actions.forEach(action => this.onAction(action));
                }
                break;
            case 'PONG':
                // 心跳响应 = 连接保持
                break;
            default:
                console.warn('[AgentBridge] Unknown message type:', msg.type);
        }
    }

    // ============================================================================
    /**
     * 发送游戏状态更新（通常在游戏循环中调用）=> _send(msg)
     * @param {Object} [state] 可选的手动状态，否则使用 observe() 获取
     */
    tick(state) {
        const gameState = state || this.observe();
        if (!gameState.player_id) {
            gameState.player_id = this.agentId + '_player';
        }
        this._send({
            type: 'STATE_UPDATE',
            state: gameState
        });
    }
    /**
     * 发送消息到服务器(send/messageQueue)
     */
    _send(msg) {
        if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
            // 已连接且 WebSocket 连接为“打开”状态 立即通过 WebSocket 发送消息
            this.socket.send(JSON.stringify(msg));
        } else {
            // 未连接或连接未打开，将消息加入队列等待
            this.messageQueue.push(msg);
        }
    }

    /**
     * @deprecated 请使用 REST API 获取配置，或监听 CONFIG_UPDATE 动作实现热更新
     * @see GET /api/agent/{agentId}
     */
    getConfig() {
        console.warn('[AgentBridge] getConfig() 已废弃，请使用 REST API /api/agent/{agentId} 获取配置');
    }

    /**
     * 断开连接
     */
    disconnect() {
        this._intentionalClose = true;
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

// ========================================
// 提供标准 Action 的默认处理逻辑
// ====================================

/**
 * 标准的 Action 路由函数
 * 发者可以完全不用 routeAction，自己实现 onAction 回调；
 * 也可以以 routeAction 为基础，扩展自定义的 Action 类型
 * 
 * 在创建 AgentBridge 时，将 routeAction 作为 onAction 的回调
 * const agent = new AgentBridge({
 *   agentId: 'npc1',
 *   observe: () => ({ ... }),
 *   onAction: (action) => routeAction(action, {
 *      gameScene: window.myGameEngine,
 *      uiManager: window.ui
 *   })
 * });
 * @param {Object} action 标准 Action 对象
 * @param {Object} handlers 自定义处理器
 * 使用示例：
 * ```javascript
 * routeAction(action, {
 *     gameScene: window.gameScene,
 *     uiManager: window.uiManager,
 *     inventory: player.inventory
 * });
 * ```
 */
function routeAction(action, handlers = {}) {
    const { type, params } = action;
    switch (type) {
        // ===== 对话类 =====
        case 'NPC_SAY':
            // 显示对话气泡
            if (handlers.uiManager?.showBubble) {
                handlers.uiManager.showBubble(params.npc_id, params.text, params.emotion);
            } else {
                console.log(`💬 [${params.npc_id}]: ${params.text}`);
            }
            break;

        case 'NPC_EMOTE':
            // 播放表情动画
            if (handlers.gameScene?.playEmote) {
                handlers.gameScene.playEmote(params.npc_id, params.emotion, params.duration);
            }
            break;
        // ===== 移动类 =====
        case 'MOVE_TO':
            // NPC 移动到目标位置
            if (handlers.gameScene?.moveNPC) {
                handlers.gameScene.moveNPC(params.npc_id, params.x, params.y, params.speed);
            }
            break;
        case 'NPC_STOP':
            // NPC 停止移动
            if (handlers.gameScene?.stopNPC) {
                handlers.gameScene.stopNPC(params.npc_id);
            }
            break;
        case 'FOLLOW':
            // NPC 跟随目标
            if (handlers.gameScene?.followTarget) {
                handlers.gameScene.followTarget(params.npc_id, params.target_id, params.distance);
            }
            break;
        // ===== 交互类 =====
        case 'START_TRADE':
            // 打开交易界面
            if (handlers.uiManager?.showTrade) {
                handlers.uiManager.showTrade(params.npc_id, params.items);
            }
            break;
        case 'GIVE_ITEM':
            // NPC 给予物品
            if (handlers.inventory?.addItem) {
                handlers.inventory.addItem(params.item, params.quantity);
                console.log(`🎁 [${params.npc_id}] 给了你 ${params.quantity}x ${params.item}`);
            }
            break;
        case 'TAKE_ITEM':
            // NPC 拿走物品
            if (handlers.inventory?.removeItem) {
                handlers.inventory.removeItem(params.item, params.quantity);
                console.log(`📦 [${params.npc_id}] 取走了你 ${params.quantity}x ${params.item}`);
            }
            break;
        // ===== 任务类 =====
        case 'START_QUEST':
            // 开始任务
            if (handlers.questManager?.startQuest) {
                handlers.questManager.startQuest(params.quest_id, params.title, params.description);
            }
            break;
        case 'UPDATE_QUEST':
            // 更新任务进度
            if (handlers.questManager?.updateQuest) {
                handlers.questManager.updateQuest(params.quest_id, params.progress);
            }
            break;
        case 'COMPLETE_QUEST':
            // 完成任务
            if (handlers.questManager?.completeQuest) {
                handlers.questManager.completeQuest(params.quest_id, params.rewards);
            }
            break;
        // ===== 系统类 =====
        case 'ERROR':
            console.error(`❌ [${params.npc_id || 'System'}]: ${params.message}`);
            break;
        case 'CONFIG_UPDATE':
            // 配置热更新
            if (handlers.onConfigUpdate) {
                handlers.onConfigUpdate(params);
            }
            break;
        default:
            console.warn('[AgentBridge] Unknown action type:', type);
    }
}


// ES Module 导出
export { AgentBridge, routeAction };
// 可选：默认导出
export default AgentBridge;

// DEBUG: 开发模式下保留全局挂载（可选，便于调试）
// if (typeof process !== 'undefined' && process.env.NODE_ENV === 'development') {
//     if (typeof window !== 'undefined') {
//         window.AgentBridgeDev = AgentBridge;
//         console.log('[DEV] AgentBridge 开发模式全局挂载可用');
//     }
// }