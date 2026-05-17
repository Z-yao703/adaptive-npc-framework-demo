#!/usr/bin/env python3
"""
协议代码生成器

功能：读取 protocol.yaml 协议定义，生成：
1. bridge/core/protocol.js - 前端协议实现
2. src/protocol.py - 后端协议实现

使用方法：
1. 修改 protocol.yaml 中的协议定义
2. 运行本脚本：python generate_protocols.py
3. 脚本会自动覆盖现有的 protocol.js 和 protocol.py

注意事项：
1. 生成前请备份重要代码
2. 生成后请运行测试验证协议一致性
"""

import yaml
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# ==================== 配置 ====================
PROTOCOL_YAML = "protocol.yaml"
OUTPUT_JS = "bridge/core/protocol.js"
OUTPUT_PY = "src/protocol.py"

# ==================== 工具函数 ====================
def load_yaml(file_path: str) -> Dict[str, Any]:
    """加载 YAML 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def ensure_dir(file_path: str):
    """确保文件所在目录存在"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

# ==================== JavaScript 生成器 ====================
def generate_js_protocol(data: Dict[str, Any]) -> str:
    """生成 JavaScript 协议文件"""
    
    metadata = data.get('metadata', {})
    message_types = data.get('message_types', {})
    action_types = data.get('action_types', {})
    action_params = data.get('action_params', {})
    event_types = data.get('event_types', {})
    validation = data.get('validation', {})
    
    # 构建文件内容
    content = []
    content.append(f"""/**
 * Protocol - NPC 框架通信协议定义
 * 
 * 此文件由 generate_protocols.py 自动生成
 * 源文件: {PROTOCOL_YAML}
 * 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * 版本: {metadata.get('version', '1.0.0')}
 * 
 * 定义前后端通信的标准消息格式和 Action 类型
 * 这是框架的"契约层"，确保前后端对协议的理解一致
 */
""")
    
    # 1. 消息类型定义
    content.append("// =========================================")
    content.append("// 消息类型定义 (Message Types)")
    content.append("// =========================================")
    content.append("")
    
    # 客户端消息类型
    content.append("/**")
    content.append(" * 前端 → 后端 消息类型")
    content.append(" */")
    content.append("export const ClientMessageType = {")
    for msg_name, msg_info in message_types.get('client', {}).items():
        if msg_info.get('frontend_only', False):
            continue
        value = msg_info.get('value', msg_name)
        desc = msg_info.get('description', '')
        if desc:
            content.append(f"    {msg_name}: '{value}',   // {desc}")
        else:
            content.append(f"    {msg_name}: '{value}',")
    content.append("};")
    content.append("")
    
    # 服务器消息类型
    content.append("/**")
    content.append(" * 后端 → 前端 消息类型")
    content.append(" */")
    content.append("export const ServerMessageType = {")
    for msg_name, msg_info in message_types.get('server', {}).items():
        if msg_info.get('backend_only', False):
            continue
        value = msg_info.get('value', msg_name)
        desc = msg_info.get('description', '')
        if desc:
            content.append(f"    {msg_name}: '{value}',   // {desc}")
        else:
            content.append(f"    {msg_name}: '{value}',")
    content.append("};")
    content.append("")
    
    # 所有消息类型
    content.append("/**")
    content.append(" * 所有消息类型集合")
    content.append(" */")
    content.append("export const MessageType = {")
    content.append("    ...ClientMessageType,")
    content.append("    ...ServerMessageType")
    content.append("};")
    content.append("")
    
    # 2. Action 类型定义
    content.append("// =========================================")
    content.append("// Action 类型定义 (Action Types)")
    content.append("// =========================================")
    content.append("")
    content.append("/**")
    content.append(" * 标准 Action 类型")
    content.append(" * ")
    content.append(" * 分类：")
    for category_name, category_actions in action_types.items():
        if category_actions:
            category_desc = {
                'dialogue': '对话类',
                'movement': '移动类', 
                'interaction': '交互类',
                'quest': '任务类',
                'system': '系统类'
            }.get(category_name, category_name)
            content.append(f" * - {category_desc}：{', '.join(category_actions.keys())}")
    content.append(" */")
    content.append("export const ActionType = {")
    
    # 收集所有 Action 类型
    all_actions = []
    for category_actions in action_types.values():
        for action_name, action_info in category_actions.items():
            value = action_info.get('value', action_name)
            desc = action_info.get('description', '')
            if desc:
                all_actions.append(f"    {action_name}: '{value}',   // {desc}")
            else:
                all_actions.append(f"    {action_name}: '{value}',")
    
    # 按字母排序输出
    all_actions.sort()
    content.extend(all_actions)
    content.append("};")
    content.append("")
    
    # 3. Action 参数定义（作为文档注释）
    content.append("// =========================================")
    content.append("// Action 参数定义 (Action Params)")
    content.append("// =========================================")
    content.append("")
    
    for action_name, param_info in action_params.items():
        # 跳过 QUEST_COMMON，它不是 Action 类型，而是通用参数定义
        if action_name == 'QUEST_COMMON':
            continue
        
        content.append("/**")
        content.append(f" * {param_info.get('description', f'{action_name} Action 参数')}")
        content.append(" */")
        content.append(f"export const {action_name}Params = {{")
        
        # 添加必选参数
        required = param_info.get('required_params', {})
        for param_name, param_spec in required.items():
            param_type = param_spec.get('type', 'any')
            js_type_map = {
                'string': 'String',
                'number': 'Number', 
                'boolean': 'Boolean',
                'array': 'Array',
                'object': 'Object'
            }
            js_type = js_type_map.get(param_type, 'Object')
            desc = param_spec.get('description', '')
            if desc:
                content.append(f"    {param_name}: {js_type},   // {desc}")
            else:
                content.append(f"    {param_name}: {js_type},")
        
        # 添加可选参数
        optional = param_info.get('optional_params', {})
        for param_name, param_spec in optional.items():
            param_type = param_spec.get('type', 'any')
            js_type_map = {
                'string': 'String',
                'number': 'Number',
                'boolean': 'Boolean',
                'array': 'Array',
                'object': 'Object'
            }
            js_type = js_type_map.get(param_type, 'Object')
            desc = param_spec.get('description', '')
            default = param_spec.get('default', None)
            if default is not None:
                default_str = f"（默认: {default}）"
            else:
                default_str = ""
            if desc:
                content.append(f"    {param_name}: {js_type},   // {desc}{default_str}")
            else:
                content.append(f"    {param_name}: {js_type},")
        
        content.append("};")
        content.append("")
    
    # 4. 游戏事件类型
    content.append("// =========================================")
    content.append("// 事件类型定义 (Event Types)")
    content.append("// =========================================")
    content.append("")
    content.append("/**")
    content.append(" * 游戏事件类型")
    content.append(" */")
    content.append("export const GameEventType = {")
    
    events = event_types.get('events', {})
    for event_name, event_info in events.items():
        value = event_info.get('value', event_name.lower())
        desc = event_info.get('description', '')
        if desc:
            content.append(f"    {event_name}: '{value}',   // {desc}")
        else:
            content.append(f"    {event_name}: '{value}',")
    
    content.append("};")
    content.append("")
    
    # 5. 验证工具函数
    content.append("// =========================================")
    content.append("// 验证工具函数")
    content.append("// =========================================")
    content.append("")
    
    # validateMessage 函数
    content.append("/**")
    content.append(" * 验证消息格式是否正确")
    content.append(" * @param {Object} msg 消息对象")
    content.append(" * @returns {boolean} 是否有效")
    content.append(" */")
    content.append("export function validateMessage(msg) {")
    content.append("    if (!msg || typeof msg !== 'object') return false;")
    content.append("    if (!msg.type || typeof msg.type !== 'string') return false;")
    content.append("")
    content.append("    // 检查类型是否已知")
    content.append("    const allTypes = { ...MessageType };")
    content.append("    if (!Object.values(allTypes).includes(msg.type)) {")
    content.append("        console.warn(`[Protocol] Unknown message type: ${msg.type}`);")
    content.append("    }")
    content.append("")
    content.append("    return true;")
    content.append("}")
    content.append("")
    
    # validateAction 函数
    content.append("/**")
    content.append(" * 验证 Action 格式是否正确")
    content.append(" * @param {Object} action Action 对象")
    content.append(" * @returns {boolean} 是否有效")
    content.append(" */")
    content.append("export function validateAction(action) {")
    content.append("    if (!action || typeof action !== 'object') return false;")
    content.append("    if (!action.type || typeof action.type !== 'string') return false;")
    content.append("")
    content.append("    // 检查类型是否已知")
    content.append("    if (!Object.values(ActionType).includes(action.type)) {")
    content.append("        console.warn(`[Protocol] Unknown action type: ${action.type}`);")
    content.append("        return false;")
    content.append("    }")
    content.append("")
    content.append("    return true;")
    content.append("}")
    content.append("")
    
    # createMessage 函数
    content.append("/**")
    content.append(" * 创建标准消息")
    content.append(" * @param {string} type 消息类型")
    content.append(" * @param {Object} payload 消息负载")
    content.append(" * @returns {Object} 标准消息对象")
    content.append(" */")
    content.append("export function createMessage(type, payload = {}) {")
    content.append("    return {")
    content.append("        type,")
    content.append("        ...payload,")
    content.append("        timestamp: Date.now()")
    content.append("    };")
    content.append("}")
    content.append("")
    
    # createAction 函数
    content.append("/**")
    content.append(" * 创建标准 Action")
    content.append(" * @param {string} type Action 类型")
    content.append(" * @param {Object} params Action 参数")
    content.append(" * @returns {Object} 标准 Action 对象")
    content.append(" */")
    content.append("export function createAction(type, params = {}) {")
    content.append("    return {")
    content.append("        type,")
    content.append("        params")
    content.append("    };")
    content.append("}")
    content.append("")
    
    # 6. 默认导出
    content.append("// =========================================")
    content.append("// 默认导出")
    content.append("// =========================================")
    content.append("")
    content.append("export default {")
    content.append("    MessageType,")
    content.append("    ClientMessageType,")
    content.append("    ServerMessageType,")
    content.append("    ActionType,")
    content.append("    GameEventType,")
    content.append("    validateMessage,")
    content.append("    validateAction,")
    content.append("    createMessage,")
    content.append("    createAction")
    content.append("};")
    
    return "\n".join(content)

# ==================== Python 生成器 ====================
def generate_py_protocol(data: Dict[str, Any]) -> str:
    """生成 Python 协议文件"""
    
    metadata = data.get('metadata', {})
    action_types = data.get('action_types', {})
    action_params = data.get('action_params', {})
    
    content = []
    content.append(f'''"""
通信协议定义模块

此文件由 generate_protocols.py 自动生成
源文件: {PROTOCOL_YAML}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
版本: {metadata.get('version', '1.0.0')}

本模块定义标准的 Action 协议，供前后端通信使用。

核心原则：
- 后端只做"决策"，返回标准 Action
- 前端只做"执行"，解析标准 Action
- 协议是唯一的契约，任何游戏都可接入

标准输出格式：
{{
    "type": "ACTIONS",
    "actions": [
        {{"type": "NPC_SAY", "params": {{"npc_id": "...", "text": "..."}}}},
        {{"type": "MOVE_TO", "params": {{"npc_id": "...", "x": 100, "y": 200}}}}
    ]
}}

标准输入格式：
{{
    "type": "STATE_UPDATE",
    "state": {{
        "player_position": {{"x": 100, "y": 200}},
        "player_inventory": ["apple", "apple"],
        "distance_to_npc": 50
    }}
}}
"""

from typing import Dict, Any, List, Optional
''')
    
    # 1. ActionType 类
    content.append("")
    content.append("# ========================================")
    content.append("# 标准 Action 类型枚举")
    content.append("# ========================================")
    content.append("class ActionType:")
    content.append('    """标准 Action 类型常量"""')
    
    # 按类别组织 Action 类型
    for category_name, category_actions in action_types.items():
        if category_actions:
            # 添加类别注释
            category_desc = {
                'dialogue': '对话类',
                'movement': '移动类', 
                'interaction': '交互类',
                'quest': '任务类',
                'system': '系统类'
            }.get(category_name, category_name)
            content.append(f"    # {category_desc}")
            
            for action_name, action_info in category_actions.items():
                value = action_info.get('value', action_name)
                desc = action_info.get('description', '')
                if desc:
                    content.append(f'    {action_name} = "{value}"  # {desc}')
                else:
                    content.append(f'    {action_name} = "{value}"')
    
    content.append("")
    
    # 2. 基础工厂函数
    content.append("# ========================================")
    content.append("# Action 工厂函数")
    content.append("# ========================================")
    content.append("")
    content.append('def action(type_: str, **params) -> Dict[str, Any]:')
    content.append('    """')
    content.append('    创建单个 Action')
    content.append('    ')
    content.append('    Args:')
    content.append('        type_: Action 类型（如 NPC_SAY, MOVE_TO）')
    content.append('        **params: Action 参数')
    content.append('    ')
    content.append('    Returns:')
    content.append('        标准 Action 字典')
    content.append('    """')
    content.append('    return {')
    content.append('        "type": type_,')
    content.append('        "params": params')
    content.append('    }')
    content.append("")
    content.append("")
    content.append('def pack_actions(actions: List[Dict[str, Any]]) -> Dict[str, Any]:')
    content.append('    """')
    content.append('    打包多个 Action 为标准输出格式')
    content.append('    ')
    content.append('    Args:')
    content.append('        actions: Action 列表')
    content.append('    ')
    content.append('    Returns:')
    content.append('        标准 ACTIONS 消息')
    content.append('    """')
    content.append('    return {')
    content.append('        "type": "ACTIONS",')
    content.append('        "actions": actions')
    content.append('    }')
    content.append("")
    
    # 3. 便捷 Action 构造函数
    content.append("# ========================================")
    content.append("# 标准 Action 构造函数（便捷封装）")
    content.append("# ========================================")
    content.append("")
    
    # 为每个 Action 类型生成构造函数
    for category_name, category_actions in action_types.items():
        for action_name, action_info in category_actions.items():
            # 跳过 ERROR Action，因为已经手动添加了带参数的 error() 函数
            if action_name == 'ERROR':
                continue
            
            # 获取参数定义：优先使用 Action 自己的参数，否则检查是否复用 QUEST_COMMON
            if action_name in action_params:
                param_info = action_params.get(action_name, {})
            elif action_name in ['START_QUEST', 'UPDATE_QUEST', 'COMPLETE_QUEST']:
                # 任务类 Action 复用 QUEST_COMMON 参数定义
                param_info = action_params.get('QUEST_COMMON', {})
            else:
                param_info = {}
            
            # 确保 required_params 和 optional_params 是字典
            if isinstance(param_info, dict):
                required_params = param_info.get('required_params', {})
                optional_params = param_info.get('optional_params', {})
            else:
                required_params = {}
                optional_params = {}
            
            # 构建函数签名和文档
            func_name = action_name.lower()
            func_desc = action_info.get('description', f'{action_name} Action')
            
            # 构建参数列表
            param_lines = []
            doc_lines = []
            
            # 必需参数
            for param_name, param_spec in required_params.items():
                param_type = param_spec.get('type', 'Any')
                py_type_map = {
                    'string': 'str',
                    'number': 'float',
                    'boolean': 'bool',
                    'array': 'List',
                    'object': 'Dict'
                }
                py_type = py_type_map.get(param_type, 'Any')
                param_lines.append(f"{param_name}: {py_type}")
                
                desc = param_spec.get('description', '')
                if desc:
                    doc_lines.append(f"        {param_name}: {desc}")
            
            # 可选参数
            for param_name, param_spec in optional_params.items():
                param_type = param_spec.get('type', 'Any')
                py_type_map = {
                    'string': 'str',
                    'number': 'float',
                    'boolean': 'bool',
                    'array': 'List',
                    'object': 'Dict'
                }
                py_type = py_type_map.get(param_type, 'Any')
                default = param_spec.get('default', None)
                
                # 处理默认值
                if default is None:
                    param_lines.append(f"{param_name}: Optional[{py_type}] = None")
                else:
                    if isinstance(default, str):
                        default_str = f'"{default}"'
                    else:
                        default_str = str(default)
                    param_lines.append(f"{param_name}: {py_type} = {default_str}")
                
                desc = param_spec.get('description', '')
                if desc:
                    default_text = param_spec.get('default', '')
                    if default_text != '':
                        doc_lines.append(f"        {param_name}: {desc}（默认: {default_text}）")
                    else:
                        doc_lines.append(f"        {param_name}: {desc}")
            
            # 生成函数
            if param_lines:
                signature = f"def {func_name}({', '.join(param_lines)}) -> Dict[str, Any]:"
            else:
                signature = f"def {func_name}() -> Dict[str, Any]:"
            
            content.append(signature)
            content.append(f'    """')
            content.append(f'    {func_desc}')
            content.append(f'    ')
            content.append(f'    Args:')
            for doc_line in doc_lines:
                content.append(f'    {doc_line}')
            content.append(f'    ')
            content.append(f'    Returns:')
            content.append(f'        {action_name} Action')
            content.append(f'    """')
            
            # 函数体 - 构建参数字典
            all_params = list(required_params.keys()) + list(optional_params.keys())
            if all_params:
                params_dict = ", ".join([f"{p}={p}" for p in all_params])
                content.append(f'    return action(ActionType.{action_name}, {params_dict})')
            else:
                content.append(f'    return action(ActionType.{action_name})')
            
            content.append("")
            content.append("")
    
    # 4. 便捷响应函数
    content.append("# ========================================")
    content.append("# 便捷函数：构建完整响应")
    content.append("# ========================================")
    content.append("")
    
    # error 函数 - 生成 ERROR Action
    content.append('def error(message: str, npc_id: Optional[str] = None) -> Dict[str, Any]:')
    content.append('    """')
    content.append('    生成 ERROR Action')
    content.append('    ')
    content.append('    Args:')
    content.append('        message: 错误信息')
    content.append('        npc_id: NPC 标识（可选）')
    content.append('    ')
    content.append('    Returns:')
    content.append('        ERROR Action')
    content.append('    """')
    content.append('    params = {"message": message}')
    content.append('    if npc_id:')
    content.append('        params["npc_id"] = npc_id')
    content.append('    return action(ActionType.ERROR, **params)')
    content.append("")
    content.append("")
    
    content.append('def ok(actions: List[Dict[str, Any]]) -> Dict[str, Any]:')
    content.append('    """')
    content.append('    构建成功响应')
    content.append('    ')
    content.append('    Args:')
    content.append('        actions: Action 列表')
    content.append('    ')
    content.append('    Returns:')
    content.append('        标准 ACTIONS 消息')
    content.append('    """')
    content.append('    return pack_actions(actions)')
    content.append("")
    content.append("")
    content.append('def fail(message: str, npc_id: Optional[str] = None) -> Dict[str, Any]:')
    content.append('    """')
    content.append('    构建失败响应')
    content.append('    ')
    content.append('    Args:')
    content.append('        message: 错误信息')
    content.append('        npc_id: NPC 标识')
    content.append('    ')
    content.append('    Returns:')
    content.append('        包含 ERROR Action 的标准消息')
    content.append('    """')
    content.append('    return pack_actions([error(message, npc_id)])')
    
    return "\n".join(content)

# ==================== 主程序 ====================
def main():
    """主函数"""
    print(">> 开始生成协议代码...")
    
    try:
        # 1. 加载协议定义
        print(f">> 加载协议定义: {PROTOCOL_YAML}")
        data = load_yaml(PROTOCOL_YAML)
        
        # 2. 生成 JavaScript 协议
        print(f">> 生成 JavaScript 协议: {OUTPUT_JS}")
        js_content = generate_js_protocol(data)
        ensure_dir(OUTPUT_JS)
        with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        # 3. 生成 Python 协议
        print(f">> 生成 Python 协议: {OUTPUT_PY}")
        py_content = generate_py_protocol(data)
        ensure_dir(OUTPUT_PY)
        with open(OUTPUT_PY, 'w', encoding='utf-8') as f:
            f.write(py_content)
        
        # 4. 统计信息
        js_lines = len(js_content.split('\n'))
        py_lines = len(py_content.split('\n'))
        
        print(">> 协议代码生成完成！")
        print(f">> 生成统计:")
        print(f"   - JavaScript: {js_lines} 行")
        print(f"   - Python: {py_lines} 行")
        print(f"   - Action 类型: {sum(len(cat) for cat in data.get('action_types', {}).values())} 个")
        print(f"   - 消息类型: {len(data.get('message_types', {}).get('client', {})) + len(data.get('message_types', {}).get('server', {}))} 个")
        print("\n>> 重要提醒:")
        print("   1. 生成后请运行测试验证协议一致性")
        print("   2. 检查生成的文件是否正确替换了现有文件")
        print("   3. 如有问题，请检查 protocol.yaml 格式")
        
    except FileNotFoundError:
        print(f">> 错误: 找不到 {PROTOCOL_YAML} 文件")
        print(f"   请确保 {PROTOCOL_YAML} 与脚本在同一目录")
    except yaml.YAMLError as e:
        print(f">> YAML 解析错误: {e}")
        print("   请检查 protocol.yaml 文件格式")
    except Exception as e:
        print(f">> 生成过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
