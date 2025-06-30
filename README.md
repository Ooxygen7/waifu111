# CyberWaifu Bot

一个功能丰富的 Telegram AI 聊天机器人，支持多角色对话、群组管理、加密货币分析、数据库管理等高级功能。采用模块化架构设计，支持私聊和群聊场景，具备完善的权限管理和错误处理机制。

**测试版机器人：** https://t.me/waifucui_bot

---

## ✨ 核心特性

- 🤖 **多角色 AI 对话**：支持预设和自定义角色，角色切换，个性化对话体验
- 👥 **智能群组管理**：关键词触发、回复频率控制、群组角色管理
- 📊 **加密货币分析**：实时行情查询，AI 驱动的市场分析（支持多空倾向）
- 🛠️ **LLM 工具调用**：集成多种工具，支持数据库查询、市场分析等功能
- 🎯 **权限管理系统**：用户等级、管理员权限、群组权限精细控制
- 💾 **对话持久化**：对话保存/加载、历史记录管理
- 🌐 **Web 管理后台**：用户管理、数据统计、系统监控
- 🔧 **高度可扩展**：模块化架构，易于添加新功能和命令

## 📁 项目结构

```
cyberwaifu_bot/
├── 📄 bot_run.py                    # 🚀 应用启动入口
├── 📄 Dockerfile                    # 🐳 Docker 部署配置
├── 📄 requirements.txt              # 📦 Python 依赖包
├── 📄 README.md                     # 📖 项目文档
├── 📁 bot_core/                     # 🤖 机器人核心模块
│   ├── 📁 command_handlers/         # ⚡ 命令处理器
│   │   ├── 📄 base.py              # 🏗️ 命令基类和元数据
│   │   ├── 📄 private.py           # 👤 私聊命令（角色管理、对话控制、加密货币分析）
│   │   ├── 📄 group.py             # 👥 群组命令（群管、关键词、频率控制）
│   │   └── 📄 admin.py             # 🔐 管理员命令（用户管理、数据库操作）
│   ├── 📁 message_handlers/         # 💬 消息处理器
│   │   ├── 📄 private.py           # 👤 私聊消息处理
│   │   ├── 📄 group.py             # 👥 群组消息处理
│   │   └── 📁 features/            # 🎯 特殊功能（图片识别、角色创建等）
│   ├── 📁 callback_handlers/        # 🔄 回调查询处理
│   │   ├── 📄 callback.py          # 🎛️ 内联键盘回调处理
│   │   ├── 📄 inline.py            # ⌨️ 内联键盘生成
│   │   └── 📄 director_classes.py  # 🎬 导演模式（多角色对话）
│   └── 📁 public_functions/         # 🔧 公共功能模块
│       ├── 📄 conversation.py      # 💭 对话管理核心
│       ├── 📄 config.py            # ⚙️ 配置管理
│       ├── 📄 decorators.py        # 🎨 装饰器（权限检查、消息验证）
│       ├── 📄 messages.py          # 📨 消息发送和格式化
│       └── 📄 error.py             # ❌ 错误处理
├── 📁 LLM_tools/                    # 🛠️ LLM 工具调用系统
│   ├── 📄 tools.py                 # 🔨 工具实现（市场分析、数据库查询）
│   └── 📄 tools_registry.py        # 📋 工具注册和调用管理
├── 📁 utils/                        # 🔧 工具函数库
│   ├── 📄 LLM_utils.py             # 🧠 LLM API 封装和客户端管理
│   ├── 📄 db_utils.py              # 🗄️ 数据库操作（SQLite 连接池）
│   ├── 📄 file_utils.py            # 📂 文件处理（配置、角色、提示词）
│   ├── 📄 logging_utils.py         # 📝 日志系统
│   └── 📄 text_utils.py            # 📝 文本处理工具
├── 📁 web/                          # 🌐 Web 管理后台
│   ├── 📄 app.py                   # 🖥️ Flask Web 应用
│   ├── 📄 database.md              # 📊 数据库文档
│   └── 📁 templates/               # 🎨 Web 模板
├── 📁 config/                       # ⚙️ 配置文件
│   ├── 📄 config.json              # 🔧 主配置文件
│   └── 📄 director_menu.json       # 🎬 导演模式配置
├── 📁 characters/                   # 🎭 角色配置文件
├── 📁 prompts/                      # 💭 提示词模板
└── 📁 data/                         # 💾 数据存储
    ├── 📄 data.db                  # 🗄️ SQLite 数据库
    └── 📁 pics/                    # 🖼️ 图片存储
```

## 🏗️ 系统架构

### 1. 📨 消息处理系统
- **双模式支持**：私聊和群聊消息智能路由
- **消息验证**：过期检查、用户验证、权限控制
- **触发机制**：关键词触发、@提及、回复检测
- **装饰器架构**：`@ensure_user_info_updated`、`@check_message_expiration` 等
- **异常处理**：完善的错误捕获和用户友好提示

### 2. ⚡ 命令处理系统
- **模块化设计**：私聊、群组、管理员命令分离
- **元数据驱动**：`CommandMeta` 类定义命令属性
- **权限控制**：用户等级、管理员权限、群组权限
- **动态注册**：自动扫描和注册命令处理器
- **菜单生成**：根据权限动态生成命令菜单

### 3. 🎭 角色管理系统
- **角色库**：预设角色 + 用户自定义角色
- **状态持久化**：角色配置、对话历史、用户偏好
- **切换机制**：无缝角色切换，自动重置对话上下文
- **个性化**：支持角色昵称、问候语、行为模式定制
- **文件管理**：JSON 格式角色配置，支持导入导出

### 4. 🛠️ LLM 工具调用系统
- **工具注册表**：`MarketToolRegistry`、`DatabaseToolRegistry` 等
- **异步调用**：支持并发工具执行
- **结果格式化**：工具输出的智能格式化和展示
- **错误处理**：工具调用失败的优雅降级
- **扩展性**：易于添加新工具和功能

### 5. 💾 数据持久化
- **连接池管理**：SQLite 连接池，支持并发访问
- **事务处理**：数据一致性保证
- **用户数据**：个人配置、对话历史、使用统计
- **群组数据**：群组配置、消息记录、权限设置
- **备份恢复**：数据导出导入功能

### 6. 🌐 Web 管理后台
- **用户管理**：用户信息查看、权限修改、额度管理
- **数据统计**：使用情况分析、热门功能统计
- **系统监控**：实时状态监控、日志查看
- **配置管理**：在线配置修改、角色管理
- **安全认证**：登录验证、会话管理

## 快速开始

### 依赖环境
- Python 3.12+
- pip
- Docker（可选，推荐生产环境部署）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置
1. 复制 `config/config.json`，填写 Telegram Bot Token、API Keys、管理员等信息
2. 自定义 `characters/` 角色配置
3. 编辑 `prompts/` 预设文件

### 启动方式

#### 本地运行
```bash
python bot_run.py
```

#### Docker 部署
```bash
docker build -t cyber-waifu-bot .
docker run -d --name cyber-waifu-container \
  -v "${PWD}/config:/app/config" \
  -v "${PWD}/prompts:/app/prompts" \
  -v "${PWD}/data:/app/data" \
  -v "${PWD}/characters:/app/characters" \
  cyber-waifu-bot
```

> Windows PowerShell 下 `${PWD}` 表示当前目录，CMD 用 `%CD%`

## 📖 命令手册

### 👤 私聊命令

#### 🎯 基础功能
| 命令 | 描述 | 示例 |
|------|------|------|
| `/start` | 欢迎消息和功能介绍 | `/start` |
| `/help` | 详细帮助文档 | `/help` |
| `/me` | 查看个人信息和使用统计 | `/me` |
| `/sign` | 每日签到获取额度奖励 | `/sign` |

#### 🎭 角色管理
| 命令 | 描述 | 示例 |
|------|------|------|
| `/char` | 查看当前角色和角色列表 | `/char` |
| `/newchar [角色名]` | 创建自定义角色 | `/newchar 我的助手` |
| `/delchar` | 删除已有角色 | `/delchar` |
| `/nick [昵称]` | 修改当前角色昵称 | `/nick 小助手` |

#### 💬 对话管理
| 命令 | 描述 | 示例 |
|------|------|------|
| `/new` | 开始新的对话会话 | `/new` |
| `/save [标题]` | 保存当前对话 | `/save 重要讨论` |
| `/load` | 加载历史对话 | `/load` |
| `/delete` | 删除指定对话记录 | `/delete` |
| `/undo` | 撤销上一条消息 | `/undo` |
| `/regen` | 重新生成AI回复 | `/regen` |

#### ⚙️ 设置配置
| 命令 | 描述 | 示例 |
|------|------|------|
| `/setting` | 个人设置菜单 | `/setting` |
| `/api` | 切换LLM模型 | `/api` |
| `/preset` | 管理对话预设 | `/preset` |
| `/stream` | 切换流式输出模式 | `/stream` |

#### 📊 高级功能
| 命令 | 描述 | 示例 |
|------|------|------|
| `/c [币种] [参数]` | 加密货币分析 | `/c btc long` |
| `/crypto [币种] [参数]` | 加密货币分析（完整命令） | `/crypto ethereum short` |
| `/director` | 导演模式（多角色对话） | `/director` |
| `/done` | 标记任务完成 | `/done` |

**加密货币分析参数说明：**
- `long` - 多头分析倾向
- `short` - 空头分析倾向  
- 无参数 - 中性分析

### 👥 群组命令

#### 🛠️ 群组管理（需要管理员权限）
| 命令 | 描述 | 示例 |
|------|------|------|
| `/remake` | 重置群聊对话上下文 | `/remake` |
| `/switch` | 切换群组角色 | `/switch` |
| `/rate [0-1]` | 设置回复概率 | `/rate 0.3` |
| `/kw` | 管理关键词触发 | `/kw` |
| `/e` | 启用群聊话题讨论 | `/e` |
| `/d` | 禁用群聊话题讨论 | `/d` |

#### 📊 群组功能
| 命令 | 描述 | 示例 |
|------|------|------|
| `/cc [币种] [参数]` | 群聊加密货币分析 | `/cc btc long` |

### 🔐 管理员命令

| 命令 | 描述 | 示例 |
|------|------|------|
| `/addf [用户ID/all] [数量]` | 增加用户额度 | `/addf 123456 100` |
| `/sett [用户ID] [等级]` | 修改用户等级 | `/sett 123456 2` |
| `/q [查询]` | 数据库查询分析 | `/q 查看用户统计` |

## 🛠️ 开发指南

### 🏗️ 架构设计原则

#### 1. 模块化设计
```
bot_core/
├── command_handlers/     # 命令处理层
│   ├── base.py          # 基类和元数据系统
│   ├── private.py       # 私聊命令实现
│   ├── group.py         # 群组命令实现
│   └── admin.py         # 管理员命令实现
├── message_handlers/     # 消息处理层
├── callback_handlers/    # 回调处理层
└── public_functions/     # 公共功能层
```

#### 2. 数据访问层
```
utils/
├── db_utils.py          # 数据库连接池和操作
├── LLM_utils.py         # LLM客户端管理
├── file_utils.py        # 文件和配置管理
└── logging_utils.py     # 日志系统
```

#### 3. 业务逻辑层
```
LLM_tools/
├── tools.py             # 工具实现
└── tools_registry.py    # 工具注册和调用
```

### 🔧 扩展开发

#### 添加新命令
```python
# 在 bot_core/command_handlers/ 中创建新命令
class MyCommand(BaseCommand):
    meta = CommandMeta(
        name='my_command',
        command_type='private',  # 或 'group', 'admin'
        trigger='mycmd',
        menu_text='我的命令',
        show_in_menu=True,
        menu_weight=10,
        bot_admin_required=False  # 可选的权限要求
    )
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # 命令处理逻辑
        await update.message.reply_text("Hello from my command!")
```

#### 添加新工具
```python
# 在 LLM_tools/tools.py 中添加工具
async def my_tool(param1: str, param2: int) -> str:
    """我的自定义工具
    
    Args:
        param1: 参数1描述
        param2: 参数2描述
        
    Returns:
        工具执行结果
    """
    # 工具逻辑实现
    return f"结果: {param1} - {param2}"

# 在 tools_registry.py 中注册
MY_TOOLS = {
    "my_tool": {
        "description": "我的自定义工具描述",
        "parameters": {
            "param1": {"type": "string", "description": "参数1"},
            "param2": {"type": "integer", "description": "参数2"}
        }
    }
}
```

#### 添加新角色
```json
// 在 characters/ 目录下创建 my_character.json
{
    "name": "我的角色",
    "description": "角色描述",
    "personality": "角色性格设定",
    "meeting": "初次见面的问候语",
    "example_dialogue": [
        {"user": "用户示例", "assistant": "角色回复示例"}
    ]
}
```

### 🔍 错误处理体系

#### 1. 分层错误处理
```python
# 全局错误处理器 (bot_run.py)
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 处理所有未捕获的异常
    
# 装饰器错误处理 (decorators.py)
@Decorators.ensure_user_info_updated
@Decorators.check_message_expiration
async def message_handler(update, context):
    # 消息级别的错误处理
    
# 业务逻辑错误处理
try:
    result = await some_operation()
except SpecificError as e:
    logger.error(f"具体错误: {e}")
    await update.message.reply_text("用户友好的错误提示")
```

#### 2. 错误类型定义
```python
# bot_core/public_functions/error.py
class BotError(Exception):
    """Bot运行时错误基类"""
    
class ConfigError(BotError):
    """配置错误"""
    
class DatabaseError(BotError):
    """数据库错误"""
```

### 📊 性能优化

#### 1. 数据库连接池
```python
# utils/db_utils.py
class DatabaseConnectionPool:
    # 单例模式的连接池管理
    # 支持并发访问和连接复用
```

#### 2. LLM客户端管理
```python
# utils/LLM_utils.py
class LLMClientManager:
    # 异步客户端池
    # 并发控制和资源管理
```

#### 3. 异步处理
```python
# 所有I/O操作都使用异步
async def handle_message():
    async with llm_client_manager.semaphore:
        # 控制并发数量
        result = await llm_client.chat.completions.create(...)
```

## 🤝 贡献指南

### 开发流程
1. **Fork 项目** → 创建功能分支 → 开发测试 → 提交 PR
2. **代码规范**：遵循 PEP 8，使用类型注解
3. **提交规范**：清晰的提交信息，功能完整的提交
4. **文档更新**：同步更新相关文档和注释

### 测试要求
- 本地测试所有修改功能
- 确保不破坏现有功能
- 添加必要的错误处理
- 更新相关文档

## ❓ 常见问题

### 🔧 部署相关
**Q: 如何获取 Telegram Bot Token？**
A: 联系 [@BotFather](https://t.me/BotFather) 创建机器人并获取 Token

**Q: 如何配置 LLM API？**
A: 在 `config/config.json` 中配置 API 密钥和端点，支持 OpenAI、Claude、Gemini 等

**Q: Docker 部署注意事项？**
A: 确保挂载 `config`、`data`、`characters`、`prompts` 目录以持久化数据

### 🐛 故障排除
**Q: 机器人无响应怎么办？**
A: 检查 `data/bot.log` 日志文件，查看错误信息和网络连接状态

**Q: 数据库错误如何处理？**
A: 检查 `data/data.db` 文件权限，确保应用有读写权限

**Q: 群组中机器人不回复？**
A: 确保机器人有群组消息权限，检查关键词设置和回复频率配置

### 🎯 功能使用
**Q: 如何创建自定义角色？**
A: 使用 `/newchar 角色名` 命令，然后按提示输入角色设定

**Q: 加密货币分析支持哪些币种？**
A: 支持主流加密货币，如 BTC、ETH、BNB 等，使用币种符号或全名

**Q: 如何备份对话数据？**
A: 定期备份 `data/data.db` 文件，或使用 Web 后台的导出功能

## 🚀 未来规划

### 短期目标 (1-3个月)
- [ ] 🌍 **多语言支持**：国际化适配，支持英文、日文等
- [ ] 📱 **移动端优化**：改进移动设备上的交互体验
- [ ] 🔊 **语音支持**：语音消息识别和合成
- [ ] 🎨 **主题系统**：可自定义的界面主题

### 中期目标 (3-6个月)
- [ ] 🤖 **AI Agent 系统**：更智能的任务执行和工具调用
- [ ] 📊 **高级分析**：用户行为分析和个性化推荐
- [ ] 🔗 **API 开放**：提供第三方集成接口
- [ ] 🛡️ **安全增强**：端到端加密和隐私保护

### 长期目标 (6个月+)
- [ ] 🌐 **分布式部署**：支持多实例负载均衡
- [ ] 🧠 **本地模型**：支持本地部署的开源模型
- [ ] 🎮 **游戏化功能**：积分系统、成就系统
- [ ] 🤝 **社区功能**：用户间的角色分享和交流

## 📞 支持与反馈

- 🐛 **Bug 报告**：[GitHub Issues](https://github.com/your-repo/issues)
- 💡 **功能建议**：[GitHub Discussions](https://github.com/your-repo/discussions)
- 📧 **联系开发者**：[@Xi_cuicui](https://t.me/Xi_cuicui)
- 📖 **项目文档**：[Wiki](https://github.com/your-repo/wiki)

---

⭐ **如果这个项目对你有帮助，请给个 Star 支持一下！**

💖 **感谢所有贡献者和用户的支持！**
