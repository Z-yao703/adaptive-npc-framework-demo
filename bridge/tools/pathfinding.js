/**
 * Pathfinder - 寻路工具模块（框架提供的基础设施）
 *
 * 设计原则：
 * - 纯 JS 模块，不依赖任何游戏引擎
 * - 接收简单的碰撞网格数据，返回像素坐标路径点列表
 * - 游戏层负责构建碰撞网格并解释路径
 *
 * 使用示例：
 * ```javascript
 * import { Pathfinder } from '../bridge/tools/pathfinding.js';
 * const pf = new Pathfinder(collisionGrid, 32);
 * const path = pf.findPath(npcX, npcY, doorX, doorY);
 * ```
 */
export class Pathfinder {
    /**
     * @param {number[][]} grid - 二维数组，0=可走，1=阻挡；grid[row][col]
     * @param {number} cellSize - 每格像素尺寸，默认 32
     */
    constructor(grid, cellSize = 32) {
        this.grid = grid;
        this.cellSize = cellSize;
        this.width = grid[0]?.length || 0;
        this.height = grid.length;
    }

    /**
     * 像素坐标 → 网格坐标
     */
    _toGrid(px) {
        return Math.floor(px / this.cellSize);
    }

    /**
     * 网格坐标 → 像素坐标（格中心）
     */
    _toPixel(gx, gy) {
        return {
            x: (gx + 0.5) * this.cellSize,
            y: (gy + 0.5) * this.cellSize
        };
    }

    /**
     * 检查网格单元是否可走
     */
    _isWalkable(gx, gy) {
        if (gx < 0 || gx >= this.width || gy < 0 || gy >= this.height) return false;
        return this.grid[gy][gx] === 0;
    }

    /**
     * 曼哈顿距离启发函数
     */
    _heuristic(ax, ay, bx, by) {
        return Math.abs(ax - bx) + Math.abs(ay - by);
    }

    /**
     * A* 寻路
     * @param {number} startX - 起始像素X
     * @param {number} startY - 起始像素Y
     * @param {number} endX - 目标像素X
     * @param {number} endY - 目标像素Y
     * @returns {Array<{x: number, y: number}>} 路径点列表（像素坐标），空数组表示不可达
     */
    findPath(startX, startY, endX, endY) {
        const startGX = this._toGrid(startX);
        const startGY = this._toGrid(startY);
        const endGX = this._toGrid(endX);
        const endGY = this._toGrid(endY);

        // 起终点同格 → 直达
        if (startGX === endGX && startGY === endGY) {
            return [{ x: endX, y: endY }];
        }

        // 起终点不可走 → 返回空
        if (!this._isWalkable(startGX, startGY)) {
            return [];
        }
        if (!this._isWalkable(endGX, endGY)) {
            return [];
        }

        // A* 搜索
        const openSet = new Map();
        const closedSet = new Set();
        const gScore = new Map();
        const cameFrom = new Map();

        const startKey = `${startGX},${startGY}`;
        const endKey = `${endGX},${endGY}`;

        openSet.set(startKey, this._heuristic(startGX, startGY, endGX, endGY));
        gScore.set(startKey, 0);

        const dirs = [[0, -1], [1, 0], [0, 1], [-1, 0]];

        while (openSet.size > 0) {
            // 取 f 值最小的节点
            let currentKey = null;
            let minF = Infinity;
            for (const [key, f] of openSet) {
                if (f < minF) {
                    minF = f;
                    currentKey = key;
                }
            }

            if (currentKey === endKey) {
                // 到达终点，回溯路径
                return this._reconstructPath(cameFrom, endGX, endGY);
            }

            openSet.delete(currentKey);
            closedSet.add(currentKey);

            const [cx, cy] = currentKey.split(',').map(Number);
            const currentG = gScore.get(currentKey);

            for (const [dx, dy] of dirs) {
                const nx = cx + dx;
                const ny = cy + dy;
                const neighborKey = `${nx},${ny}`;

                if (closedSet.has(neighborKey)) continue;
                if (!this._isWalkable(nx, ny)) continue;

                const tentativeG = currentG + 1;

                if (!gScore.has(neighborKey) || tentativeG < gScore.get(neighborKey)) {
                    cameFrom.set(neighborKey, currentKey);
                    gScore.set(neighborKey, tentativeG);
                    const f = tentativeG + this._heuristic(nx, ny, endGX, endGY);
                    openSet.set(neighborKey, f);
                }
            }
        }

        // 不可达
        console.warn(`[Pathfinder] 不可达: (${startGX},${startGY}) → (${endGX},${endGY})`);
        return [];
    }

    /**
     * 回溯构建像素坐标路径
     */
    _reconstructPath(cameFrom, endGX, endGY) {
        const path = [];
        let current = `${endGX},${endGY}`;
        const startKey = cameFrom.keys().next().value; // won't be used

        // 先收集网格坐标
        const gridPath = [[endGX, endGY]];
        while (cameFrom.has(current)) {
            current = cameFrom.get(current);
            const [gx, gy] = current.split(',').map(Number);
            gridPath.unshift([gx, gy]);
        }

        // 转为像素坐标（格中心）并简化
        return this._simplifyPath(gridPath);
    }

    /**
     * 简化路径：去除共线的中间点
     * 保留起点、转折点、终点
     */
    _simplifyPath(gridPath) {
        if (gridPath.length <= 2) {
            return gridPath.map(([gx, gy]) => this._toPixel(gx, gy));
        }

        const simplified = [gridPath[0]];
        for (let i = 1; i < gridPath.length - 1; i++) {
            const prev = gridPath[i - 1];
            const curr = gridPath[i];
            const next = gridPath[i + 1];

            // 如果三点不共线，保留curr
            const dx1 = curr[0] - prev[0];
            const dy1 = curr[1] - prev[1];
            const dx2 = next[0] - curr[0];
            const dy2 = next[1] - curr[1];

            if (dx1 !== dx2 || dy1 !== dy2) {
                simplified.push(curr);
            }
        }
        simplified.push(gridPath[gridPath.length - 1]);

        return simplified.map(([gx, gy]) => this._toPixel(gx, gy));
    }
}
