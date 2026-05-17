/**
 * Protocol - NPC 框架通信协议定义
 * 
 * 此文件由 generate_protocols.py 自动生成
 * 源文件: protocol.yaml
 * 生成时间: 2026-05-01 15:50:22
 * 版本: 2.0.0
 * 
 * 定义前后端通信的标准消息格式和 Action 类型
 * 这是框架的"契约层"，确保前后端对协议的理解一致
 */

// =========================================
// 消息类型定义 (Message Types)
// =========================================

/**
 * 前端 → 后端 消息类型
 */
export const ClientMessageType = {
    STATE_UPDATE: 'STATE_UPDATE',   // 游戏状态更新消息
};

/**
 * 后端 → 前端 消息类型
 */
export const ServerMessageType = {
    ACTIONS: 'ACTIONS',   // Action列表消息
    PONG: 'PONG',   // 心跳响应
    CONFIG_UPDATE: 'CONFIG_UPDATE',   // 配置热更新
};

/**
 * 所有消息类型集合
 */
export const MessageType = {
    ...ClientMessageType,
    ...ServerMessageType
};

// =========================================
// Action 类型定义 (Action Types)
// =========================================

/**
 * 标准 Action 类型
 * 
 * 分类：
 * - 对话类：NPC_SAY, NPC_EMOTE
 * - 移动类：MOVE_TO, NPC_STOP, FOLLOW
 * - 交互类：START_TRADE, GIVE_ITEM, TAKE_ITEM
 * - 任务类：START_QUEST, UPDATE_QUEST, COMPLETE_QUEST
 * - 系统类：ERROR, CONFIG_UPDATE
 */
export const ActionType = {
    COMPLETE_QUEST: 'COMPLETE_QUEST',   // 完成任务
    CONFIG_UPDATE: 'CONFIG_UPDATE',   // 配置热更新
    ERROR: 'ERROR',   // 错误信息
    FOLLOW: 'FOLLOW',   // NPC跟随目标
    GIVE_ITEM: 'GIVE_ITEM',   // NPC给予物品
    MOVE_TO: 'MOVE_TO',   // NPC移动到目标位置
    NPC_EMOTE: 'NPC_EMOTE',   // NPC表情动作
    NPC_SAY: 'NPC_SAY',   // NPC说话/显示对话气泡
    NPC_STOP: 'NPC_STOP',   // NPC停止移动
    START_QUEST: 'START_QUEST',   // 开始新任务
    START_TRADE: 'START_TRADE',   // 打开交易界面
    TAKE_ITEM: 'TAKE_ITEM',   // NPC拿走物品
    UPDATE_QUEST: 'UPDATE_QUEST',   // 更新任务进度
};

// =========================================
// Action 参数定义 (Action Params)
// =========================================

/**
 * NPC说话Action的参数
 */
export const NPC_SAYParams = {
    npc_id: String,   // NPC的唯一标识符
    text: String,   // NPC要说的文本内容
    emotion: String,   // NPC说话时的情绪（默认: neutral）
};

/**
 * NPC表情动作参数
 */
export const NPC_EMOTEParams = {
    npc_id: String,   // NPC的唯一标识符
    emotion: String,   // 表情类型
    duration: Number,   // 动作持续时间（毫秒）（默认: 2000）
};

/**
 * NPC移动参数
 */
export const MOVE_TOParams = {
    npc_id: String,   // NPC的唯一标识符
    x: Number,   // 目标位置的X坐标
    y: Number,   // 目标位置的Y坐标
    speed: Number,   // 移动速度（像素/帧）（默认: 3.0）
};

/**
 * NPC跟随参数
 */
export const FOLLOWParams = {
    npc_id: String,   // NPC的唯一标识符
    target_id: String,   // 要跟随的目标标识（玩家或其他NPC）
    distance: Number,   // 跟随距离（像素）（默认: 50.0）
};

// =========================================
// 事件类型定义 (Event Types)
// =========================================

/**
 * 游戏事件类型
 */
export const GameEventType = {
    PLAYER_NEAR: 'player_near',   // 玩家靠近NPC
    PLAYER_FAR: 'player_far',   // 玩家远离NPC
    DIALOGUE_START: 'dialogue_start',   // 对话开始
    DIALOGUE_END: 'dialogue_end',   // 对话结束
    NPC_CLICKED: 'npc_clicked',   // NPC被玩家点击
    STATE_CHANGED: 'state_changed',   // 游戏状态改变
};

// =========================================
// 验证工具函数
// =========================================

/**
 * 验证消息格式是否正确
 * @param {Object} msg 消息对象
 * @returns {boolean} 是否有效
 */
export function validateMessage(msg) {
    if (!msg || typeof msg !== 'object') return false;
    if (!msg.type || typeof msg.type !== 'string') return false;

    // 检查类型是否已知
    const allTypes = { ...MessageType };
    if (!Object.values(allTypes).includes(msg.type)) {
        console.warn(`[Protocol] Unknown message type: ${msg.type}`);
    }

    return true;
}

/**
 * 验证 Action 格式是否正确
 * @param {Object} action Action 对象
 * @returns {boolean} 是否有效
 */
export function validateAction(action) {
    if (!action || typeof action !== 'object') return false;
    if (!action.type || typeof action.type !== 'string') return false;

    // 检查类型是否已知
    if (!Object.values(ActionType).includes(action.type)) {
        console.warn(`[Protocol] Unknown action type: ${action.type}`);
        return false;
    }

    return true;
}

/**
 * 创建标准消息
 * @param {string} type 消息类型
 * @param {Object} payload 消息负载
 * @returns {Object} 标准消息对象
 */
export function createMessage(type, payload = {}) {
    return {
        type,
        ...payload,
        timestamp: Date.now()
    };
}

/**
 * 创建标准 Action
 * @param {string} type Action 类型
 * @param {Object} params Action 参数
 * @returns {Object} 标准 Action 对象
 */
export function createAction(type, params = {}) {
    return {
        type,
        params
    };
}

// =========================================
// 默认导出
// =========================================

export default {
    MessageType,
    ClientMessageType,
    ServerMessageType,
    ActionType,
    GameEventType,
    validateMessage,
    validateAction,
    createMessage,
    createAction
};