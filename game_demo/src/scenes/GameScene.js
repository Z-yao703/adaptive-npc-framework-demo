/**
 * GameScene - 主游戏场景（协调器）
 *
 * 职责：
 * - 初始化并协调所有子系统（地图、玩家、商店、剧本、NPC）
 * - 主更新循环，委托各子系统执行每帧逻辑
 * - 按钮 UI 绑定（协调 ShopSystem / ScriptManager / DeductionPanel）
 * - NPC 系统生命周期管理（创建、交互、对话、tick）
 * - 场景销毁清理
 *
 * 子系统依赖：
 * - MapBuilder        → 地图创建、区域触发、交互区域
 * - PlayerController  → 玩家精灵、动画、碰撞、输入
 * - ShopSystem        → 购买面板、背包渲染、金币管理
 * - ScriptManager     → 剧本会话、加载/结束界面、历史管理
 * - NpcManager        → NPC 精灵、WebSocket 连接、距离检测
 * - DialogueUI        → 对话浮层 UI
 * - DeductionPanel    → 答题面板 UI
 */
import NpcManager from '../systems/NpcManager.js';
import DialogueUI from '../systems/DialogueUI.js';
import DeductionPanel from '../systems/DeductionPanel.js';
import InteractionManager from '../systems/InteractionManager.js';
import MapBuilder from '../systems/MapBuilder.js';
import PlayerController from '../systems/PlayerController.js';
import ShopSystem from '../systems/ShopSystem.js';
import ScriptManager from '../systems/ScriptManager.js';
import TradePanel from '../systems/TradePanel.js';
import { Pathfinder } from '../../../bridge/tools/pathfinding.js';
import { TICK_INTERVAL } from '../config/npc-config.js';

export default class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });

        // 子系统引用
        this.mapBuilder = null;
        this.playerController = null;
        this.shopSystem = null;
        this.tradePanel = null;
        this.scriptManager = null;
        this.npcManager = null;
        this.dialogueUI = null;
        this.deductionPanel = null;

        // 路径查询基础设施
        this.pathfinder = null;     // Pathfinder 实例
        this.markersObjects = null; // markers 层对象引用（门位置查询）

        // 状态变量
        this.inputLocked = true;
        this.gameSessionId = null;
        this.gameQuestions = [];
        this.tickTimer = null;
        this.spaceKey = null;
        this.lastSpaceState = false;
    }

    create() {
        console.log('GameScene 创建开始');

        // 1. 实例化子系统
        this.mapBuilder = new MapBuilder(this);
        this.playerController = new PlayerController(this);
        this.shopSystem = new ShopSystem(this);
        this.tradePanel = new TradePanel(this);
        this.scriptManager = new ScriptManager(this);

        // 2. 创建地图
        this.mapBuilder.createMap();

        // 3. 创建玩家
        this.playerController.createPlayer();

        // 4. 设置碰撞
        this.playerController.setupCollisions();

        // 5. 创建房间触发区域
        this.mapBuilder.createRoomTriggers();

        // 6. 创建交互区域（料理台、杂物柜）
        this.mapBuilder.createInteractZones();

        // 7. 设置 UI 交互
        this.setupUI();

        // 8. 初始化金币显示
        this.shopSystem.updateGoldDisplay();

        // 9. 创建 NPC 系统
        this.createNpcSystem();

        // 9b. 构建碰撞网格 + Pathfinder 实例
        this.collisionGrid = this.mapBuilder.buildCollisionGrid();
        if (this.collisionGrid && this.collisionGrid.length > 0) {
            this.pathfinder = new Pathfinder(this.collisionGrid, 32);
            console.log('[GameScene] Pathfinder 实例已创建');
            // 注入给 NpcManager 用于漫游寻路
            if (this.npcManager) {
                this.npcManager.setPathfinder(this.pathfinder);
            }
        }

        // 9c. 注册房间触发回调（NPC 自主行动）
        this.registerRoomCallbacks();

        // 10. 设置 NPC tick 定时器
        this.setupNpcTick();

        // 11. 创建答题面板
        this.deductionPanel = new DeductionPanel();
        this.deductionPanel.onVictory = (title, story) => this.showEndScreen(title, story);
        this.deductionPanel.onGameOver = (suspicion) => this.showEndScreen(null, null, suspicion);
        this.deductionPanel.onEnd = () => this.scriptManager.endGameReturnToNormal();
        this.deductionPanel.onCreateScript = () => this.scriptManager.startNewScript();

        // 12. 显示开始界面（不自动加载剧本）
        this.scriptManager.showStartScreen();

        // 13. 注册场景销毁事件
        this.events.on('shutdown', this.shutdown, this);

        console.log('GameScene 创建完成');
    }

    /**
     * 更新循环
     * 委托各子系统处理：输入、区域限制、触发检测、光标更新、NPC 交互
     */
    update() {
        if (!this.player || !this.player.body) return;

        this.playerController.handlePlayerInput();
        this.playerController.constrainPlayerToArea();
        this.mapBuilder.checkRoomTriggers();
        this.mapBuilder.updateInteractCursors();
        this.updateNpcInteraction();
    }

    /**
     * 设置 UI 交互
     * 使用 HTML DOM 元素，通过事件监听控制面板显示/隐藏
     * 协调 ShopSystem / ScriptManager / DeductionPanel
     */
    setupUI() {
        const btnBackpack = document.getElementById('btn-backpack');
        const panelBackpack = document.getElementById('panel-backpack');
        const btnDeduction = document.getElementById('btn-deduction');
        const panelDeduction = document.getElementById('panel-deduction');
        const btnScripts = document.getElementById('btn-scripts');
        const panelScripts = document.getElementById('panel-scripts');

        // 背包按钮点击事件
        btnBackpack.addEventListener('click', () => {
            this.shopSystem.closePurchasePanel();
            panelDeduction.classList.add('hidden');
            InteractionManager.unlock('deduction_panel');
            panelScripts.classList.add('hidden');

            panelBackpack.classList.toggle('hidden');

            if (!panelBackpack.classList.contains('hidden')) {
                const content = panelBackpack.querySelector('.panel-content');
                if (content) {
                    this.shopSystem.renderBackpackContent(content);
                }
            }

            console.log('背包面板切换');
        });

        // 推论按钮点击事件
        btnDeduction.addEventListener('click', () => {
            this.shopSystem.closePurchasePanel();
            panelBackpack.classList.add('hidden');
            panelScripts.classList.add('hidden');

            panelDeduction.classList.toggle('hidden');

            if (!panelDeduction.classList.contains('hidden')) {
                InteractionManager.lock('deduction_panel');
                if (this.gameSessionId) {
                    this.deductionPanel.init(this.gameSessionId, this.gameQuestions, '');
                } else {
                    this.deductionPanel.render();
                }
            } else {
                InteractionManager.unlock('deduction_panel');
            }
            console.log('推论面板切换');
        });

        // 剧本按钮点击事件
        btnScripts.addEventListener('click', () => {
            this.shopSystem.closePurchasePanel();
            panelBackpack.classList.add('hidden');
            panelDeduction.classList.add('hidden');
            InteractionManager.unlock('deduction_panel');

            panelScripts.classList.toggle('hidden');

            if (!panelScripts.classList.contains('hidden')) {
                this.scriptManager.loadScriptsHistory();
            }
            console.log('剧本面板切换');
        });

        // 关闭按钮事件
        this.setupCloseButtons();

        console.log('UI 交互设置完成');
    }

    /**
     * 设置关闭按钮监听
     */
    setupCloseButtons() {
        setTimeout(() => {
            const closeButtons = document.querySelectorAll('.panel-close');
            closeButtons.forEach(btn => {
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);

                newBtn.addEventListener('click', (e) => {
                    const panelName = e.target.getAttribute('data-panel');
                    if (panelName === 'backpack') {
                        document.getElementById('panel-backpack').classList.add('hidden');
                    } else if (panelName === 'deduction') {
                        document.getElementById('panel-deduction').classList.add('hidden');
                        InteractionManager.unlock('deduction_panel');
                    } else if (panelName === 'scripts') {
                        document.getElementById('panel-scripts').classList.add('hidden');
                    } else if (panelName === 'script-detail') {
                        const detailPanel = document.getElementById('panel-script-detail');
                        if (detailPanel && detailPanel.parentNode) {
                            detailPanel.remove();
                        }
                    }
                });
            });
        }, 100);
    }

    // ===== NPC 系统 =====

    /**
     * 创建 NPC 系统（对话 UI + NPC 管理器）
     */
    createNpcSystem() {
        console.log('[GameScene] 创建 NPC 系统');

        this.dialogueUI = new DialogueUI();
        this.dialogueUI.setSendCallback((npcId, text) => {
            this.handleNpcDialogue(npcId, text);
        });

        const markersLayer = this.map.getObjectLayer('markers');
        if (!markersLayer) {
            console.warn('[GameScene] 未找到 markers 层，无法创建 NPC');
            return;
        }

        // 保存 markers 对象引用（供回调读取 door 坐标等）
        this.markersObjects = markersLayer.objects;

        this.npcManager = new NpcManager(this, markersLayer.objects, this.dialogueUI);
        this.npcManager.createAllNpcs(this.player.x, this.player.y);

        this.setupNpcInteraction();

        this.spaceKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);

        console.log('[GameScene] NPC 系统创建完成');
    }

    /**
     * 设置 NPC 精灵的点击和指针事件
     */
    setupNpcInteraction() {
        if (!this.npcManager || !this.npcManager.npcs) return;

        Object.entries(this.npcManager.npcs).forEach(([npcId, npcData]) => {
            const sprite = npcData.sprite;
            const config = npcData.config;

            sprite.on('pointerdown', () => {
                if (!InteractionManager.isInteractionAllowed()) return;
                this.openNpcDialogue(npcId, config.name);
            });

            sprite.on('pointerover', () => {
                sprite.setTint(0xdddddd);
            });

            sprite.on('pointerout', () => {
                sprite.clearTint();
            });

            console.log(`[GameScene] NPC 交互事件绑定: ${config.name} (${npcId})`);
        });
    }

    /**
     * 设置 NPC tick 定时器（定期同步状态到服务器）
     */
    setupNpcTick() {
        this.tickTimer = setInterval(() => {
            if (this.npcManager) {
                this.npcManager.tickAll();
            }
        }, TICK_INTERVAL);

        console.log(`[GameScene] NPC tick 定时器已启动，间隔 ${TICK_INTERVAL}ms`);
    }

    /**
     * 打开 NPC 对话面板
     */
    openNpcDialogue(npcId, npcName) {
        if (this.shopSystem) this.shopSystem.closeAllPanels();

        InteractionManager.lock('dialogue');

        console.log(`[GameScene] 打开对话: ${npcName} (${npcId})`);

        if (this.dialogueUI) {
            this.dialogueUI.open(npcId, npcName);
        }
    }

    /**
     * 关闭 NPC 对话面板
     */
    closeNpcDialogue() {
        if (this.dialogueUI) {
            this.dialogueUI.close();
        }
    }

    /**
     * 处理 NPC 对话发送
     */
    handleNpcDialogue(npcId, text) {
        if (this.npcManager) {
            this.npcManager.sendDialogue(npcId, text);
        }
    }

    /**
     * 更新 NPC 交互（距离检测 + 空格键交互）
     */
    updateNpcInteraction() {
        if (!this.npcManager) return;

        this.npcManager.update(this.player.x, this.player.y);

        const spaceDown = this.spaceKey && this.spaceKey.isDown;
        if (spaceDown && !this.lastSpaceState) {
            if (this.npcManager.isAnyNpcNearby()) {
                const nearestId = this.npcManager.getNearestNpcId();
                const config = this.npcManager.getNpcConfig(nearestId);
                if (config && (this.dialogueUI?.isOpen !== true || this.dialogueUI?.currentNpcId !== nearestId)) {
                    this.openNpcDialogue(nearestId, config.name);
                }
            }
        }
        this.lastSpaceState = spaceDown;
    }

    /**
     * 注册房间触发回调
     * 当玩家进入 room1/2/3 区域时，对应 NPC 通过寻路走向 door1/2/3
     * room→door 映射和 NPC 的 doorMarker 字段由 npc-config.js 定义
     */
    registerRoomCallbacks() {
        if (!this.roomTriggerCallbacks) {
            console.warn('[GameScene] roomTriggerCallbacks 未初始化');
            return;
        }
        if (!this.npcManager || !this.markersObjects) {
            console.warn('[GameScene] NPC 系统未就绪，跳过房间回调注册');
            return;
        }

        // room → door 映射（游戏业务逻辑）
        const roomToDoorMap = { room1: 'door1', room2: 'door2', room3: 'door3' };

        const self = this;

        ['room1', 'room2', 'room3'].forEach(roomName => {
            this.roomTriggerCallbacks[roomName] = {
                onEnter: (name) => {
                    self._onPlayerEnterRoom(name, roomToDoorMap);
                },
                onLeave: (name) => {
                    self._onPlayerLeaveRoom(name);
                }
            };
        });

        console.log('[GameScene] 房间触发回调注册完成 (room1/2/3 → door1/2/3 → NPC)');
    }

    /**
     * 玩家进入房间：对应 NPC 走到门口
     */
    _onPlayerEnterRoom(roomName, roomToDoorMap) {
        if (!this.npcManager || !this.markersObjects) return;

        // 1. 查找属于该房间的 NPC（doorMarker === roomName）
        const npcEntries = Object.values(this.npcManager.npcs);
        const npcEntry = npcEntries.find(n => n.config.doorMarker === roomName);
        if (!npcEntry) return;

        const npcId = npcEntry.config.id;
        const npcName = npcEntry.config.name;

        // 2. 从 markers 层获取对应门坐标
        const doorName = roomToDoorMap[roomName];
        const doorObj = this.markersObjects.find(obj => obj.name === doorName);
        if (!doorObj) {
            console.warn(`[GameScene] 未找到门对象: ${doorName}`);
            return;
        }

        const doorX = doorObj.x;
        const doorY = doorObj.y;

        console.log(`[GameScene] 玩家进入 ${roomName}，NPC ${npcName} → ${doorName} (${doorX}, ${doorY})`);

        // 2b. 暂停该 NPC 的随机漫游
        this.npcManager.disableRoaming(npcId);

        // 3. 通过寻路计算路径
        if (this.pathfinder) {
            const path = this.pathfinder.findPath(npcEntry.x, npcEntry.y, doorX, doorY);
            if (path && path.length > 0) {
                this.npcManager.setNpcPath(npcId, path);
                console.log(`[GameScene] ${npcName} 路径计算完成，共 ${path.length} 个路径点`);
            } else {
                // 寻路失败 → 直线移动作为降级方案
                console.warn(`[GameScene] ${npcName} 寻路失败，使用直线移动`);
                npcEntry.targetX = doorX;
                npcEntry.targetY = doorY;
                npcEntry.isMoving = true;
            }
        } else {
            // 无 Pathfinder → 直线移动
            npcEntry.targetX = doorX;
            npcEntry.targetY = doorY;
            npcEntry.isMoving = true;
        }
    }

    /**
     * 玩家离开房间：恢复 NPC 随机漫游
     */
    _onPlayerLeaveRoom(roomName) {
        console.log(`[GameScene] 玩家离开 ${roomName}`);

        // 查找该房间对应的 NPC 并恢复漫游
        const npcEntries = Object.values(this.npcManager.npcs);
        const npcEntry = npcEntries.find(n => n.config.doorMarker === roomName);
        if (npcEntry) {
            this.npcManager.enableRoaming(npcEntry.config.id);
        }
    }

    // ===== 委托方法（供 ScriptManager 调用） =====

    /** 重新开始游戏（委托给 ScriptManager） */
    async restartGame() {
        await this.scriptManager.restartGame();
    }

    /** 显示胜利/失败画面（委托给 ScriptManager） */
    showEndScreen(title, story, suspicion) {
        this.scriptManager.showEndScreen(title, story, suspicion);
    }

    // ===== 场景销毁 =====

    shutdown() {
        if (this.tickTimer) {
            clearInterval(this.tickTimer);
            this.tickTimer = null;
        }
        if (this.scriptManager && this.scriptManager._loadingInterval) {
            clearInterval(this.scriptManager._loadingInterval);
            this.scriptManager._loadingInterval = null;
        }
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) loadingOverlay.remove();
        if (this.npcManager) {
            this.npcManager.destroy();
            this.npcManager = null;
        }
        if (this.tradePanel) {
            this.tradePanel.close();
            this.tradePanel = null;
        }
        if (this.dialogueUI) {
            this.dialogueUI.close();
            this.dialogueUI = null;
        }
    }
}
