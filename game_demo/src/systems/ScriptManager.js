/**
 * ScriptManager - 剧本与游戏流程管理器
 *
 * 职责：
 * - 创建游戏会话（调用 /api/game/start）
 * - 游戏重启、剧本重玩、剧本删除
 * - 显示开始界面、加载界面、结束界面
 * - 历史剧本列表加载与详情展示
 * - 怀疑度更新
 * - NPC 名称映射
 */
import { NPC_CONFIGS, API_BASE, PLAYER_ID } from '../config/npc-config.js';
import InteractionManager from './InteractionManager.js';

export default class ScriptManager {
    /**
     * @param {Phaser.Scene} scene - 游戏场景引用
     */
    constructor(scene) {
        this.scene = scene;

        // 加载进度相关
        this._loadingProgress = 0;
        this._loadingInterval = null;
    }

    /**
     * 创建游戏会话（调用 /api/game/start）
     */
    async createGameSession() {
        const scene = this.scene;
        console.log('[ScriptManager] 正在启动游戏会话...');

        const agentIds = NPC_CONFIGS.map(c => c.id);

        try {
            const resp = await fetch(`${API_BASE}/api/game/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_ids: agentIds, player_id: PLAYER_ID })
            });

            if (!resp.ok) {
                console.warn('[ScriptManager] 后端未响应，使用离线模式');
                scene.gameSessionId = 'offline-session';
                scene.gameQuestions = [];
                return;
            }

            const data = await resp.json();
            scene.gameSessionId = data.session_id;
            scene.gameQuestions = data.questions || [];

            console.log('[ScriptManager] 新建剧本 - 后端返回完整数据:', JSON.stringify(data, null, 2));
            console.log('[ScriptManager] npc_role_mapping:', data.npc_role_mapping);
            console.log('[ScriptManager] npc_role_mapping keys:', data.npc_role_mapping ? Object.keys(data.npc_role_mapping) : 'null/undefined');

            console.log(`[ScriptManager] 会话已创建: ${scene.gameSessionId}, 标题: ${data.title}, 题目数: ${scene.gameQuestions.length}`);
            console.log('\n' + '='.repeat(60));
            console.log('📖 剧本生成完成');
            console.log('='.repeat(60));
            console.log('会话ID:', data.session_id);
            console.log('剧本标题:', data.title);
            console.log('-'.repeat(60));
            console.log('故事内容:');
            console.log('  ' + (data.story || '无'));
            console.log('-'.repeat(60));

            if (data.npc_role_mapping && Object.keys(data.npc_role_mapping).length > 0) {
                console.log(`角色分配 (${Object.keys(data.npc_role_mapping).length} 个角色):`);
                const alignmentMap = {
                    'villain': '🦹 坏人',
                    'hero': '🦸 好人',
                    'witness': '👁️ 目击者'
                };
                for (const [npcId, roleData] of Object.entries(data.npc_role_mapping)) {
                    const label = alignmentMap[roleData.alignment] || roleData.alignment;
                    const npcName = this.getNpcNameById(npcId);
                    console.log(`  [${label}] ${npcName}`);
                    if (roleData.secret) {
                        console.log(`    秘密: ${roleData.secret}`);
                    }
                }
            } else {
                console.log('⚠️ 角色分配信息为空或不存在！');
                console.log('  npc_role_mapping 值:', data.npc_role_mapping);
            }

            console.log('-'.repeat(60));
            console.log(`题目 (${data.questions.length} 道):`);
            data.questions.forEach(q => {
                console.log(`  Q${q.id}: ${q.question}`);
                if (q.options) {
                    q.options.forEach(opt => {
                        console.log(`    ${opt.label}. ${opt.text}`);
                    });
                }
                if (q.answer) {
                    console.log(`    ✅ 答案: ${q.answer}`);
                }
            });
            console.log('='.repeat(60) + '\n');

            // 更新推论面板标题
            const panelTitle = document.querySelector('#panel-deduction .panel-title');
            if (panelTitle && data.title) {
                panelTitle.textContent = `推论 - ${data.title}`;
            }

            // 初始化答题面板数据
            if (scene.deductionPanel) {
                scene.deductionPanel.init(scene.gameSessionId, scene.gameQuestions, data.title || '', data.gold);
            }

        } catch (err) {
            console.error('[ScriptManager] 游戏会话创建失败:', err);
            scene.gameSessionId = 'offline-session';
            scene.gameQuestions = [];
        }
    }

    /**
     * 重新开始游戏
     */
    async restartGame() {
        const scene = this.scene;
        console.log('[ScriptManager] 重新开始游戏');

        scene.inputLocked = true;
        this.showLoadingOverlay();

        this.updateSuspicion(0);

        if (scene.deductionPanel) scene.deductionPanel.clear();

        // 关闭所有面板
        if (scene.shopSystem) scene.shopSystem.closeAllPanels();
        scene.closeNpcDialogue();

        // 关掉结束面板 overlay
        const overlay = document.querySelector('.end-overlay');
        if (overlay) overlay.remove();

        // 角色回到起始位置
        if (scene.player && scene.playerArea) {
            const markersLayer = scene.map.getObjectLayer('markers');
            if (markersLayer) {
                const playerStart = markersLayer.objects.find(obj => obj.name === 'playerStart');
                if (playerStart) {
                    scene.player.setPosition(playerStart.x, playerStart.y);
                    scene.player.body.setVelocity(0, 0);
                }
            }
        }

        // 断开旧连接、销毁 NPC
        if (scene.npcManager) scene.npcManager.destroy();

        // 清除短期记忆
        for (const cfg of NPC_CONFIGS) {
            try {
                await fetch(`${API_BASE}/api/short_term_memory/${cfg.id}`, { method: 'DELETE' });
            } catch (e) { /* ignore */ }
        }

        // 重新初始化 NPC
        for (const cfg of NPC_CONFIGS) {
            try {
                await fetch(`${API_BASE}/api/agent/${cfg.id}/init`, { method: 'POST' });
            } catch (e) { /* ignore */ }
        }

        // 重新创建 NPC 系统
        scene.createNpcSystem();

        // 重新启动游戏会话
        await this.createGameSession();

        this.hideLoadingOverlay(() => {
            scene.inputLocked = false;
        });
    }

    /**
     * 更新怀疑度进度条
     */
    updateSuspicion(value) {
        const scene = this.scene;
        if (scene.deductionPanel) {
            scene.deductionPanel.updateSuspicion(value);
        }
        const fill = document.getElementById('suspicion-fill');
        if (fill) {
            fill.style.width = value + '%';
        }
    }

    /**
     * 显示胜利/失败画面
     */
    showEndScreen(title, story, suspicion) {
        const scene = this.scene;

        if (scene.shopSystem) scene.shopSystem.closeAllPanels();
        scene.closeNpcDialogue();

        if (title && story) {
            scene.deductionPanel.showVictory(title, story);
        } else if (suspicion !== undefined) {
            scene.deductionPanel.showGameOver(suspicion);
        }
    }

    /**
     * 结束探案，回归日常游戏状态
     * 清除剧本注入、警惕性等剧本带来的配置，不加载新剧本
     */
    async endGameReturnToNormal() {
        const scene = this.scene;
        console.log('[ScriptManager] 结束探案，回归日常状态');

        scene.inputLocked = true;

        this.updateSuspicion(0);

        if (scene.shopSystem) scene.shopSystem.closeAllPanels();
        scene.closeNpcDialogue();

        const endOverlay = document.querySelector('.end-overlay');
        if (endOverlay) endOverlay.remove();

        if (scene.player && scene.playerArea) {
            const markersLayer = scene.map.getObjectLayer('markers');
            if (markersLayer) {
                const playerStart = markersLayer.objects.find(obj => obj.name === 'playerStart');
                if (playerStart) {
                    scene.player.setPosition(playerStart.x, playerStart.y);
                    scene.player.body.setVelocity(0, 0);
                }
            }
        }

        if (scene.npcManager) scene.npcManager.destroy();

        for (const cfg of NPC_CONFIGS) {
            try {
                await fetch(`${API_BASE}/api/short_term_memory/${cfg.id}`, { method: 'DELETE' });
            } catch (e) { /* ignore */ }
        }

        for (const cfg of NPC_CONFIGS) {
            try {
                await fetch(`${API_BASE}/api/agent/${cfg.id}/init`, { method: 'POST' });
            } catch (e) { /* ignore */ }
        }

        scene.createNpcSystem();

        scene.gameSessionId = null;
        scene.gameQuestions = [];

        if (scene.deductionPanel) scene.deductionPanel.clear();

        scene.inputLocked = false;
        console.log('[ScriptManager] 已回归日常游戏状态');
    }

    /**
     * 从日常状态创建新剧本（推论面板"创建新剧本"按钮触发）
     */
    async startNewScript() {
        const scene = this.scene;
        console.log('[ScriptManager] 创建新剧本');

        scene.inputLocked = true;

        if (scene.shopSystem) scene.shopSystem.closeAllPanels();
        scene.closeNpcDialogue();

        this.showLoadingOverlay();
        await this.createGameSession();

        this.hideLoadingOverlay(() => {
            scene.inputLocked = false;
            console.log('[ScriptManager] 新剧本加载完成');
        });
    }

    /**
     * 显示开始界面
     */
    showStartScreen() {
        const scene = this.scene;
        const self = this;

        const overlay = document.createElement('div');
        overlay.className = 'start-overlay';
        overlay.id = 'start-overlay';

        const title = document.createElement('div');
        title.className = 'start-title';
        title.textContent = '混沌旅馆';

        const subtitle = document.createElement('div');
        subtitle.className = 'start-subtitle';
        subtitle.textContent = 'CHAOS INN';

        const btnContainer = document.createElement('div');
        btnContainer.className = 'btn-container';

        const btnNewGame = document.createElement('button');
        btnNewGame.className = 'btn-start';
        btnNewGame.textContent = '新的游戏';
        btnNewGame.onclick = () => self.startGameLoad(overlay);

        const btnEnter = document.createElement('button');
        btnEnter.className = 'btn-enter';
        btnEnter.textContent = '直接进入';
        btnEnter.onclick = async () => {
            overlay.style.opacity = '0';
            await new Promise(r => setTimeout(r, 500));
            overlay.remove();
            scene.inputLocked = false;
            console.log('[ScriptManager] 直接进入游戏，未加载剧本');
        };

        btnContainer.appendChild(btnNewGame);
        btnContainer.appendChild(btnEnter);

        overlay.appendChild(title);
        overlay.appendChild(subtitle);
        overlay.appendChild(btnContainer);
        document.body.appendChild(overlay);

        console.log('[ScriptManager] 开始界面已显示');
    }

    /**
     * 开始加载剧本（点击「开始游戏」后触发）
     */
    async startGameLoad(startOverlay) {
        const scene = this.scene;

        console.log('[ScriptManager] 开始加载剧本');

        startOverlay.style.opacity = '0';
        await new Promise(r => setTimeout(r, 500));
        startOverlay.remove();

        this.showLoadingOverlay();

        await this.createGameSession();

        this.hideLoadingOverlay(() => {
            scene.inputLocked = false;
            console.log('[ScriptManager] 剧本加载完成，游戏正式开始');
        });
    }

    /**
     * 显示加载覆盖层
     */
    showLoadingOverlay() {
        if (document.getElementById('loading-overlay')) return;

        InteractionManager.lock('loading');

        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.id = 'loading-overlay';

        const text = document.createElement('div');
        text.className = 'loading-text pulse';
        text.textContent = '正在加载剧本...';

        const barTrack = document.createElement('div');
        barTrack.className = 'loading-bar-track';

        const barFill = document.createElement('div');
        barFill.className = 'loading-bar-fill';
        barFill.id = 'loading-bar-fill';

        barTrack.appendChild(barFill);
        overlay.appendChild(text);
        overlay.appendChild(barTrack);
        document.body.appendChild(overlay);

        this._loadingProgress = 0;
        this._loadingInterval = setInterval(() => {
            if (this._loadingProgress < 90) {
                this._loadingProgress += Math.random() * 15;
                if (this._loadingProgress > 90) this._loadingProgress = 90;
                barFill.style.width = this._loadingProgress + '%';
            }
        }, 300);
    }

    /**
     * 隐藏加载覆盖层（渐隐 + 移除）
     * @param {Function} [onDone] - 渐隐完成后的回调
     */
    hideLoadingOverlay(onDone) {
        const scene = this.scene;

        InteractionManager.unlock('loading');

        const barFill = document.getElementById('loading-bar-fill');
        if (barFill) barFill.style.width = '100%';

        if (this._loadingInterval) {
            clearInterval(this._loadingInterval);
            this._loadingInterval = null;
        }

        const overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            if (onDone) onDone();
            return;
        }

        setTimeout(() => {
            overlay.style.opacity = '0';
            setTimeout(() => {
                if (overlay.parentNode) overlay.remove();
                if (onDone) onDone();
            }, 400);
        }, 300);
    }

    // ===== 剧本历史面板 =====

    /**
     * 加载历史剧本列表
     */
    async loadScriptsHistory() {
        try {
            const resp = await fetch(`${API_BASE}/api/game/history`);
            const histories = await resp.json();

            const content = document.querySelector('#panel-scripts .panel-content');
            content.innerHTML = '';

            if (!histories || histories.length === 0) {
                content.innerHTML = '<p>暂无历史剧本</p>';
                return;
            }

            histories.forEach(h => {
                const item = document.createElement('div');
                item.className = 'script-item';
                item.innerHTML = `
                    <div class="script-info">
                        <div class="script-title">${this._escapeHtml(h.title)}</div>
                        <div class="script-date">${new Date(h.created_at).toLocaleString('zh-CN')}</div>
                    </div>
                    <div class="script-actions">
                        <button class="script-btn" title="查看详情" data-action="view" data-id="${h.session_id}">👁</button>
                        <button class="script-btn" title="重玩剧本" data-action="replay" data-id="${h.session_id}">🔄</button>
                        <button class="script-btn" title="删除剧本" data-action="delete" data-id="${h.session_id}">🗑</button>
                    </div>
                `;
                content.appendChild(item);
            });

            content.querySelectorAll('.script-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const action = e.target.dataset.action;
                    const sessionId = e.target.dataset.id;
                    this.handleScriptAction(action, sessionId);
                });
            });

        } catch (err) {
            console.error('[ScriptManager] 加载历史剧本失败:', err);
        }
    }

    /**
     * 处理剧本操作
     */
    async handleScriptAction(action, sessionId) {
        if (action === 'view') {
            await this.showScriptDetail(sessionId);
        } else if (action === 'replay') {
            await this.replayScript(sessionId);
        } else if (action === 'delete') {
            await this.deleteScript(sessionId);
        }
    }

    /**
     * 显示剧本详情面板
     */
    async showScriptDetail(sessionId) {
        try {
            const resp = await fetch(`${API_BASE}/api/game/summary?session_id=${sessionId}`);
            const data = await resp.json();

            const oldPanel = document.getElementById('panel-script-detail');
            if (oldPanel && oldPanel.parentNode) {
                oldPanel.remove();
            }

            const panel = document.createElement('div');
            panel.className = 'panel';
            panel.id = 'panel-script-detail';
            panel.innerHTML = `
                <div class="panel-header">
                    <span class="panel-title">剧本详情</span>
                    <button class="panel-close" data-panel="script-detail">✕</button>
                </div>
                <div class="panel-content">
                    <div class="script-detail-section">
                        <h4>标题</h4>
                        <p>${this._escapeHtml(data.title)}</p>
                    </div>
                    <div class="script-detail-section">
                        <h4>故事</h4>
                        <p>${this._escapeHtml(data.story)}</p>
                    </div>
                    ${this.renderRolesDetail(data.roles)}
                </div>
            `;
            document.body.appendChild(panel);

            panel.querySelector('.panel-close').addEventListener('click', () => {
                panel.remove();
            });

        } catch (err) {
            console.error('[ScriptManager] 加载剧本详情失败:', err);
        }
    }

    /**
     * 渲染角色详情 HTML
     */
    renderRolesDetail(roles) {
        if (!roles || Object.keys(roles).length === 0) {
            return '<div class="script-detail-section"><h4>人物</h4><p>无角色信息</p></div>';
        }

        const alignmentMap = {
            'villain': '🦹 坏人',
            'hero': '🦸 好人',
            'witness': '👁️ 目击者'
        };

        let html = '<div class="script-detail-section"><h4>人物</h4>';
        for (const [key, role] of Object.entries(roles)) {
            const label = alignmentMap[role.alignment] || role.alignment;
            html += `
                <div class="role-card">
                    <div class="role-name">${key}: ${label}</div>
                    <p>秘密：${this._escapeHtml(role.secret || '无')}</p>
                </div>
            `;
        }
        html += '</div>';
        return html;
    }

    /**
     * 重玩剧本
     */
    async replayScript(sessionId) {
        const scene = this.scene;

        console.log('[ScriptManager] 重玩剧本:', sessionId);

        scene.inputLocked = true;

        document.getElementById('panel-scripts').classList.add('hidden');

        if (scene.shopSystem) scene.shopSystem.closeAllPanels();
        scene.closeNpcDialogue();

        this.showLoadingOverlay();

        try {
            for (const cfg of NPC_CONFIGS) {
                try {
                    await fetch(`${API_BASE}/api/short_term_memory/${cfg.id}`, { method: 'DELETE' });
                } catch (e) { /* ignore */ }
            }

            for (const cfg of NPC_CONFIGS) {
                try {
                    await fetch(`${API_BASE}/api/agent/${cfg.id}/init`, { method: 'POST' });
                } catch (e) { /* ignore */ }
            }

            if (scene.npcManager) scene.npcManager.destroy();
            scene.createNpcSystem();

            const agentIds = NPC_CONFIGS.map(c => c.id);
            const resp = await fetch(`${API_BASE}/api/game/replay`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    agent_ids: agentIds,
                    player_id: PLAYER_ID
                })
            });

            if (!resp.ok) {
                throw new Error('重玩剧本失败');
            }

            const data = await resp.json();

            scene.gameSessionId = data.session_id;
            scene.gameQuestions = data.questions || [];

            console.log('[ScriptManager] 重玩剧本 - 后端返回完整数据:', JSON.stringify(data, null, 2));
            console.log('[ScriptManager] npc_role_mapping:', data.npc_role_mapping);
            console.log('[ScriptManager] npc_role_mapping keys:', data.npc_role_mapping ? Object.keys(data.npc_role_mapping) : 'null/undefined');

            console.log(`[ScriptManager] 重玩会话: ${scene.gameSessionId}, 标题: ${data.title}, 题目数: ${scene.gameQuestions.length}`);
            console.log('\n' + '='.repeat(60));
            console.log('📖 剧本重玩完成');
            console.log('='.repeat(60));
            console.log('会话ID:', data.session_id);
            console.log('剧本标题:', data.title);
            console.log('-'.repeat(60));
            console.log('故事内容:');
            console.log('  ' + (data.story || '无'));
            console.log('-'.repeat(60));

            if (data.npc_role_mapping && Object.keys(data.npc_role_mapping).length > 0) {
                const alignmentMap = {
                    'villain': '🦹 坏人',
                    'hero': '🦸 好人',
                    'witness': '👁️ 目击者'
                };
                console.log(`角色分配 (${Object.keys(data.npc_role_mapping).length} 个角色):`);
                for (const [npcId, roleData] of Object.entries(data.npc_role_mapping)) {
                    const label = alignmentMap[roleData.alignment] || roleData.alignment;
                    const npcName = this.getNpcNameById(npcId);
                    console.log(`  [${label}] ${npcName}`);
                    if (roleData.secret) {
                        console.log(`    秘密: ${roleData.secret}`);
                    }
                }
            } else {
                console.log('⚠️ 角色分配信息为空或不存在！');
                console.log('  npc_role_mapping 值:', data.npc_role_mapping);
            }

            console.log('-'.repeat(60));
            console.log(`题目 (${data.questions.length} 道):`);
            data.questions.forEach(q => {
                console.log(`  Q${q.id}: ${q.question}`);
                if (q.options) {
                    q.options.forEach(opt => {
                        console.log(`    ${opt.label}. ${opt.text}`);
                    });
                }
                if (q.answer) {
                    console.log(`    ✅ 答案: ${q.answer}`);
                }
            });
            console.log('='.repeat(60) + '\n');

            const panelTitle = document.querySelector('#panel-deduction .panel-title');
            if (panelTitle && data.title) {
                panelTitle.textContent = `推论 - ${data.title}`;
            }

            // 重玩时先完全重置侦察面板状态（清除变量、UI、LocalStorage）
            if (scene.deductionPanel) {
                scene.deductionPanel.clear(scene.gameSessionId);
                scene.deductionPanel.init(scene.gameSessionId, scene.gameQuestions, data.title || '', data.gold);
            }

            this.hideLoadingOverlay(() => {
                scene.inputLocked = false;
                console.log('[ScriptManager] 剧本重玩完成');
            });

        } catch (err) {
            console.error('[ScriptManager] 重玩剧本失败:', err);
            this.hideLoadingOverlay();
            scene.inputLocked = false;
        }
    }

    /**
     * 删除剧本
     */
    async deleteScript(sessionId) {
        if (!confirm('确定要删除这个剧本吗？')) return;

        try {
            const resp = await fetch(`${API_BASE}/api/game/${sessionId}`, {
                method: 'DELETE'
            });

            if (resp.ok) {
                this.loadScriptsHistory();
            }
        } catch (err) {
            console.error('[ScriptManager] 删除剧本失败:', err);
        }
    }

    /**
     * 根据 NPC ID 获取 NPC 名字
     */
    getNpcNameById(npcId) {
        const config = NPC_CONFIGS.find(c => c.id === npcId);
        return config ? config.name : npcId;
    }

    /**
     * 将 role_0/role_1/role_2 映射为真实的 NPC 名字
     */
    getNpcNameByRoleKey(roleKey) {
        const match = roleKey.match(/role_(\d+)/);
        if (match) {
            const index = parseInt(match[1], 10);
            if (NPC_CONFIGS[index]) {
                return NPC_CONFIGS[index].name;
            }
        }
        return roleKey;
    }

    /**
     * 转义 HTML 特殊字符
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
