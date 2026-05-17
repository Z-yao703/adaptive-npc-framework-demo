/**
 * TradePanel - NPC 交易面板（玩家售卖物资给 NPC）
 *
 * 职责：
 * - 动态渲染 NPC 同意交易的物资列表（名称 + 售价 + 附加费提示）
 * - 提供"售出"/"取消"按钮
 * - 售出时调用后端 API 扣减背包 + 增加金币
 * - 关闭面板时解锁交互
 */
import InteractionManager from './InteractionManager.js';
import { API_BASE, PLAYER_ID } from '../config/npc-config.js';

export default class TradePanel {
    constructor(scene) {
        this.scene = scene;
        this.panel = null;
        this.currentTradeData = null;  // { npcId, npcName, items, tip, message }
    }

    /**
     * 打开交易面板
     * @param {string} npcId - NPC ID
     * @param {string} npcName - NPC 名称
     * @param {Array} items - 物品列表 [{name, sellPrice, type}, ...]
     * @param {number} tip - NPC 附加费（0 或 5）
     * @param {string} message - NPC 接受交易说的话
     */
    open(npcId, npcName, items, tip, message) {
        this.close();
        InteractionManager.lock('trade_panel');

        this.currentTradeData = { npcId, npcName, items, tip, message };

        const panel = document.createElement('div');
        panel.className = 'panel';
        panel.id = 'panel-trade';

        // 标题栏
        const header = document.createElement('div');
        header.className = 'panel-header';
        const titleSpan = document.createElement('span');
        titleSpan.className = 'panel-title';
        titleSpan.textContent = `${npcName} 的交易`;
        const closeBtn = document.createElement('button');
        closeBtn.className = 'panel-close';
        closeBtn.textContent = '✕';
        closeBtn.onclick = () => this.close();
        header.appendChild(titleSpan);
        header.appendChild(closeBtn);

        // NPC 消息
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = `
            padding: 10px 20px; color: #FFD700; font-size: 14px;
            font-style: italic; text-align: center;
            background: rgba(93, 64, 55, 0.4);
            border-bottom: 1px solid var(--primary-color-1);
        `;
        msgDiv.textContent = message || '我愿意买下这些~';

        // 内容区
        const content = document.createElement('div');
        content.className = 'panel-content';
        content.style.cssText = `
            padding: 15px 20px; justify-content: flex-start;
            align-items: stretch; flex-direction: column;
            min-height: 150px; overflow-y: auto;
        `;

        this.renderTradeItems(content, items, tip);

        panel.appendChild(header);
        panel.appendChild(msgDiv);
        panel.appendChild(content);
        document.getElementById('game-container').appendChild(panel);
        this.panel = panel;

        console.log(`[TradePanel] 打开: ${npcName}, items=${items.length}, tip=${tip}`);
    }

    /**
     * 渲染交易物品列表
     */
    renderTradeItems(container, items, tip) {
        container.innerHTML = '';

        if (!items || items.length === 0) {
            const empty = document.createElement('p');
            empty.textContent = '没有可交易的物品';
            empty.style.cssText = 'color: var(--text-color-1); font-size: 14px; opacity: 0.7;';
            container.appendChild(empty);
            return;
        }

        // 规范化 tip 为数字
        const normalizedTip = Number(tip) || 0;

        items.forEach((rawItem, idx) => {
            // 防御性规范化物品字段（应对后端可能遗漏字段的情况）
            const item = {
                name: rawItem.name || rawItem.item_name || rawItem.item || `物品#${idx}`,
                sellPrice: Number(rawItem.sellPrice || rawItem.sell_price || rawItem.price || 0),
                type: rawItem.type || rawItem.item_type || 'food'
            };
            console.log(`[TradePanel] 渲染物品: name=${item.name}, sellPrice=${item.sellPrice}, type=${item.type}, raw=${JSON.stringify(rawItem)}`);

            const totalPrice = item.sellPrice + normalizedTip;
            const tipText = normalizedTip > 0 ? ` (含附加费+${normalizedTip})` : '';

            const row = document.createElement('div');
            row.style.cssText = `
                display: flex; justify-content: space-between; align-items: center;
                padding: 10px 15px; margin: 5px 0;
                background: rgba(93, 64, 55, 0.3); border-radius: 6px;
                border: 1px solid var(--primary-color-1);
            `;

            const info = document.createElement('div');
            info.style.cssText = 'display: flex; flex-direction: column; align-items: flex-start; gap: 2px;';

            const nameEl = document.createElement('span');
            nameEl.textContent = item.name;
            nameEl.style.cssText = 'color: var(--text-color-1); font-size: 14px; font-weight: bold;';

            const priceEl = document.createElement('span');
            priceEl.textContent = `售价: ${totalPrice} 金币${tipText}`;
            priceEl.style.cssText = 'color: #FFD700; font-size: 12px;';

            info.appendChild(nameEl);
            info.appendChild(priceEl);

            const btnGroup = document.createElement('div');
            btnGroup.style.cssText = 'display: flex; gap: 8px;';

            const sellBtn = this.createBtn('售出', '#4CAF50', () => this.handleSell(item, normalizedTip));
            const cancelBtn = this.createBtn('取消', '#f44336', () => this.close());

            btnGroup.appendChild(sellBtn);
            btnGroup.appendChild(cancelBtn);
            row.appendChild(info);
            row.appendChild(btnGroup);
            container.appendChild(row);
        });
    }

    createBtn(text, color, onClick) {
        const btn = document.createElement('button');
        btn.textContent = text;
        btn.style.cssText = `
            padding: 6px 16px; background-color: ${color};
            border: 2px solid var(--primary-color-1); border-radius: 6px;
            color: white; font-size: 12px; font-weight: bold;
            cursor: pointer; transition: all 0.2s ease;
        `;
        btn.onmouseover = () => { btn.style.transform = 'scale(1.05)'; };
        btn.onmouseout = () => { btn.style.transform = 'scale(1)'; };
        btn.onclick = onClick;
        return btn;
    }

    /**
     * 处理售出：调用后端 API
     */
    async handleSell(item, tip) {
        // 防御性规范化
        const itemName = item.name || '';
        const itemType = item.type || 'food';
        const itemPrice = Number(item.sellPrice) || 0;
        const normalizedTip = Number(tip) || 0;

        console.log(`[TradePanel] 执行售出: name=${itemName}, type=${itemType}, price=${itemPrice}, tip=${normalizedTip}`);

        if (!itemName || itemPrice <= 0) {
            this.showToast('物品信息无效，无法售出', '#f44336');
            return;
        }

        try {
            const resp = await fetch(`${API_BASE}/api/player/${PLAYER_ID}/sell`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_name: itemName,
                    item_type: itemType,
                    price: itemPrice,
                    tip: normalizedTip
                })
            });
            const data = await resp.json();

            if (data.success) {
                window.gameState.gold = data.gold;
                // 更新前端背包数量
                if (itemType === 'food' && window.gameState.foods[itemName]) {
                    window.gameState.foods[itemName].count = Math.max(0, (window.gameState.foods[itemName].count || 0) - 1);
                } else if (itemType === 'supply' && window.gameState.supplies[itemName]) {
                    window.gameState.supplies[itemName].count = Math.max(0, (window.gameState.supplies[itemName].count || 0) - 1);
                }
                // 刷新金币显示
                if (this.scene.shopSystem) {
                    this.scene.shopSystem.updateGoldDisplay();
                }
                this.showToast(`售出成功！获得 ${data.total} 金币`, '#4CAF50');
                this.close();
            } else {
                this.showToast(data.message || data.error || '售出失败', '#f44336');
            }
        } catch (err) {
            console.error('[TradePanel] 售出请求失败:', err);
            this.showToast('网络错误，售出失败', '#f44336');
        }
    }

    showToast(message, color) {
        let toast = document.getElementById('trade-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'trade-toast';
            toast.style.cssText = `
                position: fixed; top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                color: white; padding: 15px 30px; border-radius: 8px;
                font-size: 16px; font-weight: bold; z-index: 500;
                border: 2px solid rgba(255,255,255,0.3);
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            `;
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.backgroundColor = color;
        setTimeout(() => {
            if (toast && toast.parentNode) toast.parentNode.removeChild(toast);
        }, 2000);
    }

    close() {
        if (this.panel && this.panel.parentNode) {
            this.panel.parentNode.removeChild(this.panel);
            this.panel = null;
        }
        this.currentTradeData = null;
        InteractionManager.unlock('trade_panel');
    }
}
