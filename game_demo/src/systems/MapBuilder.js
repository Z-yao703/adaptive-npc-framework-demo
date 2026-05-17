/**
 * MapBuilder - 地图构建与区域管理系统
 *
 * 职责：
 * - 从 Tiled JSON 缓存创建地图、图块集、图层
 * - 设置图层碰撞属性
 * - 创建房间触发区域 (room1/2/3)
 * - 创建交互区域（料理台、杂物柜）及事件处理
 * - 每帧检测房间触发、更新交互光标
 */
import InteractionManager from './InteractionManager.js';

export default class MapBuilder {
    /**
     * @param {Phaser.Scene} scene - 游戏场景引用
     */
    constructor(scene) {
        this.scene = scene;
    }

    /**
     * 创建地图和所有图层
     * 从 Tiled JSON 动态读取所有数据，不硬编码任何数值
     */
    createMap() {
        const scene = this.scene;

        // 创建地图（从 BootScene 加载的缓存中读取）
        scene.map = scene.make.tilemap({ key: 'map' });

        // 遍历 JSON 中的所有图块集，动态添加
        const tilesets = [];
        const tilesetNames = ['hotel', 'room', 'room2', 'r3', 'r4'];

        tilesetNames.forEach(name => {
            const tileset = scene.map.addTilesetImage(name);
            if (tileset) {
                tilesets.push(tileset);
                console.log(`图块集加载成功: ${name}`);
            } else {
                console.warn(`图块集加载失败: ${name}`);
            }
        });

        // 按顺序创建图层（从下到上）
        scene.floorLayer = scene.map.createLayer('floor', tilesets);
        scene.wallsLayer = scene.map.createLayer('walls', tilesets);
        scene.furnituresLayer = scene.map.createLayer('furnitures', tilesets);

        // 设置墙壁和家具图层的碰撞（基于 Tiled 中设置的 collides 属性）
        scene.wallsLayer.setCollisionByProperty({ collides: true });
        scene.furnituresLayer.setCollisionByProperty({ collides: true });

        console.log('地图创建完成');
        console.log('墙壁图层碰撞 tiles:', scene.wallsLayer.filterTiles(tile => tile.index > 0).length);
        console.log('家具图层碰撞 tiles:', scene.furnituresLayer.filterTiles(tile => tile.index > 0).length);
    }

    /**
     * 创建房间触发区域
     * 从 markers 对象层读取 room1/room2/room3 矩形对象
     * 当玩家与这些区域重叠时触发事件
     */
    createRoomTriggers() {
        const scene = this.scene;
        const markersLayer = scene.map.getObjectLayer('markers');
        if (!markersLayer) return;

        scene.roomTriggers = [];

        // 初始化房间触发回调存储（由 GameScene 注册业务逻辑）
        scene.roomTriggerCallbacks = scene.roomTriggerCallbacks || {};

        ['room1', 'room2', 'room3'].forEach(roomName => {
            const room = markersLayer.objects.find(obj => obj.name === roomName);
            if (room) {
                const triggerZone = scene.add.zone(
                    room.x + room.width / 2,
                    room.y + room.height / 2,
                    room.width,
                    room.height
                );
                scene.physics.add.existing(triggerZone, true);

                scene.roomTriggers.push({
                    name: roomName,
                    zone: triggerZone,
                    triggered: false
                });

                console.log(`房间触发区域创建: ${roomName}, 位置: (${room.x}, ${room.y}), 尺寸: ${room.width}x${room.height}`);
            }
        });
    }

    /**
     * 创建交互区域（料理台、杂物柜）
     * 从 markers 对象层读取 kitchen_counter 和 supply_closet
     * 设置为可交互区域，监听 pointerdown 事件
     */
    createInteractZones() {
        const scene = this.scene;
        const markersLayer = scene.map.getObjectLayer('markers');
        if (!markersLayer) {
            console.warn('未找到 markers 对象层');
            return;
        }

        scene.interactZones = scene.interactZones || [];

        const zoneConfigs = [
            { name: 'kitchen_counter', type: 'food', title: '料理购买' },
            { name: 'supply_closet', type: 'supply', title: '杂物购买' }
        ];

        const self = this;

        zoneConfigs.forEach(config => {
            const zoneObj = markersLayer.objects.find(obj => obj.name === config.name);
            if (zoneObj) {
                const zone = scene.add.zone(
                    zoneObj.x + zoneObj.width / 2,
                    zoneObj.y + zoneObj.height / 2,
                    zoneObj.width,
                    zoneObj.height
                );
                scene.physics.add.existing(zone, true);

                zone.setInteractive({ useHandCursor: false });

                scene.interactZones.push({
                    name: config.name,
                    type: config.type,
                    title: config.title,
                    zone: zone,
                    zoneObj: zoneObj
                });

                console.log(`交互区域创建: ${config.name}, 位置: (${zoneObj.x}, ${zoneObj.y}), 尺寸: ${zoneObj.width}x${zoneObj.height}`);

                // 监听指针事件
                zone.on('pointerdown', () => {
                    self.handleZoneClick(config.name, config.type, config.title);
                });

                zone.on('pointerover', () => {
                    self.handleZoneHover(config.name, true);
                });

                zone.on('pointerout', () => {
                    self.handleZoneHover(config.name, false);
                });
            } else {
                console.warn(`未在 Tiled 中找到对象: ${config.name}`);
            }
        });
    }

    /**
     * 计算玩家与交互区域中心的距离
     * @param {object} zone - Phaser Zone 对象
     * @returns {number} 距离（像素）
     */
    getDistanceToZone(zone) {
        const player = this.scene.player;
        if (!player) return Infinity;
        const dx = player.x - zone.x;
        const dy = player.y - zone.y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    /**
     * 处理交互区域悬停
     * 根据距离决定是否显示 pointer 光标
     */
    handleZoneHover(zoneName, isOver) {
        const zoneData = this.scene.interactZones.find(z => z.name === zoneName);
        if (!zoneData) return;

        const distance = this.getDistanceToZone(zoneData.zone);
        const canInteract = distance <= 150;

        zoneData.zone.input.handCursor = canInteract ? true : false;
    }

    /**
     * 处理交互区域点击
     * 只有距离 <= 150px 时才能触发购买
     */
    handleZoneClick(zoneName, zoneType, zoneTitle) {
        if (!InteractionManager.isInteractionAllowed()) return;

        const zoneData = this.scene.interactZones.find(z => z.name === zoneName);
        if (!zoneData) return;

        const distance = this.getDistanceToZone(zoneData.zone);
        if (distance > 150) {
            console.log(`距离太远，无法交互（距离: ${distance.toFixed(0)}px）`);
            return;
        }

        console.log(`点击交互区域: ${zoneName}, 类型: ${zoneType}`);

        // 关闭背包和推论面板，打开购买面板
        const shop = this.scene.shopSystem;
        if (shop) {
            shop.closeAllPanels();
            shop.openPurchasePanel(zoneType, zoneTitle);
        }
    }

    /**
     * 每帧更新交互区域的光标状态
     * 根据玩家与区域的距离决定是否显示 pointer 光标
     */
    updateInteractCursors() {
        const zones = this.scene.interactZones;
        if (!zones) return;

        zones.forEach(zoneData => {
            const distance = this.getDistanceToZone(zoneData.zone);
            const canInteract = distance <= 64;

            if (zoneData.zone.input) {
                zoneData.zone.input.handCursor = canInteract;
            }
        });
    }

    /**
     * 检测房间触发
     * 当玩家与 room1/2/3 区域重叠时，在控制台打印信息
     */
    checkRoomTriggers() {
        const player = this.scene.player;
        const triggers = this.scene.roomTriggers;
        if (!player || !triggers) return;

        triggers.forEach(trigger => {
            const zone = trigger.zone;
            const playerX = player.x;
            const playerY = player.y;
            const playerWidth = player.width;
            const playerHeight = player.height;

            const playerLeft = playerX - playerWidth / 2;
            const playerRight = playerX + playerWidth / 2;
            const playerTop = playerY - playerHeight / 2;
            const playerBottom = playerY + playerHeight / 2;

            const zoneLeft = zone.x - zone.width / 2;
            const zoneRight = zone.x + zone.width / 2;
            const zoneTop = zone.y - zone.height / 2;
            const zoneBottom = zone.y + zone.height / 2;

            const isOverlapping = !(
                playerLeft > zoneRight ||
                playerRight < zoneLeft ||
                playerTop > zoneBottom ||
                playerBottom < zoneTop
            );

            if (isOverlapping && !trigger.triggered) {
                trigger.triggered = true;
                console.log(`靠近房门 ${trigger.name.replace('room', '')}`);
                // 调用业务层注册的进入回调
                const cb = this.scene.roomTriggerCallbacks?.[trigger.name];
                if (cb?.onEnter) cb.onEnter(trigger.name);
            } else if (!isOverlapping && trigger.triggered) {
                trigger.triggered = false;
                // 调用业务层注册的离开回调
                const cb = this.scene.roomTriggerCallbacks?.[trigger.name];
                if (cb?.onLeave) cb.onLeave(trigger.name);
            }
        });
    }

    /**
     * 从 Phaser tilemap 构建碰撞网格（游戏特定逻辑）
     * 遍历 walls 和 furnitures 图层，将标记了 collides: true 的 tile 记为阻挡
     * @returns {number[][]} 二维数组，0=可走，1=阻挡；grid[row][col]
     */
    buildCollisionGrid() {
        const scene = this.scene;
        if (!scene.map || !scene.wallsLayer) {
            console.warn('[MapBuilder] 地图未就绪，无法构建碰撞网格');
            return [];
        }

        const mapWidth = scene.map.width;
        const mapHeight = scene.map.height;
        const grid = [];

        for (let row = 0; row < mapHeight; row++) {
            const rowData = [];
            for (let col = 0; col < mapWidth; col++) {
                const wallTile = scene.wallsLayer.getTileAt(col, row);
                const furnTile = scene.furnituresLayer.getTileAt(col, row);

                const blocked = (wallTile && wallTile.collides) ||
                                (furnTile && furnTile.collides);
                rowData.push(blocked ? 1 : 0);
            }
            grid.push(rowData);
        }

        console.log(`[MapBuilder] 碰撞网格构建完成: ${mapWidth}x${mapHeight}`);
        return grid;
    }
}
