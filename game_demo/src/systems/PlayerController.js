/**
 * PlayerController - 玩家控制器
 *
 * 职责：
 * - 创建玩家精灵动画（四方向行走动画）
 * - 从 Tiled markers 层读取 playerStart 坐标创建玩家
 * - 设置玩家与地图图层的碰撞
 * - 处理键盘输入（四方向移动 + 动画切换）
 * - 限制玩家在 player_area 范围内移动
 */
export default class PlayerController {
    /**
     * @param {Phaser.Scene} scene - 游戏场景引用
     */
    constructor(scene) {
        this.scene = scene;

        // 玩家移动速度
        this.playerSpeed = 150;

        // 记录最后一次移动方向（用于静止时显示对应帧）
        this.lastDirection = 'down';
    }

    /**
     * 创建玩家动画
     * 精灵图布局：4行×4列，共16帧
     * 第1行：向下走（帧0-3）
     * 第2行：向左走（帧4-7）
     * 第3行：向右走（帧8-11）
     * 第4行：向上走（帧12-15）
     */
    createPlayerAnimations() {
        const scene = this.scene;

        scene.anims.create({
            key: 'walk-down',
            frames: scene.anims.generateFrameNumbers('player', { start: 0, end: 3 }),
            frameRate: 8,
            repeat: -1
        });

        scene.anims.create({
            key: 'walk-left',
            frames: scene.anims.generateFrameNumbers('player', { start: 4, end: 7 }),
            frameRate: 8,
            repeat: -1
        });

        scene.anims.create({
            key: 'walk-right',
            frames: scene.anims.generateFrameNumbers('player', { start: 8, end: 11 }),
            frameRate: 8,
            repeat: -1
        });

        scene.anims.create({
            key: 'walk-up',
            frames: scene.anims.generateFrameNumbers('player', { start: 12, end: 15 }),
            frameRate: 8,
            repeat: -1
        });

        console.log('玩家动画创建完成');
    }

    /**
     * 创建玩家
     * 从 markers 对象层读取 playerStart 坐标
     */
    createPlayer() {
        const scene = this.scene;

        const markersLayer = scene.map.getObjectLayer('markers');
        if (!markersLayer) {
            console.error('未找到 markers 对象层');
            return;
        }

        const playerStart = markersLayer.objects.find(obj => obj.name === 'playerStart');
        if (!playerStart) {
            console.error('未找到 playerStart 对象');
            return;
        }

        // 创建玩家精灵
        scene.player = scene.add.sprite(playerStart.x, playerStart.y, 'player');

        // 创建动画
        this.createPlayerAnimations();

        // 启用物理
        scene.physics.add.existing(scene.player);
        scene.player.body.setCollideWorldBounds(true);
        scene.player.body.setBounce(0);
        scene.player.body.setDrag(500, 500);

        // 调整碰撞体大小
        scene.player.body.setSize(24, 32);
        scene.player.body.setOffset(12, 32);

        // 获取 player_area 对象（玩家移动限制区域）
        scene.playerArea = markersLayer.objects.find(obj => obj.name === 'player_area');
        if (scene.playerArea) {
            console.log('玩家移动限制区域:', scene.playerArea);
        }

        // 设置摄像机
        scene.cameras.main.setBounds(0, 0, scene.map.widthInPixels, scene.map.heightInPixels);
        scene.cameras.main.startFollow(scene.player);
        scene.cameras.main.setZoom(1);

        // 初始化输入
        scene.cursors = scene.input.keyboard.createCursorKeys();

        console.log(`玩家创建成功，起始位置: (${playerStart.x}, ${playerStart.y})`);
    }

    /**
     * 设置碰撞检测
     */
    setupCollisions() {
        const scene = this.scene;

        scene.physics.add.collider(scene.player, scene.wallsLayer);
        scene.physics.add.collider(scene.player, scene.furnituresLayer);

        console.log('碰撞检测设置完成');
    }

    /**
     * 处理玩家输入
     * 支持四方向移动，速度 150
     * 根据移动方向播放对应动画
     */
    handlePlayerInput() {
        const scene = this.scene;

        if (scene.inputLocked) return;

        const body = scene.player.body;
        let velocityX = 0;
        let velocityY = 0;
        let isMoving = false;

        if (scene.cursors.left.isDown) {
            velocityX = -this.playerSpeed;
            scene.player.anims.play('walk-left', true);
            this.lastDirection = 'left';
            isMoving = true;
        } else if (scene.cursors.right.isDown) {
            velocityX = this.playerSpeed;
            scene.player.anims.play('walk-right', true);
            this.lastDirection = 'right';
            isMoving = true;
        }

        if (scene.cursors.up.isDown) {
            velocityY = -this.playerSpeed;
            scene.player.anims.play('walk-up', true);
            this.lastDirection = 'up';
            isMoving = true;
        } else if (scene.cursors.down.isDown) {
            velocityY = this.playerSpeed;
            scene.player.anims.play('walk-down', true);
            this.lastDirection = 'down';
            isMoving = true;
        }

        body.setVelocity(velocityX, velocityY);

        // 如果玩家静止，显示对应方向的静止帧
        if (!isMoving) {
            scene.player.anims.stop();
            switch (this.lastDirection) {
                case 'down':
                    scene.player.setFrame(0);
                    break;
                case 'left':
                    scene.player.setFrame(4);
                    break;
                case 'right':
                    scene.player.setFrame(8);
                    break;
                case 'up':
                    scene.player.setFrame(12);
                    break;
            }
        }
    }

    /**
     * 限制玩家在 player_area 内（硬限制）
     * 如果玩家超出区域，强制拉回
     */
    constrainPlayerToArea() {
        const scene = this.scene;

        if (!scene.playerArea || !scene.player) return;

        const playerX = scene.player.x;
        const playerY = scene.player.y;
        const playerWidth = scene.player.width;
        const playerHeight = scene.player.height;

        const playerLeft = playerX - playerWidth / 2;
        const playerRight = playerX + playerWidth / 2;
        const playerTop = playerY - playerHeight / 2;
        const playerBottom = playerY + playerHeight / 2;

        const areaLeft = scene.playerArea.x;
        const areaRight = scene.playerArea.x + scene.playerArea.width;
        const areaTop = scene.playerArea.y;
        const areaBottom = scene.playerArea.y + scene.playerArea.height;

        let newX = playerX;
        let newY = playerY;

        if (playerLeft < areaLeft) {
            newX = areaLeft + playerWidth / 2;
        }
        if (playerRight > areaRight) {
            newX = areaRight - playerWidth / 2;
        }
        if (playerTop < areaTop) {
            newY = areaTop + playerHeight / 2;
        }
        if (playerBottom > areaBottom) {
            newY = areaBottom - playerHeight / 2;
        }

        if (newX !== playerX || newY !== playerY) {
            scene.player.setPosition(newX, newY);
            scene.player.body.setVelocity(0, 0);
        }
    }
}
