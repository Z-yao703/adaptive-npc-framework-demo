/**
 * InteractionManager - 全局交互锁定管理器
 * 使用栈式锁定，支持嵌套锁定场景（如同时打开推论面板和对话窗口）
 * 所有地图对象交互（kitchen_counter、supply_closet、NPC点击）必须通过此类校验
 */
class InteractionManager {
    constructor() {
        this.lockStack = [];
    }

    /** 锁定交互，reason为锁定原因（如 loading、deduction_panel、dialogue） */
    lock(reason = 'default') {
        if (!this.lockStack.includes(reason)) {
            this.lockStack.push(reason);
        }
    }

    /** 解锁交互，需传入对应锁定原因 */
    unlock(reason = 'default') {
        const index = this.lockStack.indexOf(reason);
        if (index > -1) {
            this.lockStack.splice(index, 1);
        }
    }

    /** 检查当前是否允许地图交互 */
    isInteractionAllowed() {
        return this.lockStack.length === 0;
    }
}

export default new InteractionManager();
