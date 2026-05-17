/**
 * NPC 渲染模块 - 可独立使用的 NPC 渲染模板
 * 
 * 【ES Module 版本】
 * 使用方法：
 * 1. 在游戏 JS 中 import { NPCRender } from './npc-render.js';
 * 2. 在游戏循环中调用 NPCRender.update() 和 NPCRender.draw()
 * 3. 只需关注你的游戏逻辑，NPC 渲染交给此模块
 * 
 * 示例：
 * ```javascript
 * import { NPCRender } from './npc-render.js';
 * // 初始化: NPCRender.init({...});
 * // 更新: NPCRender.update();
 * // 绘制: NPCRender.draw();
 * ```
 */
import { AgentBridge } from '../core/agent_bridge.js';


// ===== 私有变量 =====
let canvas, ctx;
let npcId = 'default_npc';
let npcName = 'NPC';
let npc = {
    x: 500, y: 300,
    width: 48, height: 64,
    scale: 1,
    sprite: null,
    spriteLoaded: false,
    // 移动
    targetX: 0, targetY: 0,
    speed: 2,
    // 表情
    emote: null,
    emoteUntil: 0,
    // 动画
    frame: 0,
    frameCount: 4,
    frameTimer: 0,
    isMoving: false,
    facingDirection: 'down'
};
let npcConfig = null;
let agentBridge = null;
let pendingDialogue = null;
let nearDistance = 20;  // 对话触发距离
let tickInterval = 350;
let tickTimer = null;
let playerNearLastTick = false;

// 对话相关
let chatHistory = [];  // 对话历史，最多3条
let isChatOpen = false;
let chatUI = null;

// 配置加载完成回调
let onConfigLoaded = null;
let configLoaded = false;

// 表情映射
const EMOTE_MAP = {
    wave: '👋', nod: '👍', happy: '😊', angry: '😠',
    think: '🤔', greet: '🙋', satisfied: '😌'
};

// ===== 公开 API =====
function init(options) {
    // 防御性检查：验证 canvas 和 ctx
    if (!options.canvas) {
        console.error('[NPCRender] 初始化失败: canvas 未提供');
        return;
    }
    if (!options.ctx) {
        console.error('[NPCRender] 初始化失败: ctx 未提供');
        return;
    }

    canvas = options.canvas;
    ctx = options.ctx;
    npcId = options.npcId || 'default_npc';
    npcName = options.npcName || 'NPC';
    npc.x = options.x || 500;
    npc.y = options.y || 300;
    npc.targetX = npc.x;
    npc.targetY = npc.y;
    npc.width = options.width || 48;
    npc.height = options.height || 64;
    nearDistance = options.nearDistance || 20;
    tickInterval = options.tickInterval || 350;

    // 【新增】配置加载完成回调
    onConfigLoaded = options.onConfigLoaded || null;

    // 加载精灵图
    if (options.sprite) {
        loadSprite(options.sprite);
    }

    // 加载 NPC 配置（异步）
    loadNpcConfig();

    // 初始化 AgentBridge （已通过 import 引入）
    initAgentBridge(options.onObserve, options.onAction);
    // 提示：AgentBridge 缺失请检查 import 路径

    console.log('[NPCRender] 初始化完成，NPC ID:', npcId);
}

function update(playerState) {
    updateNpcMovement();
    updateNpcAnimation();

    if (playerState && agentBridge && tickTimer === null) {
        startAutoTick(playerState);
    }
}

function draw() {
    // 防御性检查：确保 canvas 和 ctx 已初始化
    if (!canvas || !ctx) {
        console.warn('[NPCRender] Canvas 或 Context 未初始化，跳过绘制');
        return;
    }
    drawNpc();
    drawEmote();
    drawTalkButton();
}

function handleAction(action) {
    switch (action.type) {
        case 'NPC_SAY':
            const text = action.params?.text || action.params?.message || '...';
            // 添加到对话框历史
            addToChatHistory(npcName, text);
            break;
        case 'MOVE_TO':
            const target = action.params?.target || action.params || {};
            npc.targetX = target.x ?? npc.x;
            npc.targetY = target.y ?? npc.y;
            npc.speed = Math.max(0.5, (action.params?.speed || 60) / 30);
            break;
        case 'NPC_EMOTE':
            npc.emote = action.params?.emotion || 'wave';
            npc.emoteUntil = Date.now() + (action.params?.duration || 2000);
            break;
        case 'NPC_STOP':
            npc.targetX = npc.x;
            npc.targetY = npc.y;
            break;
    }
}

function getPosition() {
    return { x: npc.x, y: npc.y };
}

function getSize() {
    return { width: npc.width, height: npc.height };
}

function setPosition(x, y) {
    npc.x = x;
    npc.y = y;
    npc.targetX = x;
    npc.targetY = y;
    console.log('[NPCRender] 位置已更新:', x, y);
}

function distanceToPlayer(playerPos) {
    const dx = playerPos.x - npc.x;
    const dy = playerPos.y - npc.y;
    return Math.sqrt(dx * dx + dy * dy);
}

function sendDialogue(message) {
    if (!message || !message.trim()) return;
    const msgToSend = message.trim();
    pendingDialogue = msgToSend;
    // 添加玩家消息到历史
    addToChatHistory('玩家', msgToSend);
    // 打开对话框
    openChatDialog();
    // 立即触发一次 tick，发送消息到后端
    if (agentBridge) {
        const state = {
            player_position: { x: npc.x, y: npc.y },
            npc_position: { x: npc.x, y: npc.y },
            event: 'dialogue',
            player_message: msgToSend,
            timestamp: Date.now()
        };
        agentBridge.tick(state);
        console.log('[NPCRender] 已发送对话:', msgToSend);
    }
    // 立即清除，避免重复发送
    pendingDialogue = null;
}

function tick(state) {
    if (agentBridge) {
        agentBridge.tick(state);
    }
}

function isConnected() {
    return agentBridge ? agentBridge.isConnected : false;
}

function destroy() {
    if (tickTimer) {
        clearInterval(tickTimer);
        tickTimer = null;
    }
    if (agentBridge) {
        agentBridge.disconnect();
    }
    closeChatDialog();
}

// ===== 私有方法 =====

function loadSprite(src) {
    npc.sprite = new Image();
    npc.spriteLoaded = false;
    npc.sprite.onload = () => {
        npc.spriteLoaded = true;
        console.log('[NPCRender] 精灵图加载完成:', src);
    };
    npc.sprite.onerror = () => {
        console.warn('[NPCRender] 精灵图加载失败:', src, '使用默认颜色块');
        npc.spriteLoaded = false;
    };
    npc.sprite.src = src;
}

async function loadNpcConfig() {
    try {
        const serverUrl = getServerBaseUrl();
        const apiUrl = `${serverUrl}/api/agent/${encodeURIComponent(npcId)}`;
        console.log('[NPCRender] 请求配置 API:', apiUrl);

        const res = await fetch(apiUrl);
        console.log('[NPCRender] API 响应状态:', res.status);

        if (res.ok) {
            const config = await res.json();
            console.log('[NPCRender] 原始配置:', JSON.stringify(config, null, 2));

            npcConfig = config;

            // 从配置读取 NPC 名称
            npcName = config.meta?.name || config.name || 'NPC';
            console.log('[NPCRender] NPC 名称:', npcName);

            // 【修复】从配置读取 sprite，优先使用配置的 sprite
            const spritePath = config.presentation?.sprite || config.sprite;
            console.log('[NPCRender] 精灵图路径:', spritePath);

            if (spritePath) {
                // 构建完整的精灵图 URL
                const spriteUrl = spritePath.startsWith('http')
                    ? spritePath
                    : `${serverUrl}${spritePath}`;
                console.log('[NPCRender] 完整精灵图 URL:', spriteUrl);

                // 重新加载精灵图
                loadSprite(spriteUrl);
            } else {
                console.log('[NPCRender] 无精灵图，使用默认颜色块');
            }

            // 从配置读取尺寸
            const renderCfg = config.presentation?.render_cfg || config.render_cfg || {};
            npc.width = renderCfg.frameWidth || npc.width;
            npc.height = renderCfg.frameHeight || npc.height;
            npc.scale = renderCfg.scale || 1;

            console.log('[NPCRender] NPC 尺寸:', npc.width, 'x', npc.height, '缩放:', npc.scale);

            // 标记配置加载完成
            configLoaded = true;

            // 调用配置加载完成回调
            if (onConfigLoaded) {
                onConfigLoaded({
                    name: npcName,
                    spritePath: spritePath,
                    sprite: npc.sprite,
                    spriteLoaded: npc.spriteLoaded,
                    width: npc.width,
                    height: npc.height,
                    scale: npc.scale,
                    config: config
                });
            }

            console.log('[NPCRender] 配置加载完成!');
        } else {
            console.warn('[NPCRender] NPC 配置加载失败，状态:', res.status);
        }
    } catch (e) {
        console.error('[NPCRender] NPC 配置加载失败:', e);
    }
}

function initAgentBridge(onObserve, onAction) {
    agentBridge = new AgentBridge({
        agentId: npcId,
        observe: () => {
            const playerState = onObserve ? onObserve() : {};
            const distance = distanceToPlayer(playerState.player_position || { x: 0, y: 0 });
            const isNear = distance <= nearDistance;

            let event = 'idle';
            if (pendingDialogue) {
                event = 'dialogue';
            } else if (isNear && !playerNearLastTick) {
                event = 'player_near';
            }
            playerNearLastTick = isNear;

            return {
                ...playerState,
                npc_position: { x: npc.x, y: npc.y },
                distance_to_player: distance,
                event: event,
                player_message: pendingDialogue || '',
                timestamp: Date.now()
            };
        },
        onAction: (action) => {
            handleAction(action);
            if (onAction) {
                onAction(action);
            }
        }
    });
}

function startAutoTick(playerStateGetter) {
    if (typeof playerStateGetter === 'function') {
        tickTimer = setInterval(() => {
            const state = playerStateGetter();
            if (agentBridge) agentBridge.tick(state);
        }, tickInterval);
    }
}

function updateNpcMovement() {
    const dx = npc.targetX - npc.x;
    const dy = npc.targetY - npc.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist > 2) {
        npc.x += (dx / dist) * npc.speed;
        npc.y += (dy / dist) * npc.speed;
        npc.isMoving = true;

        if (Math.abs(dx) > Math.abs(dy)) {
            npc.facingDirection = dx > 0 ? 'right' : 'left';
        } else {
            npc.facingDirection = dy > 0 ? 'down' : 'up';
        }
    } else {
        npc.isMoving = false;
    }
}

function updateNpcAnimation() {
    if (npc.isMoving) {
        npc.frameTimer += 0.1;
        if (npc.frameTimer >= 1) {
            npc.frame = (npc.frame + 1) % npc.frameCount;
            npc.frameTimer = 0;
        }
    } else {
        npc.frame = 0;
    }
}

function drawNpc() {
    // 防御性检查：确保 ctx 已初始化
    if (!ctx) {
        console.warn('[NPCRender] Context 未初始化，跳过 NPC 绘制');
        return;
    }

    if (npc.spriteLoaded && npc.sprite) {
        // 计算缩放后的尺寸
        const drawWidth = npc.width * npc.scale;
        const drawHeight = npc.height * npc.scale;
        ctx.drawImage(
            npc.sprite,
            npc.frame * npc.width, 0,
            npc.width, npc.height,
            npc.x - drawWidth / 2,
            npc.y - drawHeight / 2,
            drawWidth, drawHeight
        );
    } else {
        // 默认颜色块（也应用缩放）
        const drawWidth = npc.width * npc.scale;
        const drawHeight = npc.height * npc.scale;
        ctx.fillStyle = '#f97316';
        ctx.fillRect(
            npc.x - drawWidth / 2,
            npc.y - drawHeight / 2,
            drawWidth, drawHeight
        );
        // 简单眼睛（根据缩放调整位置和大小）
        const eyeSize = 6 * npc.scale;
        const eyeOffsetX = 8 * npc.scale;
        const eyeOffsetY = 10 * npc.scale;
        ctx.fillStyle = '#fff';
        ctx.fillRect(npc.x - eyeOffsetX, npc.y - eyeOffsetY, eyeSize, eyeSize);
        ctx.fillRect(npc.x + eyeOffsetX / 2, npc.y - eyeOffsetY, eyeSize, eyeSize);
    }
}

function drawEmote() {
    // 防御性检查：确保 ctx 已初始化
    if (!ctx) return;
    if (!npc.emote || Date.now() > npc.emoteUntil) return;

    // 表情位置也根据缩放调整
    const drawHeight = npc.height * npc.scale;
    ctx.font = `${28 * npc.scale}px sans-serif`;
    ctx.fillText(EMOTE_MAP[npc.emote] || '✨', npc.x - 14 * npc.scale, npc.y - drawHeight / 2 - 15 * npc.scale);
}

// ===== 对话按钮 & 底部对话框 =====

let lastPlayerPos = { x: 0, y: 0 };
let buttonClicked = false;

function drawTalkButton() {
    // 防御性检查：确保 ctx 已初始化
    if (!ctx) return;

    // 计算与玩家距离
    const dist = Math.sqrt(
        Math.pow(lastPlayerPos.x - npc.x, 2) +
        Math.pow(lastPlayerPos.y - npc.y, 2)
    );

    if (dist < nearDistance) {
        // 绘制对话按钮（按钮大小固定，位置随 NPC 缩放）
        const btnX = npc.x;
        const drawHeight = npc.height * npc.scale;
        const btnY = npc.y - drawHeight / 2 - 35;
        const btnRadius = 12;

        // 按钮背景
        ctx.beginPath();
        ctx.arc(btnX, btnY, btnRadius, 0, Math.PI * 2);
        ctx.fillStyle = '#4cc9f0';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // 按钮文字
        ctx.fillStyle = '#000';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('...', btnX, btnY);

        // 存储按钮位置供点击检测
        chatUI = chatUI || {};
        chatUI.talkButtonBounds = {
            x: btnX - btnRadius,
            y: btnY - btnRadius,
            width: btnRadius * 2,
            height: btnRadius * 2,
            centerX: btnX,
            centerY: btnY
        };
    } else {
        chatUI = chatUI || {};
        chatUI.talkButtonBounds = null;
    }
}

// 监听点击事件
if (typeof document !== 'undefined') {
    document.addEventListener('click', function (e) {
        if (!chatUI || !chatUI.talkButtonBounds) return;

        const bounds = chatUI.talkButtonBounds;
        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;

        // 检测是否点击了对话按钮
        const dx = clickX - bounds.centerX;
        const dy = clickY - bounds.centerY;
        if (Math.sqrt(dx * dx + dy * dy) <= bounds.width / 2) {
            openChatDialog();
        }
    });
}

function addToChatHistory(speaker, message) {
    chatHistory.push({ speaker: speaker, message: message });
    // 只保留最近3条
    if (chatHistory.length > 3) {
        chatHistory = chatHistory.slice(-3);
    }
    updateChatUI();
}

// ===== 短期记忆相关 =====

/**
 * 获取短期对话记忆
 * @param {string} targetNpcId - NPC ID
 * @param {number} limit - 返回轮数
 * @param {string} playerId - 玩家 ID
 * @returns {Promise<Object>} 包含 display_messages 的对象
 */
async function getShortTermMemory(targetNpcId, limit = 3, playerId = 'default_player') {
    try {
        const serverUrl = getServerBaseUrl();
        const response = await fetch(
            `${serverUrl}/api/short_term_memory/${encodeURIComponent(targetNpcId)}?limit=${limit}&player_id=${encodeURIComponent(playerId)}`
        );
        if (response.ok) {
            const data = await response.json();
            console.log('[NPCRender] 获取到记忆数据:', data);
            return data;
        } else {
            console.warn('[NPCRender] 获取记忆失败，状态码:', response.status);
        }
    } catch (e) {
        console.warn('[NPCRender] 获取历史记录失败:', e);
    }
    return { display_messages: [] };
}

/**
 * 获取服务器基础 URL
 * @returns {string} 服务器 URL
 */
function getServerBaseUrl() {
    // 默认连接到框架服务器
    if (window.location.protocol === 'https:') {
        return `https://${window.location.host}`;
    } else {
        return `http://${window.location.host}`;
    }
}

/**
 * 加载短期记忆到聊天历史
 * @param {Array} messages - 消息列表
 */
function loadMemoryToChatHistory(messages) {
    if (!messages || messages.length === 0) return;

    // 清空现有本地历史
    chatHistory = [];

    // 加载服务器返回的历史（倒序，因为服务器返回的是最新的在前面）
    messages.forEach(msg => {
        chatHistory.push({
            speaker: msg.speaker,
            message: msg.content
        });
    });

    // 只保留最近3条
    if (chatHistory.length > 3) {
        chatHistory = chatHistory.slice(-3);
    }
}

async function openChatDialog() {
    isChatOpen = true;
    createChatUI();

    // 【修复】从当前 observe 状态获取 player_id
    const observeState = typeof agentBridge !== 'undefined' && agentBridge.observe
        ? agentBridge.observe()
        : {};
    const playerId = observeState.player_id || 'default_player';

    // 获取短期记忆历史（使用正确的 NPC ID 和 Player ID）
    const memoryData = await getShortTermMemory(npcId, 3, playerId);
    if (memoryData && memoryData.display_messages) {
        loadMemoryToChatHistory(memoryData.display_messages);
        updateChatUI();
    } else {
        console.log('[NPCRender] 无历史对话记录');
    }
}

function closeChatDialog() {
    isChatOpen = false;
    removeChatUI();
}

function createChatUI() {
    removeChatUI();

    // 创建对话框容器
    const container = document.createElement('div');
    container.id = 'npc-chat-dialog';
    container.style.cssText = `
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 200px;
            background: rgba(15, 23, 42, 0.95);
            border-top: 2px solid #4cc9f0;
            display: flex;
            flex-direction: column;
            font-family: 'Segoe UI', sans-serif;
            z-index: 10000;
        `;

    // 标题栏
    const header = document.createElement('div');
    header.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            border-bottom: 1px solid rgba(76, 201, 240, 0.3);
        `;

    const title = document.createElement('span');
    title.textContent = npcName;
    title.style.cssText = 'color: #4cc9f0; font-size: 16px; font-weight: bold;';

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.cssText = `
            background: none;
            border: none;
            color: #fff;
            font-size: 24px;
            cursor: pointer;
            padding: 0 8px;
        `;
    closeBtn.onclick = closeChatDialog;
    header.appendChild(title);
    header.appendChild(closeBtn);

    // 消息显示区
    const messages = document.createElement('div');
    messages.id = 'chat-messages';
    messages.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        `;

    // 输入区
    const inputArea = document.createElement('div');
    inputArea.style.cssText = `
            display: flex;
            gap: 8px;
            padding: 12px 16px;
            border-top: 1px solid rgba(76, 201, 240, 0.3);
        `;

    const input = document.createElement('input');
    input.id = 'chat-input';
    input.type = 'text';
    input.placeholder = '输入你想说的话...';
    input.style.cssText = `
            flex: 1;
            padding: 10px 14px;
            border: 1px solid rgba(76, 201, 240, 0.5);
            border-radius: 6px;
            background: rgba(30, 41, 59, 0.8);
            color: #fff;
            font-size: 14px;
            outline: none;
        `;
    input.onkeydown = function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const sendBtn = document.createElement('button');
    sendBtn.textContent = '发送';
    sendBtn.style.cssText = `
            padding: 10px 20px;
            background: #4cc9f0;
            border: none;
            border-radius: 6px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
        `;
    sendBtn.onclick = sendMessage;

    inputArea.appendChild(input);
    inputArea.appendChild(sendBtn);

    container.appendChild(header);
    container.appendChild(messages);
    container.appendChild(inputArea);
    document.body.appendChild(container);

    chatUI = { container: container, messages: messages };
    updateChatUI();
    input.focus();
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    if (!input) return;

    const message = input.value.trim();
    if (!message) return;

    // 发送对话到框架
    sendDialogue(message);
    input.value = '';
}

function updateChatUI() {
    if (!chatUI || !chatUI.messages) return;

    chatUI.messages.innerHTML = '';
    chatHistory.forEach(item => {
        const msgDiv = document.createElement('div');
        const isPlayer = item.speaker === '玩家';
        msgDiv.style.cssText = `
                color: ${isPlayer ? '#93c5fd' : '#e5eefc'};
                font-size: 14px;
                line-height: 1.4;
            `;
        msgDiv.innerHTML = `<strong>${item.speaker}:</strong> ${item.message}`;
        chatUI.messages.appendChild(msgDiv);
    });

    // 滚动到底部
    chatUI.messages.scrollTop = chatUI.messages.scrollHeight;
}

function removeChatUI() {
    const existing = document.getElementById('npc-chat-dialog');
    if (existing) {
        existing.remove();
    }
    chatUI = null;
}

// ES Module 导出
const NPCRender = {
    init,
    update,
    draw,
    handleAction,
    getPosition,
    getSize,
    distanceToPlayer,
    sendDialogue,
    tick,
    isConnected,
    destroy,
    openChatDialog,
    closeChatDialog,
    // 暴露玩家位置更新方法
    updatePlayerPosition: (pos) => {
        lastPlayerPos = pos;
    },
    // 获取配置加载状态
    isConfigLoaded: () => configLoaded,
    // 获取当前 NPC 配置
    getNpcConfig: () => npcConfig,
    // 获取当前 NPC 名称
    getNpcName: () => npcName,
    // 获取 NPC ID
    getNpcId: () => npcId,
    setPosition
};

export { NPCRender };
export default NPCRender;

//移除了 IIFE
