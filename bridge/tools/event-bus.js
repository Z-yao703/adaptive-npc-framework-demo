/**
 * EventBus - 轻量级事件总线
 * 
 * 提供发布/订阅模式的事件系统
 * 用于解耦游戏各模块之间的通信
 * 
 * 使用示例：
 * ```javascript
 * import { EventBus } from './event-bus.js';
 * 
 * // 订阅事件
 * EventBus.on('npc:say', (data) => {
 *     console.log(data.text);
 * });
 * 
 * // 发布事件
 * EventBus.emit('npc:say', { text: 'Hello!' });
 * 
 * // 取消订阅
 * const handler = (data) => {};
 * EventBus.on('npc:say', handler);
 * EventBus.off('npc:say', handler);
 * ```
 */

class EventBus {
    constructor() {
        this._events = new Map();
    }

    /**
     * 订阅事件
     * @param {string} event 事件名称
     * @param {Function} handler 处理函数
     * @returns {EventBus} 返回 this 支持链式调用
     */
    on(event, handler) {
        if (!this._events.has(event)) {
            this._events.set(event, []);
        }
        this._events.get(event).push(handler);
        return this;
    }

    /**
     * 订阅事件（只执行一次）
     * @param {string} event 事件名称
     * @param {Function} handler 处理函数
     * @returns {EventBus} 返回 this 支持链式调用
     */
    once(event, handler) {
        const wrapper = (...args) => {
            handler(...args);
            this.off(event, wrapper);
        };
        wrapper._original = handler;
        return this.on(event, wrapper);
    }

    /**
     * 取消订阅
     * @param {string} event 事件名称
     * @param {Function} handler 处理函数（如果不提供，取消该事件所有订阅）
     * @returns {EventBus} 返回 this 支持链式调用
     */
    off(event, handler) {
        if (!this._events.has(event)) return this;

        if (!handler) {
            this._events.delete(event);
        } else {
            const handlers = this._events.get(event);
            const index = handlers.findIndex(h => h === handler || h._original === handler);
            if (index !== -1) {
                handlers.splice(index, 1);
            }
            if (handlers.length === 0) {
                this._events.delete(event);
            }
        }
        return this;
    }

    /**
     * 发布事件
     * @param {string} event 事件名称
     * @param {*} data 事件数据
     * @returns {boolean} 是否有处理函数执行
     */
    emit(event, data) {
        if (!this._events.has(event)) return false;

        const handlers = this._events.get(event);
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (e) {
                console.error(`[EventBus] Error in handler for event "${event}":`, e);
            }
        });
        return handlers.length > 0;
    }

    /**
     * 清除所有事件订阅
     * @returns {EventBus} 返回 this 支持链式调用
     */
    clear() {
        this._events.clear();
        return this;
    }

    /**
     * 获取事件的所有订阅者数量
     * @param {string} event 事件名称
     * @returns {number} 订阅者数量
     */
    listenerCount(event) {
        if (!this._events.has(event)) return 0;
        return this._events.get(event).length;
    }

    /**
     * 获取所有已注册的事件名称
     * @returns {string[]} 事件名称数组
     */
    eventNames() {
        return Array.from(this._events.keys());
    }
}

// 创建默认实例（单例模式）
const defaultEventBus = new EventBus();

// =========================================
// 导出
// =========================================

// ES Module 导出
export { EventBus, defaultEventBus as EventBus };

// 默认导出默认实例
export default defaultEventBus;
