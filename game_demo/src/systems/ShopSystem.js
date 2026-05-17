/**
 * ShopSystem - 商店/背包/金币管理系统
 *
 * 职责：
 * - 打开/关闭购买面板（料理 & 杂物）
 * - 渲染购买物品列表 & 处理购买逻辑
 * - 金币显示与管理（扣除/刷新）
 * - 背包内容渲染与刷新
 * - 关闭所有面板的统一入口
 */
import InteractionManager from './InteractionManager.js';
import { API_BASE, PLAYER_ID } from '../config/npc-config.js';

export default class ShopSystem {
    /**
     * @param {Phaser.Scene} scene - 游戏场景引用
     */
    constructor(scene) {
        this.scene = scene;
        this.purchasePanel = null;
        this.playerId = PLAYER_ID;
    }

    /**
     * 打开购买面板
     * @param {string} type - 'food' 或 'supply'
     * @param {string} title - 面板标题
     */
    openPurchasePanel(type, title) {
        // 先移除已有面板
        if (this.purchasePanel && this.purchasePanel.parentNode) {
            this.purchasePanel.parentNode.removeChild(this.purchasePanel);
            this.purchasePanel = null;
        }

        const items = type === 'food' ? window.gameState.foods : window.gameState.supplies;

        const panel = document.createElement('div');
        panel.className = 'panel';
        panel.id = 'panel-purchase';

        const header = document.createElement('div');
        header.className = 'panel-header';

        const titleSpan = document.createElement('span');
        titleSpan.className = 'panel-title';
        titleSpan.textContent = title;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'panel-close';
        closeBtn.textContent = '✕';
        closeBtn.onclick = () => this.closePurchasePanel();

        header.appendChild(titleSpan);
        header.appendChild(closeBtn);

        const content = document.createElement('div');
        content.className = 'panel-content';
        content.style.cssText = `
            padding: 15px 20px;
            justify-content: flex-start;
            align-items: stretch;
            flex-direction: column;
            min-height: 200px;
            overflow-y: auto;
        `;

        this.renderPurchaseItems(content, items, type);

        panel.appendChild(header);
        panel.appendChild(content);

        document.getElementById('game-container').appendChild(panel);
        this.purchasePanel = panel;

        console.log(`购买面板已打开: ${title}`);
    }

    /**
     * 关闭购买面板
     */
    closePurchasePanel() {
        if (this.purchasePanel && this.purchasePanel.parentNode) {
            this.purchasePanel.parentNode.removeChild(this.purchasePanel);
            this.purchasePanel = null;
        }
    }

    /**
     * 渲染购买面板中的物品列表
     */
    renderPurchaseItems(container, items, type) {
        container.innerHTML = '';

        Object.entries(items).forEach(([name, data]) => {
            const itemRow = document.createElement('div');
            itemRow.className = 'purchase-item';
            itemRow.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 15px;
                margin: 5px 0;
                background: rgba(93, 64, 55, 0.3);
                border-radius: 6px;
                border: 1px solid var(--primary-color-1);
            `;

            const itemInfo = document.createElement('div');
            itemInfo.style.cssText = `
                display: flex;
                flex-direction: column;
                align-items: flex-start;
                gap: 2px;
            `;

            const itemName = document.createElement('span');
            itemName.textContent = name;
            itemName.style.cssText = `
                color: var(--text-color-1);
                font-size: 14px;
                font-weight: bold;
            `;

            const itemPrice = document.createElement('span');
            itemPrice.textContent = `购入价: ${data.buyPrice} 金币`;
            itemPrice.style.cssText = `
                color: #FFD700;
                font-size: 12px;
            `;

            itemInfo.appendChild(itemName);
            itemInfo.appendChild(itemPrice);

            const buyBtn = document.createElement('button');
            buyBtn.textContent = '购买';
            buyBtn.style.cssText = `
                padding: 6px 16px;
                background-color: var(--primary-color-2);
                border: 2px solid var(--primary-color-1);
                border-radius: 6px;
                color: var(--text-color-1);
                font-size: 12px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.2s ease;
            `;

            buyBtn.onmouseover = () => {
                buyBtn.style.backgroundColor = 'var(--primary-color-2-hover)';
                buyBtn.style.transform = 'scale(1.05)';
            };

            buyBtn.onmouseout = () => {
                buyBtn.style.backgroundColor = 'var(--primary-color-2)';
                buyBtn.style.transform = 'scale(1)';
            };

            buyBtn.onclick = () => this.handlePurchase(name, data.buyPrice, type);

            itemRow.appendChild(itemInfo);
            itemRow.appendChild(buyBtn);
            container.appendChild(itemRow);
        });
    }

    /**
     * 处理购买逻辑（调用后端 API 真实扣金币 + 持久化背包）
     */
    async handlePurchase(itemName, price, type) {
        if (window.gameState.gold < price) {
            this.showPurchaseMessage('金币不足！');
            return;
        }

        try {
            const resp = await fetch(`${API_BASE}/api/player/${this.playerId}/buy`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_name: itemName,
                    item_type: type,
                    price: price
                })
            });

            const data = await resp.json();

            if (data.success) {
                window.gameState.gold = data.gold;

                if (type === 'food') {
                    window.gameState.foods[itemName].count++;
                } else {
                    window.gameState.supplies[itemName].count++;
                }

                this.updateGoldDisplay();
                this.refreshBackpackPanel();

                console.log(`购买成功: ${itemName}, 剩余金币: ${window.gameState.gold}`);
            } else {
                this.showPurchaseMessage(data.message || '购买失败');
            }
        } catch (err) {
            console.error('[ShopSystem] 购买请求失败:', err);
            this.showPurchaseMessage('网络错误，购买失败');
        }
    }

    /**
     * 显示购买提示信息
     */
    showPurchaseMessage(message) {
        let toast = document.getElementById('purchase-toast');
        if (toast) {
            toast.textContent = message;
        } else {
            toast = document.createElement('div');
            toast.id = 'purchase-toast';
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(200, 50, 50, 0.95);
                color: white;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                z-index: 500;
                border: 2px solid #8B0000;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
            `;
            document.body.appendChild(toast);
        }

        setTimeout(() => {
            if (toast && toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 1500);
    }

    /**
     * 更新金币显示
     */
    updateGoldDisplay() {
        const goldElement = document.getElementById('money-amount');
        if (goldElement) {
            goldElement.textContent = window.gameState.gold;
        }
    }

    /**
     * 刷新背包面板显示
     */
    refreshBackpackPanel() {
        const panelBackpack = document.getElementById('panel-backpack');
        if (!panelBackpack) return;

        if (panelBackpack.classList.contains('hidden')) return;

        const content = panelBackpack.querySelector('.panel-content');
        if (!content) return;

        this.renderBackpackContent(content);
    }

    /**
     * 渲染背包内容
     */
    renderBackpackContent(container) {
        container.innerHTML = '';

        const allItems = [];

        Object.entries(window.gameState.foods).forEach(([name, data]) => {
            if (data.count > 0) {
                allItems.push({
                    name,
                    count: data.count,
                    buyPrice: data.buyPrice,
                    sellPrice: data.sellPrice,
                    category: '料理'
                });
            }
        });

        Object.entries(window.gameState.supplies).forEach(([name, data]) => {
            if (data.count > 0) {
                allItems.push({
                    name,
                    count: data.count,
                    buyPrice: data.buyPrice,
                    sellPrice: data.sellPrice,
                    category: '杂物'
                });
            }
        });

        Object.entries(window.gameState.questItems).forEach(([name, data]) => {
            if (data.count > 0) {
                allItems.push({
                    name,
                    count: data.count,
                    buyPrice: data.buyPrice || '-',
                    sellPrice: data.sellPrice || '-',
                    category: '任务'
                });
            }
        });

        if (allItems.length === 0) {
            const emptyMsg = document.createElement('p');
            emptyMsg.textContent = '背包为空';
            emptyMsg.style.cssText = `
                color: var(--text-color-1);
                font-size: 16px;
                opacity: 0.7;
            `;
            container.appendChild(emptyMsg);
            return;
        }

        const list = document.createElement('div');
        list.style.cssText = `
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 8px;
            align-items: center;
        `;

        allItems.forEach(item => {
            const itemRow = document.createElement('div');
            itemRow.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 15px;
                background: rgba(93, 64, 55, 0.3);
                border-radius: 6px;
                border: 1px solid var(--primary-color-1);
                width: 90%;
            `;

            const nameEl = document.createElement('span');
            nameEl.textContent = item.name;
            nameEl.style.cssText = `
                color: var(--text-color-1);
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            `;

            const countEl = document.createElement('span');
            countEl.textContent = `x${item.count}`;
            countEl.style.cssText = `
                color: #FFD700;
                font-size: 13px;
                min-width: 30px;
                text-align: center;
            `;

            const buyEl = document.createElement('span');
            buyEl.textContent = `购入: ${item.buyPrice}`;
            buyEl.style.cssText = `
                color: #81C784;
                font-size: 11px;
                min-width: 55px;
                text-align: center;
            `;

            const sellEl = document.createElement('span');
            sellEl.textContent = `售出: ${item.sellPrice}`;
            sellEl.style.cssText = `
                color: #EF9A9A;
                font-size: 11px;
                min-width: 55px;
                text-align: center;
            `;

            const catEl = document.createElement('span');
            catEl.textContent = item.category;
            catEl.style.cssText = `
                color: #B0BEC5;
                font-size: 10px;
                min-width: 30px;
                text-align: center;
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                padding: 2px 6px;
            `;

            itemRow.appendChild(nameEl);
            itemRow.appendChild(countEl);
            itemRow.appendChild(buyEl);
            itemRow.appendChild(sellEl);
            itemRow.appendChild(catEl);
            list.appendChild(itemRow);
        });

        container.appendChild(list);
    }

    /**
     * 关闭所有面板（背包、推论、剧本、购买、详情）
     */
    closeAllPanels() {
        const panelBackpack = document.getElementById('panel-backpack');
        const panelDeduction = document.getElementById('panel-deduction');
        const panelScripts = document.getElementById('panel-scripts');

        if (panelBackpack) panelBackpack.classList.add('hidden');
        if (panelDeduction) {
            panelDeduction.classList.add('hidden');
            InteractionManager.unlock('deduction_panel');
        }
        if (panelScripts) panelScripts.classList.add('hidden');

        // 关闭剧本详情面板
        const detailPanel = document.getElementById('panel-script-detail');
        if (detailPanel && detailPanel.parentNode) {
            detailPanel.remove();
        }

        // 关闭购买面板
        this.closePurchasePanel();
    }
}
