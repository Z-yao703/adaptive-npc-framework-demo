/**
 * NpcManager - 多 NPC 管理系统
 * 
 * 职责：
 * - 从 markers 层读取 npc1-3 矩形区域，计算中心坐标
 * - 为每个 NPC 创建 Phaser Sprite + 名字标签
 * - 为每个 NPC 创建独立的 AgentBridge WebSocket 连接
 * - 距离检测，返回最近的可交互 NPC
 * - 定时 tick 同步玩家状态到服务器
 */
import { AgentBridge } from '../../../bridge/core/agent_bridge.js';
import { AnimationManager } from '../../../bridge/tools/animation-manager.js';
import { NPC_CONFIGS, PLAYER_ID, NEAR_DISTANCE, TICK_INTERVAL, SERVER_URL, API_BASE } from '../config/npc-config.js';

export default class NpcManager {
    /**
     * @param {Phaser.Scene} scene - 游戏场景
     * @param {Array} markerObjects - markers 对象层的 objects 数组
     * @param {object} dialogueUI - DialogueUI 实例
     */
    constructor(scene, markerObjects, dialogueUI) {
        this.scene = scene;
        this.markerObjects = markerObjects;
        this.dialogueUI = dialogueUI;

        // 存储每个 NPC 的数据
        this.npcs = {};       // { npcId: { sprite, bridge, config, label, ... } }
        this.tickTimers = {}; // { npcId: intervalId }

        // 动画配置加载状态（防重复加载）
        this._animConfigs = {}; // { npcId: { loaded: bool, loading: bool } }

        // 玩家位置引用
        this.playerX = 0;
        this.playerY = 0;
    }

    /**
     * 创建所有 NPC
     * @param {number} playerX - 初始玩家位置
     * @param {number} playerY 
     */
    createAllNpcs(playerX, playerY) {
        this.playerX = playerX;
        this.playerY = playerY;

        NPC_CONFIGS.forEach(config => {
            this.createNpc(config);
        });

        console.log(`[NpcManager] ${NPC_CONFIGS.length} 个 NPC 创建完成`);
    }

    /**
     * 创建单个 NPC
     */
    createNpc(config) {
        // 从 markers 层获取 NPC 区域坐标
        const markerObj = this.markerObjects.find(obj => obj.name === config.markerName);
        if (!markerObj) {
            console.warn(`[NpcManager] 未找到 marker: ${config.markerName}，NPC ${config.name} 将不会被创建`);
            return;
        }

        // 计算区域中心位置
        const centerX = markerObj.x + markerObj.width / 2;
        const centerY = markerObj.y + markerObj.height / 2;

        console.log(`[NpcManager] 创建 NPC: ${config.name} (${config.id}) at (${centerX}, ${centerY})`);

        // 创建 Phaser Sprite（先使用占位纹理，后续由动画系统替换）
        const textureKey = `npc_placeholder_${NPC_CONFIGS.indexOf(config) + 1}`;
        const sprite = this.scene.add.sprite(centerX, centerY, textureKey);
        sprite.setDisplaySize(32, 32);
        sprite.setInteractive({ useHandCursor: true });

        // 名字标签（头顶显示）
        const label = this.scene.add.text(centerX, centerY - 24, config.name, {
            font: '12px monospace',
            fill: '#ffffff',
            stroke: '#000000',
            strokeThickness: 3
        });
        label.setOrigin(0.5, 0.5);

        // 交互提示图标（靠近时显示）
        const hint = this.scene.add.sprite(centerX, centerY - 40, 'npc_hint');
        hint.setVisible(false);

        // 创建 AgentBridge WebSocket 连接
        const bridge = this.createAgentBridge(config, sprite, label, hint);

        // 存储 NPC 数据
        this.npcs[config.id] = {
            config: config,
            sprite: sprite,
            label: label,
            hint: hint,
            bridge: bridge,
            x: centerX,
            y: centerY,
            // ===== 动画与移动相关 =====
            animationManager: null,   // AnimationManager 实例
            animKeyMap: null,         // createFromConfig 返回的 key 映射
            currentAction: 'idle',    // 当前动作：'idle' | 'walk'
            currentDirection: 'down', // 当前朝向
            isMoving: false,          // 是否正在移动
            targetX: centerX,         // 移动目标 X
            targetY: centerY,         // 移动目标 Y
            speed: 2,                 // 移动速度（像素/帧）
            // ===== 寻路路径队列 =====
            pathQueue: [],            // 路径点队列 [{x, y}, ...]
            pathIndex: 0,             // 当前路径点索引
            // ===== 随机漫游 =====
            homeBounds: {             // 房间边界（来自地图 marker）
                x: markerObj.x, y: markerObj.y,
                width: markerObj.width, height: markerObj.height
            },
            roamingEnabled: true,     // 是否启用随机漫游
            roamTimer: 0              // 漫游计时器（ms），每10s更换目标
        };

        // 异步加载 NPC 渲染配置（精灵图 + 动画）
        this._loadNpcRenderConfig(config.id);
    }

    /**
     * 为单个 NPC 创建 AgentBridge 连接
     */
    createAgentBridge(config, sprite, label, hint) {
        const bridge = new AgentBridge({
            agentId: config.id,
            serverUrl: `${SERVER_URL}/ws/${encodeURIComponent(config.id)}`,
            observe: () => {
                // 返回当前游戏状态（复用统一构造方法）
                const npcData = this.npcs[config.id];
                const npcX = npcData ? npcData.x : sprite.x;
                const npcY = npcData ? npcData.y : sprite.y;
                const eventType = Math.sqrt(
                    (this.playerX - npcX) ** 2 + (this.playerY - npcY) ** 2
                ) < NEAR_DISTANCE ? 'player_near' : 'idle';

                return this._buildGameState(npcX, npcY, eventType);
            },
            onAction: (action) => {
                this.handleAction(config.id, config.name, action, sprite, hint);
            }
        });

        return bridge;
    }

    /**
     * 处理服务器返回的 Action
     */
    handleAction(npcId, npcName, action, sprite, hint) {
        const npcData = this.npcs[npcId];
        if (!npcData) return;

        const actionType = action.type || 'UNKNOWN';
        if (actionType === 'GIVE_GOLD' || actionType === 'COMPLETE_QUEST' || actionType === 'UPDATE_QUEST') {
            console.log(`[NpcManager] >>> 收到关键Action: ${actionType}, params=${JSON.stringify(action.params)}`);
        }

        switch (action.type) {
            case 'NPC_SAY': {
                const text = action.params?.text || action.params?.message || '...';
                console.log(`[NpcManager] NPC_SAY from ${npcName}: ${text}`);

                // 传递给对话 UI
                if (this.dialogueUI) {
                    this.dialogueUI.onNpcSay(npcId, npcName, text);
                }
                break;
            }
            case 'NPC_EMOTE':
                console.log(`[NpcManager] NPC_EMOTE from ${npcName}:`, action.params?.emotion);
                break;
            case 'MOVE_TO': {
                const tx = action.params?.x ?? action.params?.target?.x;
                const ty = action.params?.y ?? action.params?.target?.y;
                if (tx != null && ty != null) {
                    npcData.targetX = tx;
                    npcData.targetY = ty;
                    npcData.speed = Math.max(0.5, (action.params?.speed || 60) / 30);
                    npcData.isMoving = true;
                    console.log(`[NpcManager] MOVE_TO ${npcName} -> (${tx}, ${ty}), speed=${npcData.speed}`);
                }
                break;
            }
            case 'NPC_STOP':
                npcData.targetX = npcData.x;
                npcData.targetY = npcData.y;
                npcData.isMoving = false;
                console.log(`[NpcManager] NPC_STOP ${npcName}`);
                break;
            case 'START_TRADE': {
                const items = action.params?.items || [];
                const tip = action.params?.tip || 0;
                const message = action.params?.message || '';
                console.log(`[NpcManager] START_TRADE from ${npcName}: items=${JSON.stringify(items)}, tip=${tip}`);

                if (this.scene && this.scene.tradePanel) {
                    this.scene.tradePanel.open(npcId, npcName, items, tip, message);
                }
                break;
            }
            case 'GIVE_ITEM': {
                const item = action.params?.item || '';
                const quantity = action.params?.quantity || 1;
                console.log(`[NpcManager] GIVE_ITEM: ${npcName} 给玩家 ${quantity}x ${item}`);

                if (window.gameState && window.gameState.addQuestItem) {
                    window.gameState.addQuestItem(item, quantity);
                }

                if (this.scene && this.scene.shopSystem) {
                    this.scene.shopSystem.refreshBackpackPanel();
                }

                if (this.dialogueUI) {
                    this.dialogueUI.onSystemMessage(`🎁 ${npcName} 给了你 ${item} x${quantity}`);
                }
                break;
            }
            case 'TAKE_ITEM': {
                const item = action.params?.item || '';
                const quantity = action.params?.quantity || 1;
                console.log(`[NpcManager] TAKE_ITEM: ${npcName} 收走 ${quantity}x ${item}`);

                if (window.gameState && window.gameState.removeQuestItem) {
                    window.gameState.removeQuestItem(item, quantity);
                }

                if (this.scene && this.scene.shopSystem) {
                    this.scene.shopSystem.refreshBackpackPanel();
                }

                if (this.dialogueUI) {
                    this.dialogueUI.onSystemMessage(`📦 ${npcName} 收走了 ${item} x${quantity}`);
                }
                break;
            }
            case 'GIVE_GOLD': {
                const amount = action.params?.amount || 0;
                const reason = action.params?.reason || '';
                console.log(`[NpcManager] GIVE_GOLD: ${npcName} 给予 ${amount} 金币, 原因: ${reason}`);

                if (window.gameState && window.gameState.addGold) {
                    window.gameState.addGold(amount);
                }

                if (this.scene && this.scene.shopSystem) {
                    this.scene.shopSystem.updateGoldDisplay();
                }

                if (this.dialogueUI) {
                    this.dialogueUI.onSystemMessage(`💰 获得 ${amount} 金币${reason ? '（' + reason + '）' : ''}`);
                }
                break;
            }
            case 'START_QUEST': {
                const questId = action.params?.quest_id || '';
                const title = action.params?.title || questId;
                const description = action.params?.description || '';
                console.log(`[NpcManager] START_QUEST: ${title} (${questId})`);

                if (window.gameState && window.gameState.addActiveQuest) {
                    window.gameState.addActiveQuest(questId, title, description);
                }

                if (this.dialogueUI) {
                    this.dialogueUI.onSystemMessage(`📋 新任务: ${title}`);
                }
                break;
            }
            case 'UPDATE_QUEST': {
                const questId = action.params?.quest_id || '';
                const stage = action.params?.stage || 1;
                console.log(`[NpcManager] UPDATE_QUEST: ${questId} → 阶段 ${stage}`);

                if (window.gameState && window.gameState.updateQuestStage) {
                    window.gameState.updateQuestStage(questId, stage);
                }
                break;
            }
            case 'COMPLETE_QUEST': {
                const questId = action.params?.quest_id || '';
                const rewards = action.params?.rewards || [];
                console.log(`[NpcManager] COMPLETE_QUEST: ${questId}, rewards=${JSON.stringify(rewards)}`);

                if (window.gameState) {
                    for (const reward of rewards) {
                        if (reward.item === '金币' || reward.item === 'gold') {
                            if (window.gameState.addGold) {
                                window.gameState.addGold(reward.quantity || 0);
                            }
                        } else if (window.gameState.addQuestItem) {
                            window.gameState.addQuestItem(reward.item, reward.quantity || 1);
                        }
                    }
                }

                if (window.gameState && window.gameState.activeQuests) {
                    delete window.gameState.activeQuests[questId];
                }

                if (this.scene && this.scene.shopSystem) {
                    this.scene.shopSystem.updateGoldDisplay();
                    this.scene.shopSystem.refreshBackpackPanel();
                }

                if (this.dialogueUI) {
                    this.dialogueUI.onSystemMessage(`✅ 任务完成: ${questId}`);
                }
                break;
            }
            case 'UPDATE_SUSPICION': {
                const value = action.params?.value;
                if (value !== undefined && this.scene && this.scene.deductionPanel) {
                    this.scene.deductionPanel.updateSuspicion(value);
                    console.log(`[NpcManager] 警惕度更新: ${value}%`);
                }
                if (value >= 100 && this.scene && this.scene.scriptManager) {
                    this.scene.scriptManager.showEndScreen(null, null, value);
                }
                break;
            }
            default:
                console.log(`[NpcManager] Unknown action from ${npcName}:`, action.type);
        }
    }

    /**
     * 每帧更新（在 GameScene.update() 中调用）
     * @param {number} playerX 
     * @param {number} playerY 
     */
    update(playerX, playerY) {
        this.playerX = playerX;
        this.playerY = playerY;

        // 检测每个 NPC 与玩家的距离，更新交互提示
        let nearestNpcId = null;
        let nearestDistance = Infinity;

        Object.values(this.npcs).forEach(npcData => {
            const dx = playerX - npcData.x;
            const dy = playerY - npcData.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < NEAR_DISTANCE && distance < nearestDistance) {
                nearestDistance = distance;
                nearestNpcId = npcData.config.id;
            }
        });

        // 更新提示图标显示 + NPC 移动与动画 + 随机漫游
        Object.values(this.npcs).forEach(npcData => {
            npcData.hint.setVisible(npcData.config.id === nearestNpcId);
            // 驱动 NPC 移动
            this._updateNpcMovement(npcData);
            // 随机漫游计时
            this._updateRoaming(npcData);
        });

        this.nearestNpcId = nearestNpcId;
    }

    /**
     * Tick AgentBridge（发送状态更新），由 game 循环中的定时器驱动
     */
    tickAll() {
        Object.values(this.npcs).forEach(npcData => {
            if (npcData.bridge && npcData.bridge.isConnected) {
                npcData.bridge.tick();
            }
        });
    }

    /**
     * 获取最近的可交互 NPC 的 ID
     */
    getNearestNpcId() {
        return this.nearestNpcId || null;
    }

    /**
     * 获取可交易物资列表（从 gameState 提取10项物资的名称、售价、类型）
     * 供 observe() 透传给后端，用于向量匹配
     */
    getTradeableItems() {
        const items = [];
        const gs = window.gameState;
        if (!gs) return items;

        if (gs.foods) {
            Object.entries(gs.foods).forEach(([name, data]) => {
                items.push({
                    name,
                    sellPrice: data.sellPrice || 0,
                    type: 'food'
                });
            });
        }
        if (gs.supplies) {
            Object.entries(gs.supplies).forEach(([name, data]) => {
                items.push({
                    name,
                    sellPrice: data.sellPrice || 0,
                    type: 'supply'
                });
            });
        }
        return items;
    }

    /**
     * 获取指定 NPC 的 AgentBridge
     */
    getAgentBridge(npcId) {
        const npcData = this.npcs[npcId];
        return npcData ? npcData.bridge : null;
    }

    /**
     * 获取指定 NPC 的配置
     */
    getNpcConfig(npcId) {
        const npcData = this.npcs[npcId];
        return npcData ? npcData.config : null;
    }

    /**
     * 为指定 NPC 设置寻路路径
     * 通过 Pathfinder 计算的路径点列表驱动 NPC 沿路径移动
     * @param {string} npcId - NPC ID
     * @param {Array<{x: number, y: number}>} waypoints - 路径点列表（像素坐标）
     */
    setNpcPath(npcId, waypoints) {
        const npcData = this.npcs[npcId];
        if (!npcData || !waypoints || waypoints.length === 0) return;

        npcData.pathQueue = waypoints;
        npcData.pathIndex = 0;
        npcData.targetX = waypoints[0].x;
        npcData.targetY = waypoints[0].y;
        npcData.isMoving = true;

        console.log(`[NpcManager] ${npcData.config.name} 路径已设置，共 ${waypoints.length} 个路径点`);
    }

    /**
     * 设置 Pathfinder 引用（由 GameScene 在初始化时注入）
     * 漫游时使用寻路以避免穿过家具/墙壁
     */
    setPathfinder(pathfinder) {
        this._pathfinder = pathfinder;
    }

    /**
     * 启用指定 NPC 的随机漫游
     */
    enableRoaming(npcId) {
        const npcData = this.npcs[npcId];
        if (!npcData) return;
        npcData.roamingEnabled = true;
        npcData.roamTimer = 0;
        console.log(`[NpcManager] ${npcData.config.name} 漫游已启用`);
    }

    /**
     * 禁用指定 NPC 的随机漫游（如玩家进入房间时）
     */
    disableRoaming(npcId) {
        const npcData = this.npcs[npcId];
        if (!npcData) return;
        npcData.roamingEnabled = false;
        console.log(`[NpcManager] ${npcData.config.name} 漫游已禁用`);
    }

    /**
     * 每帧更新漫游计时器
     * 当 roamingEnabled 为 true 时，每 10s 选取房间内随机位置
     */
    _updateRoaming(npcData) {
        if (!npcData.roamingEnabled) return;
        if (!npcData.homeBounds) return;

        // 约 60fps → 每帧 +16ms
        npcData.roamTimer = (npcData.roamTimer || 0) + 16;

        if (npcData.roamTimer >= 10000) {
            npcData.roamTimer = 0;
            this._pickRoamingTarget(npcData);
        }
    }

    /**
     * 在房间边界内选取随机位置作为漫游目标
     */
    _pickRoamingTarget(npcData) {
        const b = npcData.homeBounds;
        const margin = 16; // 距离边界留边距

        const rx = b.x + margin + Math.random() * Math.max(0, b.width - margin * 2);
        const ry = b.y + margin + Math.random() * Math.max(0, b.height - margin * 2);

        // 有寻路器：计算路径
        if (this._pathfinder) {
            const path = this._pathfinder.findPath(npcData.x, npcData.y, rx, ry);
            if (path && path.length > 0) {
                npcData.pathQueue = path;
                npcData.pathIndex = 0;
                npcData.targetX = path[0].x;
                npcData.targetY = path[0].y;
                npcData.isMoving = true;
                return;
            }
        }

        // 降级：直线移动
        npcData.pathQueue = [];
        npcData.pathIndex = 0;
        npcData.targetX = rx;
        npcData.targetY = ry;
        npcData.isMoving = true;
    }

    /**
     * 构造统一的游戏状态（位置 + 任务 + 背包），供 observe() 和 sendDialogue() 复用
     */
    _buildGameState(npcX, npcY, eventType, extra = {}) {
        const dx = this.playerX - npcX;
        const dy = this.playerY - npcY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // 获取全局游戏状态
        const gs = window.gameState || {};

        // 构造背包列表
        const inventory = [];
        if (gs.questItems) {
            Object.entries(gs.questItems).forEach(([name, data]) => {
                if (data.count > 0) {
                    inventory.push({ id: name, item_id: name, count: data.count });
                }
            });
        }
        // 同时包含食物和杂物（如果存在）
        if (gs.foods) {
            Object.entries(gs.foods).forEach(([name, data]) => {
                if (data.count > 0) {
                    inventory.push({ id: name, item_id: name, count: data.count, type: 'food' });
                }
            });
        }
        if (gs.supplies) {
            Object.entries(gs.supplies).forEach(([name, data]) => {
                if (data.count > 0) {
                    inventory.push({ id: name, item_id: name, count: data.count, type: 'supply' });
                }
            });
        }

        // 构造活跃任务列表
        const playerQuests = gs.activeQuests ? Object.values(gs.activeQuests) : [];
        const activeQuestIds = playerQuests.map(q => q.id);
        const completedIds = gs.completedQuests ? Object.keys(gs.completedQuests) : [];

        return {
            player_id: PLAYER_ID,
            player_position: { x: this.playerX, y: this.playerY },
            npc_position: { x: npcX, y: npcY },
            distance_to_player: distance,
            event: eventType,
            timestamp: Date.now(),
            // 任务和背包状态
            player_quests: playerQuests,
            quest_active_ids: activeQuestIds,
            quest_completed_ids: completedIds,
            player_inventory: inventory,
            tradeable_items: this.getTradeableItems(),
            ...extra
        };
    }

    /**
     * 发送玩家消息到指定 NPC
     */
    sendDialogue(npcId, message) {
        if (!npcId || !message) return;

        const npcData = this.npcs[npcId];
        if (!npcData || !npcData.bridge) return;

        // 使用统一的状态构造方法，确保背包和任务数据同步发送
        const state = this._buildGameState(npcData.x, npcData.y, 'dialogue', {
            player_message: message
        });

        npcData.bridge.tick(state);

        console.log(`[NpcManager] 发送消息到 ${npcData.config.name}: ${message}`);
    }

    /**
     * 检测是否有 NPC 在可交互范围内
     */
    isAnyNpcNearby() {
        return this.nearestNpcId !== null;
    }

    /**
     * 销毁所有 NPC 和连接
     */
    destroy() {
        Object.values(this.npcs).forEach(npcData => {
            if (npcData.bridge) {
                npcData.bridge.disconnect();
            }

            const textureKey = npcData.textureKey || `npc_${npcData.config.id}`;

            if (this.scene && this.scene.anims) {
                ['idle_down', 'idle_left', 'idle_right', 'idle_up',
                    'walk_down', 'walk_left', 'walk_right', 'walk_up'].forEach(action => {
                        const animKey = `${textureKey}_${action}`;
                        if (this.scene.anims.exists(animKey)) {
                            this.scene.anims.remove(animKey);
                        }
                    });
            }

            if (this.scene && this.scene.textures && this.scene.textures.exists(textureKey)) {
                this.scene.textures.remove(textureKey);
            }

            if (npcData.sprite) {
                npcData.sprite.destroy();
            }
            if (npcData.label) {
                npcData.label.destroy();
            }
            if (npcData.hint) {
                npcData.hint.destroy();
            }
        });

        this.npcs = {};
        this._animConfigs = {};
        console.log('[NpcManager] 所有 NPC 和连接已销毁');
    }

    // =========================================
    // NPC 动画系统（框架对接）
    // =========================================

    /**
     * 从服务器加载 NPC 渲染配置（精灵图 + 动画帧）
     * 异步操作，加载完成后自动创建纹理和动画
     */
    async _loadNpcRenderConfig(npcId) {
        // 防重复加载
        if (this._animConfigs[npcId]?.loading || this._animConfigs[npcId]?.loaded) return;
        this._animConfigs[npcId] = { loading: true, loaded: false };

        try {
            const apiUrl = `${API_BASE}/api/agent/${encodeURIComponent(npcId)}`;
            console.log(`[NpcManager] 请求 NPC 配置: ${apiUrl}`);

            const res = await fetch(apiUrl);
            if (!res.ok) {
                console.warn(`[NpcManager] NPC 配置加载失败 (${npcId}), status: ${res.status}, 保持占位纹理`);
                this._animConfigs[npcId] = { loading: false, loaded: true };
                return;
            }

            const apiConfig = await res.json();
            this._onNpcConfigLoaded(npcId, apiConfig);
        } catch (err) {
            console.warn(`[NpcManager] NPC 配置加载异常 (${npcId}): ${err.message}, 保持占位纹理`);
            this._animConfigs[npcId] = { loading: false, loaded: true };
        }
    }

    /**
     * 配置加载完成后的处理：
     *   1. 读取精灵图路径和渲染配置
     *   2. 动态加载精灵图纹理
     *   3. 通过 AnimationManager 创建 8 方向动画
     */
    _onNpcConfigLoaded(npcId, apiConfig) {
        const npcData = this.npcs[npcId];
        if (!npcData) {
            this._animConfigs[npcId] = { loading: false, loaded: false };
            return;
        }

        // 读取配置
        const renderCfg = apiConfig.presentation?.render_cfg || apiConfig.render_cfg || {};
        const spritePath = apiConfig.presentation?.sprite || apiConfig.sprite;

        console.log(`[NpcManager] 配置加载成功: ${npcId}, sprite: ${spritePath}`);

        if (spritePath) {
            // 有精灵图 → 加载纹理并创建动画
            // 精灵图是静态资源，与 HTML 页面同源（Vite 开发服务器）
            // 只需处理绝对 URL（http/https 开头）和相对路径两种情况
            const spriteUrl = spritePath.startsWith('http')
                ? spritePath              // 绝对 URL：直接使用
                : spritePath;              // 相对路径：浏览器按页面 origin 解析
            this._createNpcTexture(npcId, spriteUrl, renderCfg);
        } else {
            // 无精灵图 → 使用占位纹理 + 默认动画配置
            this._createNpcAnimations(npcId, renderCfg);
            this._animConfigs[npcId] = { loading: false, loaded: true };
        }
    }

    /**
     * 动态加载 NPC 精灵图纹理并创建动画
     * 使用 Image + scene.textures.addSpriteSheet 绕过 Phaser 预加载
     */
    _createNpcTexture(npcId, spriteUrl, renderCfg) {
        const npcData = this.npcs[npcId];
        if (!npcData) return;

        const textureKey = `npc_${npcId}`;
        const frameWidth = renderCfg.frameWidth || 48;
        const frameHeight = renderCfg.frameHeight || 64;
        const scale = renderCfg.scale || 2;

        const img = new Image();
        img.crossOrigin = 'anonymous';

        img.onload = () => {
            // 如果纹理已存在，先移除
            if (this.scene.textures.exists(textureKey)) {
                this.scene.textures.remove(textureKey);
            }

            // 创建 spritesheet 纹理
            this.scene.textures.addSpriteSheet(textureKey, img, {
                frameWidth: frameWidth,
                frameHeight: frameHeight
            });

            // 替换 NPC 精灵的纹理
            npcData.sprite.setTexture(textureKey);
            npcData.sprite.setDisplaySize(frameWidth * scale, frameHeight * scale);
            npcData.textureKey = textureKey;

            // 刷新交互区域
            npcData.sprite.setInteractive({ useHandCursor: true });

            console.log(`[NpcManager] NPC ${npcId} 纹理加载成功: ${spriteUrl}`);

            // 创建动画
            this._createNpcAnimations(npcId, renderCfg, textureKey);
            this._animConfigs[npcId] = { loading: false, loaded: true };
        };

        img.onerror = () => {
            console.warn(`[NpcManager] NPC ${npcId} 精灵图加载失败: ${spriteUrl}, 保持占位纹理`);
            // 占位纹理是单帧 Canvas，不是 spritesheet，跳过动画创建
            this._animConfigs[npcId] = { loading: false, loaded: true };
        };

        img.src = spriteUrl;
    }

    /**
     * 创建 NPC 动画（通过 AnimationManager 框架）
     * 动画创建后，后续移动/停止均通过动画系统播放
     */
    _createNpcAnimations(npcId, renderCfg, textureKey) {
        const npcData = this.npcs[npcId];
        if (!npcData) return;

        const texKey = textureKey || npcData.textureKey || npcData.sprite?.texture?.key;
        if (!texKey) return;

        // 实例化 AnimationManager
        const animMgr = new AnimationManager({
            scene: this.scene,
            spriteKey: texKey,
            frameWidth: renderCfg.frameWidth || 48,
            frameHeight: renderCfg.frameHeight || 64
        });

        // 从配置创建动画
        const animKeyMap = animMgr.createFromConfig(renderCfg);

        // 存储到 NPC 数据
        npcData.animationManager = animMgr;
        npcData.animKeyMap = animKeyMap;

        // 播放初始 idle 动画
        animMgr.play(npcData.sprite, 'idle', npcData.currentDirection, animKeyMap);

        console.log(`[NpcManager] NPC ${npcId} 动画创建完成, resolved:`,
            Object.keys(animMgr.getResolved() || {}).map(k =>
                `${k}=${animMgr.getResolved()[k].source}`
            ).join(', ')
        );
    }

    /**
     * 驱动 NPC 移动（每帧调用）
     * 根据 targetX/targetY 平滑移动，自动播放行走 / 停止动画
     */
    _updateNpcMovement(npcData) {
        if (!npcData || npcData.targetX == null || npcData.targetY == null) return;

        try {
            const dx = npcData.targetX - npcData.x;
            const dy = npcData.targetY - npcData.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist > 1.5) {
                npcData.isMoving = true;
                const spd = npcData.speed || 2;
                npcData.x += (dx / dist) * spd;
                npcData.y += (dy / dist) * spd;

                if (npcData.sprite && npcData.sprite.active) {
                    npcData.sprite.setPosition(npcData.x, npcData.y);
                }
                if (npcData.label && npcData.label.active) {
                    npcData.label.setPosition(npcData.x, npcData.y - 24);
                }
                if (npcData.hint && npcData.hint.active) {
                    npcData.hint.setPosition(npcData.x, npcData.y - 40);
                }

                if (Math.abs(dx) > Math.abs(dy)) {
                    npcData.currentDirection = dx > 0 ? 'right' : 'left';
                } else {
                    npcData.currentDirection = dy > 0 ? 'down' : 'up';
                }

                if (npcData.animationManager) {
                    npcData.animationManager.play(
                        npcData.sprite, 'walk', npcData.currentDirection, npcData.animKeyMap
                    );
                }
            } else if (npcData.isMoving) {
                if (npcData.pathQueue && npcData.pathIndex < npcData.pathQueue.length - 1) {
                    npcData.pathIndex++;
                    const nextWaypoint = npcData.pathQueue[npcData.pathIndex];
                    npcData.targetX = nextWaypoint.x;
                    npcData.targetY = nextWaypoint.y;
                } else {
                    npcData.isMoving = false;
                    npcData.x = npcData.targetX;
                    npcData.y = npcData.targetY;
                    if (npcData.sprite && npcData.sprite.active) {
                        npcData.sprite.setPosition(npcData.x, npcData.y);
                    }
                    if (npcData.label && npcData.label.active) {
                        npcData.label.setPosition(npcData.x, npcData.y - 24);
                    }
                    if (npcData.hint && npcData.hint.active) {
                        npcData.hint.setPosition(npcData.x, npcData.y - 40);
                    }
                    npcData.pathQueue = [];
                    npcData.pathIndex = 0;

                    if (npcData.animationManager) {
                        npcData.animationManager.play(
                            npcData.sprite, 'idle', npcData.currentDirection, npcData.animKeyMap
                        );
                    }
                }
            }
        } catch (err) {
            console.warn(`[NpcManager] _updateNpcMovement error for ${npcData.config?.name}:`, err.message);
        }
    }
}
