// 导入 Phaser
import Phaser from 'phaser';
// 导入场景
import BootScene from './scenes/BootScene.js';
import GameScene from './scenes/GameScene.js';

// 游戏配置
const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 480,
    parent: 'game-container',
    backgroundColor: '#263238',
    physics: {
        default: 'arcade',
        arcade: {
            debug: true,  // 设为 true 可查看碰撞区域
            gravity: { y: 0 }  // 俯视角游戏，无重力
        }
    },
    scene: [BootScene, GameScene]
};

// 创建游戏实例
const game = new Phaser.Game(config);

// 导出游戏实例供其他模块使用
export default game;
