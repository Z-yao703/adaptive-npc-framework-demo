/**
 * DeductionPanel - 答题面板 UI 系统
 * 
 * 功能：
 * - 从 /api/game/start 获取的 questions 动态渲染 5 题 × 4 选项按钮
 * - 点击选项提交到 /api/game/answer
 * - 正确显示绿色，错误显示红色
 * - 错误题目支持"重新回答"（扣除20金币）
 * - 题目状态通过 LocalStorage 持久化，面板开合间保持
 * - 更新怀疑度进度条
 * - 胜利/失败结局面板
 */
import { API_BASE } from '../config/npc-config.js';
import { PLAYER_ID } from '../config/npc-config.js';

const STORAGE_PREFIX = 'game_session_';

export default class DeductionPanel {
    constructor() {
        this.sessionId = null;
        this.questions = [];
        this.answeredQuestions = {};  // { qId: { selected: 'A', correct: true/false } }
        this.allAnswered = false;
        this.currentGold = (window.gameState && window.gameState.gold) ? window.gameState.gold : 100;

        // DOM 绑定
        this.panelDeduction = document.getElementById('panel-deduction');
        this.contentArea = null;
        this.suspicionFill = document.getElementById('suspicion-fill');

        // 回调
        this.onGameOver = null;
        this.onVictory = null;
        this.onEnd = null;
        this.onCreateScript = null;

        this.render();
    }

    /**
     * 设置游戏会话和题目
     * @param {string} sessionId 
     * @param {Array} questions - [{id, question, options: [{label, text}]}]
     * @param {string} title - 剧本标题
     * @param {number} gold - 当前金币
     */
    init(sessionId, questions, title, gold) {
        this.sessionId = sessionId;
        this.questions = questions;
        if (gold !== undefined) {
            this.currentGold = gold;
        }

        this.loadQuestionStates();

        const panelTitle = this.panelDeduction?.querySelector('.panel-title');
        if (panelTitle && title) {
            panelTitle.textContent = `推论 - ${title}`;
        }

        this.render();
    }

    /**
     * 从 LocalStorage 加载题目状态
     */
    loadQuestionStates() {
        if (!this.sessionId) {
            this.answeredQuestions = {};
            return;
        }

        try {
            const key = STORAGE_PREFIX + this.sessionId;
            const stored = localStorage.getItem(key);
            if (stored) {
                this.answeredQuestions = JSON.parse(stored);
            } else {
                this.answeredQuestions = {};
            }
        } catch (e) {
            console.warn('[DeductionPanel] 加载题目状态失败:', e);
            this.answeredQuestions = {};
        }
    }

    /**
     * 保存题目状态到 LocalStorage
     */
    saveQuestionStates() {
        if (!this.sessionId) return;

        try {
            const key = STORAGE_PREFIX + this.sessionId;
            localStorage.setItem(key, JSON.stringify(this.answeredQuestions));
        } catch (e) {
            console.warn('[DeductionPanel] 保存题目状态失败:', e);
        }
    }

    /**
     * 清除会话题目状态
     * @param {string} [sessionId] - 可选，指定要清除的会话ID；不传则使用 this.sessionId
     */
    clearQuestionStates(sessionId = null) {
        const targetSessionId = sessionId || this.sessionId;
        if (!targetSessionId) return;

        try {
            const key = STORAGE_PREFIX + targetSessionId;
            localStorage.removeItem(key);
            console.log('[DeductionPanel] 已清除题目状态, sessionId:', targetSessionId);
        } catch (e) {
            console.warn('[DeductionPanel] 清除题目状态失败:', e);
        }
    }

    /**
     * 渲染题目列表
     */
    render() {
        let content = this.panelDeduction?.querySelector('.panel-content');
        if (!content) return;

        this.contentArea = content.querySelector('#quiz-content');
        if (!this.contentArea) {
            this.contentArea = document.createElement('div');
            this.contentArea.id = 'quiz-content';
            this.contentArea.style.cssText = 'width: 100%; display: flex; flex-direction: column; gap: 15px;';
            content.innerHTML = '';
            content.appendChild(this.contentArea);
        }

        this.contentArea.innerHTML = '';

        if (!this.questions || this.questions.length === 0) {
            this.renderIdleState();
            return;
        }

        this.questions.forEach(q => {
            const questionBlock = this.createQuestionBlock(q);
            this.contentArea.appendChild(questionBlock);
        });
    }

    /**
     * 渲染日常状态（无剧本时）
     */
    renderIdleState() {
        this.contentArea.innerHTML = '';

        const wrapper = document.createElement('div');
        wrapper.style.cssText = `
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; padding: 30px 20px; gap: 20px;
        `;

        const icon = document.createElement('div');
        icon.textContent = '🔍';
        icon.style.cssText = 'font-size: 40px; opacity: 0.6;';

        const hint = document.createElement('p');
        hint.textContent = '暂无进行中的案件';
        hint.style.cssText = `
            color: #9E9E9E; text-align: center; font-size: 14px;
            margin: 0; font-family: 'Courier New', monospace;
        `;

        const btnCreate = document.createElement('button');
        btnCreate.textContent = '创建新剧本';
        btnCreate.style.cssText = `
            padding: 10px 30px; font-size: 14px;
            background: #8D6E63; border: 2px solid #5D4037;
            border-radius: 8px; color: #FFFFFF; cursor: pointer;
            font-family: 'Courier New', monospace; font-weight: bold;
            letter-spacing: 3px; transition: all 0.2s ease;
        `;
        btnCreate.onmouseover = () => {
            btnCreate.style.background = '#A1887F';
            btnCreate.style.transform = 'scale(1.05)';
            btnCreate.style.boxShadow = '0 0 12px rgba(141, 110, 99, 0.4)';
        };
        btnCreate.onmouseout = () => {
            btnCreate.style.background = '#8D6E63';
            btnCreate.style.transform = 'scale(1)';
            btnCreate.style.boxShadow = 'none';
        };
        btnCreate.onclick = () => {
            if (this.onCreateScript) this.onCreateScript();
        };

        wrapper.appendChild(icon);
        wrapper.appendChild(hint);
        wrapper.appendChild(btnCreate);
        this.contentArea.appendChild(wrapper);
    }

    /**
     * 创建单道题的 DOM 块
     */
    createQuestionBlock(q) {
        const block = document.createElement('div');
        block.className = 'quiz-block';
        block.dataset.questionId = q.id;

        const qText = document.createElement('div');
        qText.className = 'quiz-question';
        qText.textContent = `${q.id}. ${q.question}`;
        block.appendChild(qText);

        const optionsGrid = document.createElement('div');
        optionsGrid.className = 'quiz-options-grid';

        const state = this.answeredQuestions[q.id];
        const isAnswered = !!state;
        const isCorrect = state && state.correct;
        const isWrong = state && !state.correct;

        q.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'quiz-option';
            btn.textContent = `${opt.label}. ${opt.text}`;
            btn.onclick = () => this.handleAnswer(q.id, opt.label, btn);

            if (isAnswered) {
                btn.classList.add('quiz-option-disabled');
                if (state.selected === opt.label) {
                    if (isCorrect) {
                        btn.classList.add('quiz-option-correct');
                    } else {
                        btn.classList.add('quiz-option-wrong');
                    }
                }
            }

            optionsGrid.appendChild(btn);
        });

        block.appendChild(optionsGrid);

        if (isWrong) {
            const retryBtn = this.createRetryButton(q.id);
            block.appendChild(retryBtn);
        }

        return block;
    }

    /**
     * 创建重新回答按钮
     */
    createRetryButton(questionId) {
        const btn = document.createElement('button');
        btn.className = 'btn-retry';
        btn.textContent = '🔄 重新回答 (-20💰)';
        btn.onclick = (e) => {
            e.stopPropagation();
            this.handleRetry(questionId);
        };

        if (this.currentGold < 20) {
            btn.disabled = true;
            btn.textContent = '💰 金币不足';
        }

        return btn;
    }

    /**
     * 同步金币到 HUD 显示
     */
    syncGoldToHUD() {
        const goldElement = document.getElementById('money-amount');
        if (goldElement) {
            goldElement.textContent = this.currentGold;
        }
        window.gameState.gold = this.currentGold;
    }

    /**
     * 处理答题
     */
    async handleAnswer(questionId, selectedLabel, btnElement) {
        if (!this.sessionId) return;
        if (this.answeredQuestions[questionId]) return;

        const block = btnElement.closest('.quiz-block');
        const allBtns = block.querySelectorAll('.quiz-option');
        allBtns.forEach(b => b.classList.add('quiz-option-disabled'));

        try {
            const resp = await fetch(`${API_BASE}/api/game/answer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    question_id: questionId,
                    selected_option: selectedLabel
                })
            });

            const data = await resp.json();

            this.answeredQuestions[questionId] = {
                selected: selectedLabel,
                correct: data.correct
            };

            if (data.gold !== undefined) {
                this.currentGold = data.gold;
                this.syncGoldToHUD();
            }

            this.saveQuestionStates();

            if (data.correct) {
                btnElement.classList.add('quiz-option-correct');
            } else {
                btnElement.classList.add('quiz-option-wrong');
                const retryBtn = this.createRetryButton(questionId);
                block.appendChild(retryBtn);
            }

            if (data.suspicion !== undefined) {
                this.updateSuspicion(data.suspicion);
            }

            if (data.victory) {
                this.allAnswered = true;
                if (this.onVictory) this.onVictory(data.title || '', data.story || '');
            } else if (data.game_over) {
                if (this.onGameOver) this.onGameOver(data.suspicion);
            }

        } catch (err) {
            console.error('[DeductionPanel] 答题提交失败:', err);
            allBtns.forEach(b => b.classList.remove('quiz-option-disabled'));
        }
    }

    /**
     * 处理重新回答
     */
    async handleRetry(questionId) {
        if (!this.sessionId) return;
        if (this.currentGold < 20) return;

        try {
            const resp = await fetch(`${API_BASE}/api/game/retry`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    question_id: questionId,
                    player_id: PLAYER_ID
                })
            });

            const data = await resp.json();

            if (data.success) {
                this.currentGold = data.gold;
                this.syncGoldToHUD();
                delete this.answeredQuestions[questionId];
                this.saveQuestionStates();
                this.render();
            } else {
                console.warn('[DeductionPanel] 重试失败:', data.message);
                if (data.gold !== undefined) {
                    this.currentGold = data.gold;
                    this.syncGoldToHUD();
                }
                this.render();
            }
        } catch (err) {
            console.error('[DeductionPanel] 重试请求失败:', err);
        }
    }

    /**
     * 更新怀疑度进度条
     */
    updateSuspicion(value) {
        if (this.suspicionFill) {
            this.suspicionFill.style.width = value + '%';

            if (value >= 80) {
                this.suspicionFill.style.background = 'linear-gradient(90deg, #c0392b, #e74c3c)';
            } else if (value >= 40) {
                this.suspicionFill.style.background = 'linear-gradient(90deg, #f39c12, #e67e22)';
            } else {
                this.suspicionFill.style.background = 'linear-gradient(90deg, #27ae60, #2ecc71)';
            }
        }
    }

    /**
     * 显示胜利面板
     */
    showVictory(title, story) {
        this.showEndPanel('案件告破', title, story, true);
    }

    /**
     * 显示失败面板
     */
    showGameOver(suspicion) {
        this.showEndPanel('调查失败', `怀疑度已达到 ${suspicion}%，犯人已逃脱...`, '', false);
    }

    /**
     * 显示结局面板（统一游戏风格）
     */
    showEndPanel(header, title, story, isVictory) {
        const overlay = document.createElement('div');
        overlay.className = 'end-overlay';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(38, 50, 56, 0.92); z-index: 500;
            display: flex; justify-content: center; align-items: center;
            font-family: 'Courier New', monospace;
        `;

        const panel = document.createElement('div');
        panel.style.cssText = `
            background: rgba(38, 50, 56, 0.95);
            border: 3px solid #5D4037;
            border-radius: 12px;
            padding: 40px 35px;
            max-width: 560px;
            width: 88%;
            text-align: center;
            color: #FFFFFF;
            box-shadow: 0 0 40px rgba(0, 0, 0, 0.6);
        `;

        const iconEl = document.createElement('div');
        iconEl.textContent = isVictory ? '✓' : '✗';
        iconEl.style.cssText = `
            font-size: 48px;
            margin-bottom: 15px;
            color: ${isVictory ? '#81C784' : '#EF9A9A'};
            text-shadow: 0 0 15px ${isVictory ? 'rgba(129, 199, 132, 0.5)' : 'rgba(239, 154, 154, 0.5)'};
        `;

        const headerEl = document.createElement('h2');
        headerEl.textContent = header;
        headerEl.style.cssText = `
            font-size: 26px;
            margin-bottom: 10px;
            color: #FFFFFF;
            letter-spacing: 4px;
            font-weight: bold;
        `;

        const divider = document.createElement('div');
        divider.style.cssText = `
            width: 60px;
            height: 2px;
            background: #5D4037;
            margin: 15px auto;
        `;

        const subEl = document.createElement('p');
        subEl.textContent = title || '';
        subEl.style.cssText = `
            font-size: 15px;
            margin-bottom: 15px;
            color: #B0BEC5;
            line-height: 1.6;
        `;

        const storyEl = document.createElement('div');
        if (story) {
            storyEl.textContent = story;
            storyEl.style.cssText = `
                font-size: 13px;
                line-height: 1.7;
                margin-bottom: 25px;
                text-align: left;
                max-height: 220px;
                overflow-y: auto;
                padding: 15px;
                background: rgba(93, 64, 55, 0.2);
                border: 1px solid rgba(93, 64, 55, 0.4);
                border-radius: 8px;
                color: #CFD8DC;
            `;
        }

        const btnEnd = document.createElement('button');
        btnEnd.textContent = '结  束';
        btnEnd.style.cssText = `
            padding: 12px 50px;
            font-size: 16px;
            background: #8D6E63;
            border: 2px solid #5D4037;
            border-radius: 8px;
            color: #FFFFFF;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            letter-spacing: 6px;
            transition: all 0.2s ease;
        `;

        btnEnd.onmouseover = () => {
            btnEnd.style.background = '#A1887F';
            btnEnd.style.transform = 'scale(1.05)';
            btnEnd.style.boxShadow = '0 0 15px rgba(141, 110, 99, 0.5)';
        };
        btnEnd.onmouseout = () => {
            btnEnd.style.background = '#8D6E63';
            btnEnd.style.transform = 'scale(1)';
            btnEnd.style.boxShadow = 'none';
        };
        btnEnd.onclick = () => {
            overlay.remove();
            this.clear();
            if (this.onEnd) this.onEnd();
        };

        panel.appendChild(iconEl);
        panel.appendChild(headerEl);
        panel.appendChild(divider);
        if (title) panel.appendChild(subEl);
        if (story) panel.appendChild(storyEl);
        panel.appendChild(btnEnd);
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
    }

    /**
     * 清空面板状态
     * @param {string} [sessionId] - 可选，指定要清除的会话ID；不传则使用 this.sessionId
     */
    clear(sessionId = null) {
        this.clearQuestionStates(sessionId);
        this.sessionId = null;
        this.questions = [];
        this.answeredQuestions = {};
        this.allAnswered = false;
        this.currentGold = (window.gameState && window.gameState.gold) ? window.gameState.gold : 100;
        this.updateSuspicion(0);

        const panelTitle = this.panelDeduction?.querySelector('.panel-title');
        if (panelTitle) panelTitle.textContent = '推论';

        this.render();
    }
}