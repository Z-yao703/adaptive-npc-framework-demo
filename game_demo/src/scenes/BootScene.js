/**
 * BootScene - 资源加载场景
 * 负责加载地图 JSON 和所有图片素材
 * 动态修改 JSON 中的图片路径以匹配项目结构
 */
import { API_BASE, PLAYER_ID } from '../config/npc-config.js';

export default class BootScene extends Phaser.Scene {
    constructor() {
        super({ key: 'BootScene' });
    }

    preload() {
        console.log('BootScene preload 开始');

        // 显示加载进度
        const width = this.cameras.main.width;
        const height = this.cameras.main.height;

        const progressBar = this.add.graphics();
        const progressBox = this.add.graphics();
        // 使用主色1作为进度框背景色
        progressBox.fillStyle(0x5D4037, 0.8);
        progressBox.fillRect(width / 2 - 160, height / 2 - 25, 320, 50);

        const loadingText = this.make.text({
            x: width / 2,
            y: height / 2 - 50,
            text: '加载中...',
            style: {
                font: '20px monospace',
                fill: '#ffffff'  // 文本色1
            }
        });
        loadingText.setOrigin(0.5, 0.5);

        const percentText = this.make.text({
            x: width / 2,
            y: height / 2,
            text: '0%',
            style: {
                font: '18px monospace',
                fill: '#ffffff'  // 文本色1
            }
        });
        percentText.setOrigin(0.5, 0.5);

        this.load.on('progress', (value) => {
            percentText.setText(parseInt(value * 100) + '%');
            progressBar.clear();
            // 使用主色2作为进度条填充色
            progressBar.fillStyle(0x8D6E63, 1);
            progressBar.fillRect(width / 2 - 150, height / 2 - 15, 300 * value, 30);
        });

        this.load.on('complete', () => {
            console.log('资源加载完成');
            progressBar.destroy();
            progressBox.destroy();
            loadingText.destroy();
            percentText.destroy();
        });

        // 加载地图 JSON（使用 Phaser 的 loader）
        this.load.tilemapTiledJSON('map', '/assets/maps/hotel_map.json');

        // 加载所有图块集图片
        // 图片 key 必须与 Tiled 中的图块集名称一致
        this.load.image('hotel', '/assets/images/floorswalls_LRK.png');
        this.load.image('room', '/assets/images/tilesheet_itchio.png');
        this.load.image('room2', '/assets/images/livingroom_LRK.png');
        this.load.image('r3', '/assets/images/kitchen_LRK.png');
        this.load.image('r4', '/assets/images/Interiors_free_32x32.png');

        // 加载玩家精灵图（spritesheet）
        // 图片尺寸：192×256，4行4列，每帧 48×64 像素
        this.load.spritesheet('player', '/assets/images/player.png', {
            frameWidth: 48,
            frameHeight: 64
        });
    }

    async create() {
        console.log('BootScene 创建完成');

        this.generateNpcPlaceholderTextures();

        await this.initGameState();

        console.log('启动 GameScene');
        this.scene.start('GameScene');
    }

    /**
     * 动态生成 NPC 占位精灵图纹理
     * 为每个 NPC 创建一个纯色块纹理，无需外部图片文件
     */
    generateNpcPlaceholderTextures() {
        const npcSizes = [
            { key: 'npc_placeholder_1', color: 0xff6b6b, size: 32 },  // 红色（小王）
            { key: 'npc_placeholder_2', color: 0x4ecdc4, size: 32 },  // 青色（猫）
            { key: 'npc_placeholder_3', color: 0xffd93d, size: 32 }   // 黄色（大强）
        ];

        npcSizes.forEach(({ key, color, size }) => {
            const canvas = this.textures.createCanvas(key, size, size);
            const ctx = canvas.getContext();
            // 绘制圆角矩形
            ctx.fillStyle = '#' + color.toString(16).padStart(6, '0');
            ctx.beginPath();
            ctx.arc(size / 2, size / 2, size / 2 - 1, 0, Math.PI * 2);
            ctx.fill();
            // 绘制外边框
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1.5;
            ctx.stroke();
            // 绘制名称首字母
            canvas.refresh();
        });

        // 生成交互提示图标（小圆点）
        const hintCanvas = this.textures.createCanvas('npc_hint', 16, 16);
        const hintCtx = hintCanvas.getContext();
        hintCtx.fillStyle = '#4cc9f0';
        hintCtx.beginPath();
        hintCtx.arc(8, 8, 7, 0, Math.PI * 2);
        hintCtx.fill();
        hintCtx.strokeStyle = '#ffffff';
        hintCtx.lineWidth = 1;
        hintCtx.stroke();
        hintCanvas.refresh();

        console.log('NPC 占位纹理生成完成');
    }

    /**
     * 初始化全局玩家数据（从后端 API 加载金币和背包）
     * 物品目录本地定义，金币和背包数量从数据库加载
     */
    async initGameState() {
        const defaultState = {
            gold: 100,
            foods: {
                '牛油果冷豆腐': { count: 0, buyPrice: 15, sellPrice: 30 },
                '牛乳可可饮': { count: 0, buyPrice: 5, sellPrice: 10 },
                '树莓乳酪贝果': { count: 0, buyPrice: 9, sellPrice: 18 },
                '牛油小火锅': { count: 0, buyPrice: 35, sellPrice: 70 },
                '火热拉面': { count: 0, buyPrice: 6, sellPrice: 12 }
            },
            supplies: {
                '毛巾': { count: 0, buyPrice: 12, sellPrice: 20 },
                '香皂': { count: 0, buyPrice: 3, sellPrice: 9 },
                '神奇魔法书': { count: 0, buyPrice: 15, sellPrice: 35 },
                '影视磁带': { count: 0, buyPrice: 9, sellPrice: 26 },
                '健身房一天卡': { count: 0, buyPrice: 5, sellPrice: 8 }
            },
            // 任务/暗号物品
            questItems: {
                '玫瑰': { count: 0, type: 'quest' },
                '薄荷叶': { count: 0, type: 'quest' },
                '猪肉': { count: 0, type: 'quest' },
                '黑鱼': { count: 0, type: 'quest' },
                '复活药水': { count: 0, type: 'potion' }
            },
            // 活跃任务
            activeQuests: {},

            // ===== 便捷方法 =====
            addQuestItem(itemName, quantity = 1) {
                if (!this.questItems[itemName]) {
                    this.questItems[itemName] = { count: 0, type: 'quest' };
                }
                this.questItems[itemName].count += quantity;
                console.log(`[GameState] 获得物品: ${itemName} x${quantity} (当前: ${this.questItems[itemName].count})`);
                // 同步绝对数量到数据库
                this._syncItemToDB(itemName, 'quest', this.questItems[itemName].count);
            },

            removeQuestItem(itemName, quantity = 1) {
                if (this.questItems[itemName]) {
                    this.questItems[itemName].count = Math.max(0, this.questItems[itemName].count - quantity);
                    console.log(`[GameState] 失去物品: ${itemName} x${quantity} (剩余: ${this.questItems[itemName].count})`);
                    // 同步绝对数量到数据库（包括 count=0 以触发删除）
                    this._syncItemToDB(itemName, 'quest', this.questItems[itemName].count);
                }
            },

            addActiveQuest(questId, title, description) {
                this.activeQuests[questId] = { id: questId, title, description, stage: 1 };
                console.log(`[GameState] 接取任务: ${title} (${questId})`);
            },

            updateQuestStage(questId, stage) {
                if (this.activeQuests[questId]) {
                    this.activeQuests[questId].stage = stage;
                    console.log(`[GameState] 任务 ${questId} 更新到阶段 ${stage}`);
                }
            },

            addGold(amount) {
                this.gold += amount;
                console.log(`[GameState] 获得金币: +${amount} (当前: ${this.gold})`);
                this._syncGoldToDB(this.gold);
            },

            async _syncItemToDB(itemName, itemType, count) {
                try {
                    const { API_BASE, PLAYER_ID } = await import('../config/npc-config.js');
                    // 使用 set_item 端点发送绝对数量，后端自动处理 count=0 的删除
                    await fetch(`${API_BASE}/api/player/${PLAYER_ID}/set_item`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ item_name: itemName, item_type: itemType, count: count })
                    });
                } catch (err) {
                    console.warn('[GameState] 物品同步失败:', err.message);
                }
            },

            async _syncGoldToDB(gold) {
                try {
                    const { API_BASE, PLAYER_ID } = await import('../config/npc-config.js');
                    await fetch(`${API_BASE}/api/player/${PLAYER_ID}/gold`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ gold: gold })
                    });
                } catch (err) {
                    console.warn('[GameState] 金币同步失败:', err.message);
                }
            }
        };

        try {
            const resp = await fetch(`${API_BASE}/api/player/${PLAYER_ID}`);
            const data = await resp.json();

            defaultState.gold = data.gold || 100;

            if (data.inventory) {
                Object.values(data.inventory).forEach(item => {
                    if (item.type === 'food' && defaultState.foods[item.name]) {
                        defaultState.foods[item.name].count = item.count;
                    } else if (item.type === 'supply' && defaultState.supplies[item.name]) {
                        defaultState.supplies[item.name].count = item.count;
                    } else if (item.type === 'quest' || item.type === 'potion') {
                        if (defaultState.questItems[item.name]) {
                            defaultState.questItems[item.name].count = item.count;
                        } else {
                            defaultState.questItems[item.name] = { count: item.count, type: item.type };
                        }
                    }
                });
            }

            console.log('从数据库加载玩家数据，金币:', defaultState.gold);
        } catch (err) {
            console.warn('无法连接后端，使用默认玩家数据:', err.message);
        }

        window.gameState = defaultState;
        console.log('游戏状态初始化完成，金币:', window.gameState.gold);
    }
}
