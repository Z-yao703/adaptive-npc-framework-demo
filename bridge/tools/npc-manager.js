/**
 * NPCManager - NPC 管理器
 * 
 * 高级封装，用于管理多个 NPC 实例
 * 提供统一的 NPC 创建、销毁、状态管理
 * 
 * 使用示例：
 * ```javascript
 * import { NPCManager } from './npc-manager.js';
 * 
 * // 初始化
 * NPCManager.init({
 *     canvas: canvas,
 *     ctx: ctx,
 *     playerStateProvider: () => ({ x: player.x, y: player.y })
 * });
 * 
 * // 创建 NPC
 * NPCManager.createNPC('npc_001', {
 *     x: 500, y: 300,
 *     onAction: (action) => { }
 * });
 * 
 * // 游戏循环中更新
 * NPCManager.updateAll();
 * NPCManager.drawAll();
 * 
 * // 销毁所有 NPC
 * NPCManager.destroyAll();
 * ```
 */

import { AgentBridge } from '../core/agent_bridge.js';
import { NPCRender } from './npc-render.js';
import EventBus from './event-bus.js';

// =========================================
// 私有变量
// =========================================

const npcs = new Map();  // npcId -> npcInstance
let canvas = null;
let ctx = null;
let playerStateProvider = null;
let config = {
    defaultTickInterval: 350,
    defaultNearDistance: 80,
    autoLoadConfig: true
};

// =========================================
// 公开 API
// =========================================

/**
 * 初始化 NPCManager
 * @param {Object} options 配置选项
 * @param {HTMLCanvasElement} options.canvas Canvas 元素
 * @param {CanvasRenderingContext2D} options.ctx Canvas 2D Context
 * @param {Function} options.playerStateProvider 玩家状态提供者函数
 * @param {Object} [options.config] 额外配置
 */
function init(options) {
    if (!options.canvas || !options.ctx) {
        console.error('[NPCManager] 初始化失败: canvas 或 ctx 未提供');
        return;
    }

    canvas = options.canvas;
    ctx = options.ctx;
    playerStateProvider = options.playerStateProvider || (() => ({}));

    if (options.config) {
        Object.assign(config, options.config);
    }

    console.log('[NPCManager] 初始化完成');
}

/**
 * 创建 NPC
 * @param {string} npcId NPC ID
 * @param {Object} [options={}] NPC 配置选项
 * @param {number} [options.x] NPC X 坐标
 * @param {number} [options.y] NPC Y 坐标
 * @param {number} [options.width] NPC 宽度
 * @param {number} [options.height] NPC 高度
 * @param {string} [options.sprite] 精灵图路径
 * @param {number} [options.nearDistance] 对话触发距离
 * @param {number} [options.tickInterval] Tick 间隔（毫秒）
 * @param {Function} [options.onObserve] 自定义观察函数
 * @param {Function} [options.onAction] 自定义 Action 处理函数
 * @param {Function} [options.onConfigLoaded] 配置加载完成回调
 * @returns {Object} NPC 实例包装对象
 */
function createNPC(npcId, options = {}) {
    if (npcs.has(npcId)) {
        console.warn(`[NPCManager] NPC ${npcId} 已存在，将覆盖`);
        destroyNPC(npcId);
    }

    const npcInstance = {
        npcId,
        agentBridge: null,
        render: null,
        options: { ...options },
        createdAt: Date.now()
    };

    // 初始化渲染模块
    const renderOptions = {
        canvas: canvas,
        ctx: ctx,
        npcId: npcId,
        npcName: options.npcName || npcId,
        x: options.x || 500,
        y: options.y || 300,
        width: options.width || 48,
        height: options.height || 64,
        sprite: options.sprite || null,
        nearDistance: options.nearDistance || config.defaultNearDistance,
        tickInterval: options.tickInterval || config.defaultTickInterval,
        onObserve: options.onObserve || (() => playerStateProvider()),
        onAction: options.onAction || null,
        onConfigLoaded: (cfg) => {
            // 配置加载完成后，触发事件
            EventBus.emit('npc:config_loaded', { npcId, config: cfg });
            if (options.onConfigLoaded) {
                options.onConfigLoaded(cfg);
            }
        }
    };

    // 使用 NPCRender 初始化
    NPCRender.init(renderOptions);
    npcInstance.render = NPCRender;

    // 保存实例
    npcs.set(npcId, npcInstance);

    // 触发事件
    EventBus.emit('npc:created', { npcId, instance: npcInstance });

    console.log(`[NPCManager] NPC 创建成功: ${npcId}`);
    return npcInstance;
}

/**
 * 销毁 NPC
 * @param {string} npcId NPC ID
 * @returns {boolean} 是否成功销毁
 */
function destroyNPC(npcId) {
    const instance = npcs.get(npcId);
    if (!instance) {
        console.warn(`[NPCManager] NPC ${npcId} 不存在`);
        return false;
    }

    // 销毁渲染模块
    if (instance.render) {
        instance.render.destroy();
    }

    // 断开 AgentBridge 连接
    if (instance.agentBridge) {
        instance.agentBridge.disconnect();
    }

    // 从 Map 中移除
    npcs.delete(npcId);

    // 触发事件
    EventBus.emit('npc:destroyed', { npcId });

    console.log(`[NPCManager] NPC 已销毁: ${npcId}`);
    return true;
}

/**
 * 获取 NPC 实例
 * @param {string} npcId NPC ID
 * @returns {Object|undefined} NPC 实例
 */
function getNPC(npcId) {
    return npcs.get(npcId);
}

/**
 * 获取所有 NPC ID
 * @returns {string[]} NPC ID 数组
 */
function getAllNPCIds() {
    return Array.from(npcs.keys());
}

/**
 * 获取所有 NPC 实例
 * @returns {Object[]} NPC 实例数组
 */
function getAllNPCs() {
    return Array.from(npcs.values());
}

/**
 * 更新所有 NPC（在游戏循环中调用）
 */
function updateAll() {
    const playerState = playerStateProvider();
    npcs.forEach((instance, npcId) => {
        if (instance.render) {
            instance.render.update(playerState);
        }
    });
}

/**
 * 绘制所有 NPC（在游戏循环中调用）
 */
function drawAll() {
    npcs.forEach((instance, npcId) => {
        if (instance.render) {
            instance.render.draw();
        }
    });
}

/**
 * 向指定 NPC 发送消息
 * @param {string} npcId NPC ID
 * @param {string} message 消息内容
 * @returns {boolean} 是否成功发送
 */
function sendMessage(npcId, message) {
    const instance = npcs.get(npcId);
    if (!instance || !instance.render) {
        console.warn(`[NPCManager] NPC ${npcId} 不存在或未初始化`);
        return false;
    }

    instance.render.sendDialogue(message);
    return true;
}

/**
 * 向所有 NPC 广播消息（用于系统事件）
 * @param {Object} state 游戏状态
 */
function tickAll(state) {
    npcs.forEach((instance, npcId) => {
        if (instance.agentBridge) {
            instance.agentBridge.tick(state);
        }
    });
}

/**
 * 销毁所有 NPC
 */
function destroyAll() {
    const npcIds = Array.from(npcs.keys());
    npcIds.forEach(npcId => destroyNPC(npcId));
    console.log('[NPCManager] 所有 NPC 已销毁');
}

/**
 * 获取管理器状态
 * @returns {Object} 状态对象
 */
function getStatus() {
    return {
        npcCount: npcs.size,
        npcIds: getAllNPCIds(),
        config: { ...config }
    };
}

// =========================================
// NPCManager 对象 (统一导出)
// =========================================

const NPCManager = {
    init,
    createNPC,
    destroyNPC,
    getNPC,
    getAllNPCIds,
    getAllNPCs,
    updateAll,
    drawAll,
    sendMessage,
    tickAll,
    destroyAll,
    getStatus
};

// =========================================
// ES Module 导出
// =========================================

export { NPCManager, init, createNPC, destroyNPC, getNPC, getAllNPCIds, getAllNPCs, updateAll, drawAll, sendMessage, tickAll, destroyAll, getStatus };

export default NPCManager;
