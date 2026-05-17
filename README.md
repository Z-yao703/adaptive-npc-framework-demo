# Adaptive NPC Framework

面向中小型游戏开发团队的情境适应性 NPC 智能体框架，通过结构化配置约束大语言模型（LLM）的输出，实现可控且富有表现力的 NPC 行为生成。

## 核心特性

- **三层解耦架构**：应用层（游戏客户端）→ 协议层（AgentBridge SDK）→ 认知层（LLM 决策引擎），各层独立可替换
- **全双工事件驱动**：基于 WebSocket 的异步通信，游戏状态推送与 NPC 决策返回解耦
- **分层意图识别**："规则匹配 → Embedding 语义匹配 → LLM 推理" 三级策略，兼顾响应速度与理解精度
- **可控动作生成**：通过 Tool Calling 机制 + Schema 校验限制 LLM 输出空间，抑制幻觉
- **分层记忆管理**：短期对话记忆（SQLite）+ 长期关系摘要 + RAG 知识检索
- **结构化 NPC 配置**：JSON Schema 定义 NPC 人格、传感器、动作、任务等参数
- **可视化配置面板**：基于 React 的 Web 工具，图形化创建和调整 NPC
- **游戏引擎解耦**：AgentBridge SDK 以回调驱动方式对接任意游戏引擎
- **多 NPC 并发**：每个 NPC 拥有独立的对话、决策、记忆实例，状态完全隔离

## 运行环境

| 类别 | 要求 |
|------|------|
| 操作系统 | Windows 10/11、macOS 12+、Linux (Ubuntu 20.04+) |
| Python | 3.10+ |
| Node.js | 18.x+（仅游戏 Demo 和配置面板需要） |
| LLM API | 默认使用火山引擎 Ark API（Doubao 模型），可替换为其他兼容 OpenAI 接口的服务 |

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入 LLM API 密钥：

```env
ARK_API_KEY=你的API密钥
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 启动框架

```bash
python main.py
```

启动后访问：
- **使用说明书**：`http://localhost:8000/docs`
- **最小接入样例**：`http://localhost:8000/mygame`
- **健康检查**：`http://localhost:8000/api/health`

### 4. （可选）启动游戏 Demo

```bash
cd game_demo && npm install && npm run dev
```

### 5. （可选）启动 NPC 配置面板

```bash
cd tools/npc-config-tool && npm install && npm run dev
```

## 项目结构

```
adaptive-npc-framework-demo/
├── main.py                     # 框架主入口
├── requirements.txt            # Python 依赖
├── protocol.yaml               # 通信协议定义（单一真相源）
├── configs/                    # NPC 配置文件目录
│   ├── npc_registry.json       # NPC 注册表
│   ├── npc_*.json              # 各 NPC 配置
│   ├── world_*.json            # 世界背景配置
│   └── tasks_definition.json   # 任务定义
├── src/                        # 框架源码（Python）
│   ├── server/                 # 服务层（FastAPI 路由、框架核心、运行时管理）
│   ├── decision/               # 决策引擎（意图分类、意图处理、工具调用）
│   ├── memory/                 # 记忆管理（短期对话、长期关系、数据库 IO）
│   ├── knowledge/              # 知识引擎（RAG 检索、暗号匹配、输出护栏）
│   ├── logic/                  # 逻辑层（任务管理、状态追踪）
│   ├── communication/          # 通信层（对话管理、WebSocket 处理）
│   ├── config/                 # 配置加载器
│   └── utils/                  # 工具（LLM 客户端、日志、人格生成）
├── bridge/                     # 桥接层 SDK（JavaScript，与游戏引擎无关）
│   ├── core/                   # 核心：AgentBridge + 协议定义
│   ├── tools/                  # 工具：NPC 管理、渲染、事件总线、寻路
│   └── examples/               # 示例：最小接入模板
├── game_demo/                  # 游戏 Demo（Phaser3，独立于框架）
├── tools/npc-config-tool/      # NPC 可视化配置面板（React，独立于框架）
└── games/chaos_hotel/          # 混沌旅馆内置游戏服务端
```

## API 概览

### Agent 管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/agent/list` | 获取所有 NPC 列表 |
| GET | `/api/agent/{agent_id}` | 获取单个 NPC 配置 |
| POST | `/api/agent/save` | 保存/更新 NPC 配置（支持热更新） |
| DELETE | `/api/agent/{agent_id}` | 删除 NPC |
| POST | `/api/agent/{agent_id}/init` | 初始化 NPC（运行时加载） |
| POST | `/api/agent/{agent_id}/process` | 同步处理游戏状态，返回决策 |

### 世界背景管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/world/list` | 获取所有世界背景列表 |
| GET | `/api/world/{world_id}` | 获取单个世界背景配置 |
| POST | `/api/world/save` | 保存世界背景配置 |
| DELETE | `/api/world/{world_id}` | 删除世界背景 |

### 记忆管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/short_term_memory/{npc_id}` | 获取 NPC 短期对话记忆 |
| DELETE | `/api/short_term_memory/{npc_id}` | 清除 NPC 短期记忆 |

### 游戏会话

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/game/start` | 启动新游戏会话 |
| POST | `/api/game/answer` | 提交游戏答案 |

### WebSocket

| 端点 | 说明 |
|------|------|
| `/ws` | 默认 NPC 连接 |
| `/ws/{agent_id}` | 指定 NPC 连接 |

## NPC 配置

在 `configs/` 下创建 JSON 文件，示例：

```json
{
  "id": "my_npc",
  "version": "2.0",
  "meta": { "name": "老村长", "role": "villager" },
  "persona": {
    "identity": "晨曦镇的老村长，慈祥但有点固执。",
    "world_id": "",
    "greeting": "欢迎来到晨曦镇，年轻人！"
  },
  "sensors": { "detect_player": true },
  "actions": ["NPC_SAY", "MOVE_TO", "GIVE_ITEM", "START_QUEST"],
  "quests": []
}
```

关键字段：`id`（唯一标识）、`persona.identity`（注入 LLM System Prompt）、`sensors.detect_player`（启用玩家检测）、`actions`（可执行动作列表）、`quests`（关联任务）。

然后在 `configs/npc_registry.json` 中注册：

```json
{
  "version": "1.0",
  "default_agent": "my_npc",
  "agents": ["my_npc"]
}
```

## 游戏接入

通过 AgentBridge SDK（`bridge/core/agent_bridge.js`）接入：

```javascript
import { AgentBridge } from './bridge/core/agent_bridge.js';

const npc = new AgentBridge({
    agentId: 'my_npc',
    serverUrl: 'ws://localhost:8000/ws/my_npc',

    observe: () => ({
        player_id: 'player_001',
        player_position: { x: player.x, y: player.y },
        npc_position: { x: npc.sprite.x, y: npc.sprite.y },
        distance_to_player: distance(player, npc),
        player_inventory: inventory.items,
        player_message: lastInput
    }),

    onAction: (action) => {
        switch (action.type) {
            case 'NPC_SAY':
                showBubble(action.params.npc_id, action.params.text);
                break;
            case 'GIVE_ITEM':
                inventory.add(action.params.item, action.params.quantity);
                break;
            case 'MOVE_TO':
                npc.moveTo(action.params.x, action.params.y);
                break;
        }
    }
});

setInterval(() => npc.tick(), 200);
```

## 标准动作类型

| Action | 说明 | 关键参数 |
|--------|------|---------|
| `NPC_SAY` | NPC 说话 | npc_id, text, emotion |
| `NPC_EMOTE` | NPC 表情 | npc_id, emotion, duration |
| `MOVE_TO` | 移动到坐标 | npc_id, x, y, speed |
| `NPC_STOP` | 停止移动 | - |
| `GIVE_ITEM` | 给予物品 | npc_id, item, quantity |
| `TAKE_ITEM` | 拿走物品 | npc_id, item, quantity |
| `START_TRADE` | 打开交易面板 | npc_id, items |
| `START_QUEST` | 开始任务 | npc_id, quest_id, title, description |
| `UPDATE_QUEST` | 更新任务进度 | npc_id, quest_id, stage |
| `COMPLETE_QUEST` | 完成任务 | npc_id, quest_id, rewards |
| `GIVE_GOLD` | 给予金币 | npc_id, amount, reason |

动作定义详见 `protocol.yaml`，修改后运行 `python generate_protocols.py` 即可同步前后端协议代码。