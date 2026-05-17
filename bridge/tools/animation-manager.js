/**
 * AnimationManager - 框架动画基础设施
 *
 * 设计原则：
 * - 从 render_cfg.animations 配置创建动画，支持 Phaser 和 Canvas 双模式
 * - 内置声明式 FALLBACK_STRATEGY 回退表，处理缺失方向的容错
 * - 游戏开发者仅需传入配置和纹理，框架负责动画创建与播放
 *
 * 使用示例（Phaser 模式）：
 * ```javascript
 * const animMgr = new AnimationManager({
 *     scene: this.scene,
 *     spriteKey: 'npc_village_chief'
 * });
 * const animKeyMap = animMgr.createFromConfig(renderCfg);
 * animMgr.play(sprite, 'walk', 'right', animKeyMap);
 * ```
 *
 * 使用示例（Canvas 模式）：
 * ```javascript
 * const animMgr = new AnimationManager({});
 * const resolved = animMgr.createFromConfig(renderCfg);
 * const frame = animMgr.getCanvasFrame('walk', 'left', resolved);
 * const flip = animMgr.getCanvasFlip('walk', 'left', resolved);
 * ```
 */

// =========================================
// 常量定义
// =========================================

/** 四方向 */
export const DIRECTIONS = ['down', 'left', 'right', 'up'];

/** 动作类型 */
export const ACTIONS = ['idle', 'walk'];

/**
 * 声明式回退策略表
 *
 * 当某个方向的动画帧缺失时，按以下策略自动回退：
 *   左缺 → 镜像右（flipX）
 *   右缺 → 镜像左（flipX）
 *   上缺 → 复用下
 *   下缺 → 复用上
 *
 * 相比 if/else 级联，表格驱动策略更易扩展、测试和审查
 */
const FALLBACK_STRATEGY = {
    left:  { source: 'right', transform: 'flipX' },
    right: { source: 'left',  transform: 'flipX' },
    up:    { source: 'down',  transform: null },
    down:  { source: 'up',    transform: null }
};

// =========================================
// AnimationManager 类
// =========================================

export class AnimationManager {

    /**
     * @param {Object} options
     * @param {Phaser.Scene} [options.scene]  - Phaser 场景引用（Phaser 模式必须）
     * @param {string} [options.spriteKey]    - 精灵图 Phaser 纹理 key
     * @param {number} [options.frameWidth]   - 单帧宽度（默认 48）
     * @param {number} [options.frameHeight]  - 单帧高度（默认 64）
     */
    constructor(options = {}) {
        this.scene = options.scene || null;
        this.spriteKey = options.spriteKey || 'default_sprite';
        this.frameWidth = options.frameWidth || 48;
        this.frameHeight = options.frameHeight || 64;

        /** @private 存储最近一次 createFromConfig 的解析结果 */
        this._resolved = null;
    }

    // =========================================
    // 核心方法：从配置创建动画
    // =========================================

    /**
     * 从 render_cfg 创建所有 8 个方向动画
     *
     * @param {Object} renderCfg - 包含 animations 的渲染配置
     *   { frameWidth, frameHeight, scale, animations: { idle_down: [0,1], ... } }
     * @returns {Object} animKeyMap - { idle_down: 'spriteKey_idle_down', ... }
     *   或 Canvas 模式下返回帧范围 { idle_down: { frames: [0,1], transform: null }, ... }
     */
    createFromConfig(renderCfg) {
        const cfg = renderCfg || {};
        this.frameWidth = cfg.frameWidth || this.frameWidth;
        this.frameHeight = cfg.frameHeight || this.frameHeight;

        const animations = cfg.animations || {};
        const resolved = this._resolveAll(animations);
        this._resolved = resolved; // 保存供 play() 等方法使用

        if (this.scene) {
            return this._createPhaserAnimations(resolved);
        }
        return resolved;
    }

    /**
     * 播放动画（Phaser 模式）
     *
     * @param {Phaser.GameObjects.Sprite} sprite - NPC/玩家精灵
     * @param {string} action    - 'idle' | 'walk'
     * @param {string} direction - 'down' | 'left' | 'right' | 'up'
     * @param {Object} [animKeyMap] - createFromConfig 返回的 key 映射（可选，优先使用）
     */
    play(sprite, action, direction, animKeyMap) {
        if (!sprite) return;

        const key = `${action}_${direction}`;
        const dirInfo = this._resolved?.[key];
        if (!dirInfo) return;

        // 处理翻转
        sprite.setFlipX(dirInfo.transform === 'flipX');
        sprite.setFlipY(false);

        // 单帧动画（start === end）：停止动画，直接设置帧
        const frames = dirInfo.frames || [0, 0];
        if (frames[0] === frames[1]) {
            sprite.anims?.stop();
            sprite.setFrame(frames[0]);
            return;
        }

        // 多帧动画：播放 Phaser 动画
        if (animKeyMap) {
            const phaserKey = animKeyMap[key];
            if (phaserKey && this.scene?.anims?.exists(phaserKey)) {
                sprite.anims?.play(phaserKey, true);
            }
        }
    }

    /**
     * 获取指定方向的静止帧索引（用于 idle 静止帧）
     * @param {string} direction - 'down' | 'left' | 'right' | 'up'
     * @returns {number} 帧索引
     */
    getIdleFrame(direction) {
        const key = `idle_${direction}`;
        const info = this._resolved?.[key];
        return info?.frames?.[0] || 0;
    }

    // =========================================
    // Canvas 模式辅助方法
    // =========================================

    /**
     * 获取 Canvas 渲染帧索引
     * @param {string} action    - 'idle' | 'walk'
     * @param {string} direction - 'down' | 'left' | 'right' | 'up'
     * @param {Object} resolved  - createFromConfig 返回的解析结果
     * @param {number} animIndex - 动画进度索引（用于帧循环）
     * @returns {number} 帧索引
     */
    getCanvasFrame(action, direction, resolved, animIndex = 0) {
        const key = `${action}_${direction}`;
        const info = (resolved || this._resolved)?.[key];
        if (!info) return 0;
        const [start, end] = info.frames || [0, 0];
        if (start === end) return start;
        return start + (animIndex % (end - start + 1));
    }

    /**
     * 获取 Canvas 渲染翻转标志
     * @param {string} action    - 'idle' | 'walk'
     * @param {string} direction - 'down' | 'left' | 'right' | 'up'
     * @param {Object} resolved  - createFromConfig 返回的解析结果
     * @returns {boolean} 是否需要水平翻转
     */
    getCanvasFlip(action, direction, resolved) {
        const key = `${action}_${direction}`;
        const info = (resolved || this._resolved)?.[key];
        return info?.transform === 'flipX';
    }

    // =========================================
    // 内部解析方法
    // =========================================

    /**
     * 全局解析：遍历 2 action × 4 direction = 8 种组合
     */
    _resolveAll(animations) {
        const result = {};
        for (const action of ACTIONS) {
            for (const dir of DIRECTIONS) {
                const key = `${action}_${dir}`;
                result[key] = this._resolveOne(action, dir, animations);
            }
        }
        return result;
    }

    /**
     * 单方向容错解析 —— 5 级回退策略：
     *
     * L1: 精确匹配（idle_left 已配置）→ 直接使用
     * L2: direction 回退（left 缺 → right + flipX，依据 FALLBACK_STRATEGY）
     * L3: cross-action 回退（walk_left 缺 → 用 idle_left）
     * L4: cross-action + direction 回退（walk_left 缺 → idle_right + flipX）
     * L5: 全局兜底 → frames: [0, 0]
     *
     * @returns {{ frames: number[], transform: string|null, source: string }}
     */
    _resolveOne(action, direction, animations) {
        const exactKey = `${action}_${direction}`;

        // L1: 精确匹配
        if (animations[exactKey] && Array.isArray(animations[exactKey]) && animations[exactKey].length >= 2) {
            return {
                frames: [animations[exactKey][0], animations[exactKey][1]],
                transform: null,
                source: 'exact'
            };
        }

        // L2: direction 回退
        const strategy = FALLBACK_STRATEGY[direction];
        if (strategy) {
            const fallbackKey = `${action}_${strategy.source}`;
            if (animations[fallbackKey] && Array.isArray(animations[fallbackKey]) && animations[fallbackKey].length >= 2) {
                return {
                    frames: [animations[fallbackKey][0], animations[fallbackKey][1]],
                    transform: strategy.transform,
                    source: 'direction_fallback'
                };
            }
        }

        // L3: cross-action 回退（walk 缺用 idle，idle 缺用 walk）
        const otherAction = action === 'walk' ? 'idle' : 'walk';
        const crossKey = `${otherAction}_${direction}`;
        if (animations[crossKey] && Array.isArray(animations[crossKey]) && animations[crossKey].length >= 2) {
            return {
                frames: [animations[crossKey][0], animations[crossKey][1]],
                transform: null,
                source: 'cross_action'
            };
        }

        // L4: cross-action + direction 回退
        if (strategy) {
            const crossFallbackKey = `${otherAction}_${strategy.source}`;
            if (animations[crossFallbackKey] && Array.isArray(animations[crossFallbackKey]) && animations[crossFallbackKey].length >= 2) {
                return {
                    frames: [animations[crossFallbackKey][0], animations[crossFallbackKey][1]],
                    transform: strategy.transform,
                    source: 'cross_action_direction'
                };
            }
        }

        // L5: 全局兜底
        return {
            frames: [0, 0],
            transform: null,
            source: 'fallback'
        };
    }

    /**
     * 创建 Phaser 动画
     * @returns {Object} animKeyMap
     */
    _createPhaserAnimations(resolved) {
        const animKeyMap = {};
        for (const key of Object.keys(resolved)) {
            const { frames } = resolved[key];
            const uniqueKey = `${this.spriteKey}_${key}`;

            if (frames[0] === frames[1]) {
                // 单帧：不需要 Phaser 动画，播放时用 setFrame
                animKeyMap[key] = uniqueKey;
                continue;
            }

            if (this.scene.anims.exists(uniqueKey)) {
                this.scene.anims.remove(uniqueKey);
            }

            this.scene.anims.create({
                key: uniqueKey,
                frames: this.scene.anims.generateFrameNumbers(this.spriteKey, {
                    start: frames[0],
                    end: frames[1]
                }),
                frameRate: 8,
                repeat: -1
            });

            animKeyMap[key] = uniqueKey;
        }
        return animKeyMap;
    }

    /**
     * 获取当前解析结果（供外部调试/审查）
     */
    getResolved() {
        return this._resolved;
    }
}

// ES Module 导出
export default AnimationManager;
