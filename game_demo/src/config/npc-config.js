/**
 * NPC 配置集中管理模块
 * 
 * 所有 NPC 相关的 ID、名字、markers 映射等常量在此定义
 * 修改 NPC 只需改这一个文件
 */
export const NPC_CONFIGS = [
    {
        id: 'npc_1778601114006',
        name: '吱呜',
        markerName: 'npc1',       // hotel_map.json markers 层中的对象名
        doorMarker: 'room1',      // 对应房间 marker 名
        color: 0xff6b6b            // Phaser 中使用的颜色块（红色系）
    },
    {
        id: 'npc_1778602052720',
        name: '咚呜',
        markerName: 'npc2',
        doorMarker: 'room2',
        color: 0x4ecdc4            // 青色系
    },
    {
        id: 'npc_1778602532658',
        name: '壬呜',
        markerName: 'npc3',
        doorMarker: 'room3',
        color: 0xffd93d            // 黄色系
    }
];

/** 玩家 ID */
export const PLAYER_ID = 'player_001';

/** NPC 对话触发距离（像素） */
export const NEAR_DISTANCE = 80;

/** AgentBridge tick 间隔（毫秒） */
export const TICK_INTERVAL = 350;

/** WebSocket 服务器地址 */
export const SERVER_URL = 'ws://localhost:8000';

/** HTTP API 基础地址 */
export const API_BASE = 'http://localhost:8000';

/** 获取 NPC 配置的辅助函数 */
export function getNpcConfigById(id) {
    return NPC_CONFIGS.find(c => c.id === id);
}

export function getNpcConfigByMarkerName(markerName) {
    return NPC_CONFIGS.find(c => c.markerName === markerName);
}
