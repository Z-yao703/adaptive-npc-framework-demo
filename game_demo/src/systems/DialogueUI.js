/**
 * DialogueUI - DOM 对话浮层系统
 * 
 * 功能：
 * - 底部固定的对话框区域
 * - 消息历史滚动显示（玩家右对齐/NPC左对齐）
 * - 文本输入框 + 发送按钮
 * - 多 NPC 独立对话历史管理
 * - 切换 NPC 时对话历史保留
 */
import InteractionManager from './InteractionManager.js';
export default class DialogueUI {
    constructor() {
        this.isOpen = false;
        this.currentNpcId = null;
        this.currentNpcName = 'NPC';

        // 每个 NPC 独立的对话历史 { npcId: [{speaker, message}, ...] }
        this.npcHistories = {};

        // 当前输入回调（由外部设置）
        this.onSendMessage = null;

        // DOM 元素引用
        this.container = null;
        this.messagesArea = null;
        this.input = null;
    }

    /**
     * 设置消息发送回调
     * @param {Function} callback - (npcId, text) => void
     */
    setSendCallback(callback) {
        this.onSendMessage = callback;
    }

    /**
     * 设置 NPC_SAY 动作回调，当收到 AgentBridge 的 NPC_SAY 时调用
     * @param {string} npcId 
     * @param {string} npcName 
     * @param {string} text 
     */
    onNpcSay(npcId, npcName, text) {
        this.addMessage(npcId, npcName || 'NPC', text, 'npc');
    }

    /**
     * 显示系统消息（物品给予/收取/任务等）
     * @param {string} text - 系统消息文本
     */
    onSystemMessage(text) {
        // 获取当前正在对话的 NPC ID
        const npcId = this.currentNpcId;
        if (!npcId) return;

        if (!this.npcHistories[npcId]) {
            this.npcHistories[npcId] = [];
        }

        this.npcHistories[npcId].push({
            speaker: '系统',
            message: text,
            type: 'system',
            timestamp: Date.now()
        });

        // 刷新显示
        this.refreshMessages();
    }

    /**
     * 打开对话面板
     * @param {string} npcId 
     * @param {string} npcName 
     */
    open(npcId, npcName) {
        if (!npcId) return;

        this.currentNpcId = npcId;
        this.currentNpcName = npcName || 'NPC';

        // 初始化该 NPC 的对话历史
        if (!this.npcHistories[npcId]) {
            this.npcHistories[npcId] = [];
        }

        if (this.isOpen) {
            // 如果已打开，刷新显示当前 NPC 的对话历史
            this.refreshMessages();
            return;
        }

        this.isOpen = true;
        this.createChatUI();
    }

    /**
     * 关闭对话面板
     */
    close() {
        this.isOpen = false;
        this.currentNpcId = null;
        this.removeChatUI();
        InteractionManager.unlock('dialogue');
    }

    /**
     * 切换当前对话的 NPC
     * @param {string} npcId 
     * @param {string} npcName 
     */
    switchNpc(npcId, npcName) {
        if (!this.isOpen) return;
        this.currentNpcId = npcId;
        this.currentNpcName = npcName || 'NPC';

        if (!this.npcHistories[npcId]) {
            this.npcHistories[npcId] = [];
        }

        // 更新标题
        const title = this.container?.querySelector('.dialogue-title');
        if (title) title.textContent = npcName || 'NPC';

        this.refreshMessages();
    }

    /**
     * 添加消息到对话历史
     * @param {string} npcId 
     * @param {string} speaker 
     * @param {string} text 
     * @param {string} type - 'player' | 'npc'
     */
    addMessage(npcId, speaker, text, type) {
        if (!npcId || !text) return;

        if (!this.npcHistories[npcId]) {
            this.npcHistories[npcId] = [];
        }

        this.npcHistories[npcId].push({
            speaker: speaker,
            message: text,
            type: type,
            timestamp: Date.now()
        });

        // 限制最多保留 50 条
        if (this.npcHistories[npcId].length > 50) {
            this.npcHistories[npcId] = this.npcHistories[npcId].slice(-50);
        }

        // 如果当前正在查看该 NPC，刷新显示
        if (this.isOpen && this.currentNpcId === npcId) {
            this.appendMessageToDOM({ speaker, message: text, type });
        }
    }

    /**
     * 设置 NPC 的对话历史（用于初始化加载）
     * @param {string} npcId 
     * @param {Array} messages 
     */
    setNpcHistory(npcId, messages) {
        this.npcHistories[npcId] = messages || [];
    }

    // ===== 内部方法 =====

    /**
     * 创建 DOM 聊天 UI
     */
    createChatUI() {
        this.removeChatUI();

        // 集装箱
        const container = document.createElement('div');
        container.id = 'dialogue-container';
        container.className = 'dialogue-container';

        // 标题栏
        const header = document.createElement('div');
        header.className = 'dialogue-header';

        const title = document.createElement('span');
        title.className = 'dialogue-title';
        title.textContent = this.currentNpcName;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'dialogue-close';
        closeBtn.textContent = '✕';
        closeBtn.onclick = () => this.close();

        header.appendChild(title);
        header.appendChild(closeBtn);

        // 消息显示区
        const messages = document.createElement('div');
        messages.id = 'dialogue-messages';
        messages.className = 'dialogue-messages';

        // 输入区
        const inputArea = document.createElement('div');
        inputArea.className = 'dialogue-input-area';

        const input = document.createElement('input');
        input.id = 'dialogue-input';
        input.className = 'dialogue-input';
        input.type = 'text';
        input.placeholder = '输入你想说的话...';
        input.onkeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        };

        const sendBtn = document.createElement('button');
        sendBtn.className = 'dialogue-send-btn';
        sendBtn.textContent = '发送';
        sendBtn.onclick = () => this.handleSend();

        inputArea.appendChild(input);
        inputArea.appendChild(sendBtn);

        container.appendChild(header);
        container.appendChild(messages);
        container.appendChild(inputArea);

        document.body.appendChild(container);

        this.container = container;
        this.messagesArea = messages;
        this.input = input;

        // 渲染当前 NPC 的对话历史
        this.refreshMessages();

        // 聚焦输入框
        setTimeout(() => input.focus(), 100);
    }

    /**
     * 移除聊天 UI
     */
    removeChatUI() {
        const existing = document.getElementById('dialogue-container');
        if (existing) existing.remove();
        this.container = null;
        this.messagesArea = null;
        this.input = null;
    }

    /**
     * 处理发送消息
     */
    handleSend() {
        if (!this.input || !this.currentNpcId) return;
        const text = this.input.value.trim();
        if (!text) return;

        // 添加到当前 NPC 的对话历史（玩家消息）
        this.addMessage(this.currentNpcId, '玩家', text, 'player');

        // 清空输入框
        this.input.value = '';
        this.input.focus();

        // 外部回调：发送到后端
        if (this.onSendMessage) {
            this.onSendMessage(this.currentNpcId, text);
        }
    }

    /**
     * 刷新消息区域（切换 NPC 时完整刷新）
     */
    refreshMessages() {
        if (!this.messagesArea) return;
        this.messagesArea.innerHTML = '';

        const history = this.npcHistories[this.currentNpcId] || [];
        history.forEach(msg => {
            this.appendMessageToDOM(msg);
        });

        this.scrollToBottom();
    }

    /**
     * 增量追加一条消息到 DOM
     */
    appendMessageToDOM(msg) {
        if (!this.messagesArea) return;

        const msgDiv = document.createElement('div');
        const isPlayer = msg.type === 'player' || msg.speaker === '玩家';
        const isSystem = msg.type === 'system' || msg.speaker === '系统';

        if (isSystem) {
            msgDiv.className = 'dialogue-msg dialogue-msg-system';
            msgDiv.innerHTML = `<span class="dialogue-msg-text" style="color:#ffd700;font-weight:bold;text-align:center;display:block;">${msg.message}</span>`;
        } else if (isPlayer) {
            msgDiv.className = 'dialogue-msg dialogue-msg-player';
            msgDiv.innerHTML = `<span class="dialogue-msg-label">你:</span> <span class="dialogue-msg-text">${msg.message}</span>`;
        } else {
            msgDiv.className = 'dialogue-msg dialogue-msg-npc';
            const label = msg.speaker;
            msgDiv.innerHTML = `<span class="dialogue-msg-label">${label}:</span> <span class="dialogue-msg-text">${msg.message}</span>`;
        }

        this.messagesArea.appendChild(msgDiv);
        this.scrollToBottom();
    }

    /**
     * 滚动到底部
     */
    scrollToBottom() {
        if (this.messagesArea) {
            this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
        }
    }
}
