# CyberWaifu Bot

一个功能强大的 Telegram AI 聊天机器人，基于现代化的分层架构设计。支持多角色对话、加密货币分析、智能群组管理等高级功能，采用模块化设计确保高可维护性和可扩展性。

**测试版机器人：** https://t.me/waifucui_bot

---

## ✨ 核心特性

- 🤖 **多角色 AI 对话**：支持预设和自定义角色，智能对话管理
- 📊 **加密货币分析**：集成 CCXT 库的实时市场数据分析，支持多空倾向分析
- 👥 **智能群组管理**：关键词触发、回复频率控制、用户权限管理
- 🛠️ **LLM 工具调用**：统一的工具注册和调用系统，支持数据库查询和市场分析
- 🌐 **Web 管理后台**：基于 Flask 的现代化管理界面
- 💾 **数据持久化**：SQLite 数据库 + 仓库模式的数据访问层
- 🔧 **高度可扩展**：模块化架构，易于添加新功能

## 📁 项目架构

```
cyberwaifu_bot/
├── 📄 bot_run.py                    # 🚀 应用启动入口
├── 📄 Dockerfile                    # 🐳 Docker 部署配置
├── 📄 requirements.txt              # 📦 Python 依赖包
├── 📁 agent/                        # 🧠 AI Agent & 工具系统
│   ├── 📄 llm_functions.py          # 💡 LLM 核心功能 (用户画像生成等)
│   ├── 📄 tools.py                  # 🔨 工具实现 (市场分析, 数据库操作)
│   ├── 📄 tools_handler.py          # 🔄 工具调用处理器
│   └── 📄 tools_registry.py         # 📋 工具注册与提示生成
├── 📁 bot_core/                     # 🤖 机器人核心模块
│   ├── 📄 models.py                 # 📊 数据模型定义
│   ├── 📄 repository.py             # 🏪 传统数据访问层
│   ├── 📁 callback_handlers/        # 🔄 回调查询处理器
│   ├── 📁 command_handlers/         # ⚡ 命令处理器
│   │   ├── 📄 base.py              # 🏗️ 命令基类
│   │   ├── 📄 admin.py             # 🔐 管理员命令
│   │   ├── 📄 group.py             # 👥 群组命令
│   │   ├── 📄 private.py           # 👤 私聊命令
│   │   └── 📄 regist.py            # ✍️ 命令注册系统
│   ├── 📁 data_repository/          # 🗄️ 新数据访问层
│   │   ├── 📄 conversations_repository.py
│   │   ├── 📄 groups_repository.py
│   │   ├── 📄 users_repository.py
│   │   └── 📄 user_config_repository.py
│   ├── 📁 inline_handlers/          # 🔍 内联查询处理器
│   ├── 📁 message_handlers/         # 💬 消息处理器
│   ├── 📁 services/                 # 🔧 业务逻辑服务
│   │   ├── 📄 conversation.py      # 💭 对话服务
│   │   ├── 📄 messages.py          # 📨 消息服务
│   │   └── 📁 utils/              # 🛠️ 服务工具
│   └── 📁 web/                     # 🌐 Web 管理后台
├── 📁 characters/                   # 🎭 角色配置文件
├── 📁 config/                       # ⚙️ 配置文件
├── 📁 data/                         # 💾 数据存储
├── 📁 prompts/                      # 💭 提示词模板
├── 📁 utils/                        # 🛠️ 通用工具函数
│   ├── 📄 auth_utils.py            # 🔐 认证工具
│   ├── 📄 config_utils.py          # ⚙️ 配置管理
│   ├── 📄 db_utils.py              # 🗄️ 数据库操作
│   ├── 📄 LLM_utils.py             # 🧠 LLM 工具
│   └── 📄 text_utils.py            # 📝 文本处理
└── 📁 web/                          # 🌐 Web 管理后台
    ├── 📄 app.py                    # 🚀 Flask 应用
    ├── 📄 factory.py                # 🏭 应用工厂
    ├── 📁 blueprints/               # 🧩 功能模块
    ├── 📁 static/                   # 🎨 静态资源
    └── 📁 templates/                # 📄 HTML 模板
```

## 🏗️ 系统架构

### 1. 📨 消息处理架构

- **分层消息处理**：消息 → 处理器 → 服务 → 响应
- **智能路由**：私聊/群组消息自动路由到对应处理器
- **异步处理**：基于 asyncio 的高并发消息处理
- **错误恢复**：完善的错误处理和重试机制

### 2. 🧠 AI Agent 系统

- **统一工具接口**：标准化工具注册和调用
- **智能提示生成**：动态构建包含上下文的提示词
- **多模型支持**：支持 OpenAI、Claude、Gemini 等主流 LLM
- **工具链执行**：支持单个和批量工具调用

### 3. 💾 数据访问层

- **双重仓库架构**：
  - `repository.py` - 传统综合性仓库
  - `data_repository/` - 专用细粒度仓库
- **连接池管理**：SQLite 连接池优化
- **事务安全**：保证数据一致性

### 4. 🌐 Web 管理后台

- **现代化架构**：基于 Flask + Blueprint
- **响应式设计**：移动端友好的管理界面
- **实时数据**：动态统计和监控
- **安全认证**：基于会话的管理后台访问控制

## 🚀 快速开始

### 环境要求

- Python 3.12+
- pip
- Docker（可选，推荐生产环境）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置说明

1. **Telegram Bot 配置**
   ```bash
   # 联系 @BotFather 创建机器人并获取 Token
   # 在 BotFather 中启用内联模式
   ```

2. **配置文件**
   - 复制 `config/config.json` 为 `config/config_local.json`
   - 填写 Telegram Bot Token、API Keys 等敏感信息

3. **角色配置**
   - 在 `characters/` 目录下添加角色 JSON 文件
   - 自定义 `prompts/` 提示词模板

### 启动方式

#### 本地开发
```bash
python bot_run.py
```

#### Docker 部署
```bash
docker build -t cyber-waifu-bot .
docker run -d --name cyber-waifu-bot \
  -v "${PWD}/config:/app/config" \
  -v "${PWD}/data:/app/data" \
  -v "${PWD}/characters:/app/characters" \
  -v "${PWD}/prompts:/app/prompts" \
  cyber-waifu-bot
```

## 📖 命令手册

### 👤 私聊命令

#### 基础功能
- `/start` - 欢迎消息和功能介绍
- `/help` - 详细帮助文档
- `/me` - 查看个人信息和使用统计

#### 角色管理
- `/char` - 查看当前角色和角色列表
- `/newchar [角色名]` - 创建自定义角色
- `/delchar` - 删除角色

#### 对话管理
- `/new` - 开始新的对话
- `/save` - 保存当前对话并自动总结
- `/dialog` - 加载历史对话
- `/undo` - 撤销上一条消息

#### 加密货币分析
- `/c [参数] [指令]` - AI 驱动的加密货币分析
  - `long` - 多头倾向分析
  - `short` - 空头倾向分析
  - 无参数 - 中性分析

### 👥 群组命令

#### 群组管理（管理员）
- `/switch` - 切换群组角色
- `/rate [0-1]` - 设置回复概率
- `/kw` - 管理关键词触发
- `/enable` - 启用群聊话题讨论
- `/disable` - 禁用群聊话题讨论

#### 群组功能
- `/cc [币种] [参数]` - 群聊加密货币分析
- `/remake` - 重置群聊对话上下文

### 🔐 管理员命令

- `/addf [用户ID/all] [数量]` - 增加用户额度
- `/sett [用户ID] [等级]` - 修改用户等级
- `/q [查询]` - 数据库查询分析

## 🔧 扩展开发

### 添加新命令

```python
# 在 bot_core/command_handlers/ 中创建新命令
from bot_core.command_handlers.base import BaseCommand, CommandMeta

class MyCommand(BaseCommand):
    meta = CommandMeta(
        name='my_command',
        command_type='private',
        trigger='mycmd',
        menu_text='我的命令',
        show_in_menu=True,
        menu_weight=10
    )

    async def handle(self, update, context):
        await update.message.reply_text("Hello from my command!")
```

### 添加新工具

```python
# 1. 在 agent/tools.py 中实现工具
class MyTools:
    @staticmethod
    async def my_tool(param: str) -> dict:
        return {
            "display": f"处理结果: {param}",
            "llm_feedback": f"Tool executed with {param}"
        }

# 2. 在 agent/tools_registry.py 中注册
```

### 数据访问

```python
# 使用新的仓库模式
from bot_core.data_repository.users_repository import UsersRepository

user_data = UsersRepository.user_info_get(user_id)
```

## 🤝 贡献指南

### 开发流程

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 遵循 PEP 8 代码风格
- 使用类型注解
- 添加必要的文档字符串
- 确保通过代码质量检查

## ❓ 常见问题

### 部署相关

**Q: 如何获取 Telegram Bot Token？**
A: 联系 [@BotFather](https://t.me/BotFather) 创建机器人并获取 Token

**Q: 如何配置 LLM API？**
A: 在 `config/config_local.json` 中配置 API 密钥和端点

**Q: Docker 部署注意事项？**
A: 确保挂载 config、data、characters、prompts 目录以持久化数据

### 功能使用

**Q: 如何创建自定义角色？**
A: 使用 `/newchar 角色名` 命令，然后按提示输入角色设定

**Q: 加密货币分析支持哪些币种？**
A: 支持主流加密货币，使用币种符号或全名查询

### 故障排除

**Q: 机器人无响应怎么办？**
A: 检查 `data/bot.log` 日志文件，查看错误信息

**Q: 数据库错误如何处理？**
A: 确保数据库文件权限正确，检查连接池配置

---

⭐ **如果这个项目对你有帮助，请给个 Star 支持一下！**

💖 **感谢所有贡献者和用户的支持！**
