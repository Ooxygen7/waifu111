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
├── 📄 .gitignore                    # Git 忽略文件
├── 📄 bot_run.py                    # 🚀 应用启动入口
├── 📄 Dockerfile                    # 🐳 Docker 部署配置
├── 📄 LICENSE                       # 📄 开源许可证
├── 📄 requirements.txt              # 📦 Python 依赖包
├── 📄 README.md                     # 📖 项目文档
├── 📁 agent/                        # 🧠 LLM Agent & 工具系统
│   ├── 📄 llm_functions.py          # 💡 调用LLM的核心功能 (例如用户画像)
│   ├── 📄 tools.py                  # 🔨 工具实现 (市场分析, 数据库操作)
│   ├── 📄 tools_handler.py          # 🔄 工具调用处理器
│   └── 📄 tools_registry.py         # 📋 工具注册与提示生成
├── 📁 bot_core/                     # 🤖 机器人核心模块
│   ├── 📁 callback_handlers/        # 🔄 回调查询 (Callback Query) 处理器
│   │   ├── 📄 base.py              # 🏗️ 回调处理器基类
│   │   ├── 📄 callback.py          # 🎛️ 通用内联键盘回调
│   │   ├── 📄 director_classes.py  # 🎬 导演模式 (多角色对话) 回调
│   │   └── 📄 inline.py            # ⌨️ 内联键盘生成与管理
│   ├── 📁 command_handlers/         # ⚡ 命令 (Command) 处理器
│   │   ├── 📄 base.py              # 🏗️ 命令基类和元数据
│   │   ├── 📄 admin.py             # 🔐 管理员命令
│   │   ├── 📄 group.py             # 👥 群组命令
│   │   ├── 📄 private.py           # 👤 私聊命令
│   │   └── 📄 regist.py            # ✍️ 命令注册
│   ├── 📁 inline_handlers/          # 🔍 内联查询 (Inline Query) 处理器
│   │   ├── 📄 base.py              # 🏗️ 内联查询基类
│   │   ├── 📄 character.py         # 🎭 角色查询
│   │   ├── 📄 default.py           # 💡 默认查询
│   │   ├── 📄 help.py              # 📖 帮助查询
│   │   ├── 📄 inline.py            # 🔄 查询路由与分发
│   │   └── 📄 preset.py            # ⚙️ 预设查询
│   ├── 📁 message_handlers/         # 💬 消息 (Message) 处理器
│   │   ├── 📄 features.py          # 🎯 特殊功能消息 (图片识别等)
│   │   ├── 📄 group.py             # 👥 群组消息
│   │   └── 📄 private.py           # 👤 私聊消息
│   └── 📁 public_functions/         # 🔧 公共功能模块
│       ├── 📄 config.py            # ⚙️ 配置管理
│       ├── 📄 conversation.py      # 💭 对话管理核心
│       ├── 📄 decorators.py        # 🎨 装饰器 (权限检查等)
│       ├── 📄 error.py             # ❌ 错误处理
│       ├── 📄 frequency_manager.py # 📊 频率和额度管理
│       ├── 📄 messages.py          # 📨 消息发送与格式化
│       └── 📄 update_parse.py      # 📥 Update对象解析
├── 📁 characters/                   # 🎭 角色配置文件
├── 📁 config/                       # ⚙️ 配置文件
├── 📁 data/                         # 💾 数据存储
├── 📁 docs/                         # 📚 项目文档
├── 📁 prompts/                      # 💭 提示词模板
├── 📁 test/                         # 🧪 测试代码
├── 📁 utils/                        # 🛠️ 工具函数库
└── 📁 web/                          # 🌐 Web 管理后台
    ├── 📄 app.py                    # 🚀 Flask 应用入口 (使用工厂模式)
    ├── 📄 factory.py                # 🏭 Flask 应用工厂
    ├── 📁 blueprints/               # 🧩 功能蓝图 (Admin, API, Auth)
    ├── 📁 static/                   # 🎨 静态文件 (CSS, JS)
    └── 📁 templates/                # 📄 HTML 模板
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

### 🧠 4. LLM Agent 系统
- **统一工具注册**：通过 `MarketToolRegistry` 和 `DatabaseSuperToolRegistry` 集中管理工具，为 LLM 提供详细的工具定义、参数说明和数据库模式。
- **智能提示生成**：`get_prompt_text` 方法动态生成包含完整上下文的提示，引导 LLM 更准确地调用工具。
- **稳健的调用处理**：`ToolHandler` 能够智能解析和修复 LLM 返回的 JSON，支持单个或多个工具的并发异步调用。
- **结构化输出**：所有工具返回包含 `display` (用户友好) 和 `llm_feedback` (AI 友好) 的结构化字典，实现清晰的人机交互分离。
- **高度可扩展**：添加新工具只需在 `tools.py` 中实现并在 `tools_registry.py` 中注册，无需修改核心处理逻辑。

### 5. 💾 数据持久化
- **连接池管理**：SQLite 连接池，支持并发访问
- **事务处理**：数据一致性保证
- **用户数据**：个人配置、对话历史、使用统计
- **群组数据**：群组配置、消息记录、权限设置
- **备份恢复**：数据导出导入功能

### 🌐 6. Web 管理后台
- **工厂模式架构**：采用 `create_app` 工厂模式初始化 Flask 应用，实现更灵活的配置和扩展。
- **蓝图化模块**：功能按 `admin`, `api`, `auth` 等蓝图进行划分，使代码结构更清晰，易于维护。
- **前后端分离**：通过 `static` 目录管理静态资源 (CSS/JS)，为未来的前端框架集成打下基础。
- **核心功能**：提供用户管理、权限修改、数据统计、系统监控和在线配置等核心功能。
- **安全认证**：集成了登录验证和会话管理，确保后台操作的安全性。

### 7. ⚙️ 配置系统
- **分层配置**：默认配置、标准配置、本地配置
- **优先级机制**：本地配置 > 标准配置 > 默认配置
- **配置访问**：通过 `config_utils` 模块统一访问
- **路径管理**：集中管理文件路径配置
- **API 配置**：支持多种 LLM API 配置

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
1. 复制 `config/config.json` 为 `config/config_local.json`，填写 Telegram Bot Token、API Keys、管理员等信息
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
| 命令 | 描述          | 示例              |
|------|-------------|-----------------|
| `/char` | 查看当前角色和角色列表 | `/char`         |
| `/newchar [角色名]` | 创建自定义角色     | `/newchar 我的助手` |
| `/delchar` | 删除已有角色      | `/delchar`      |
| `/nick [昵称]` | 修改当前自己的昵称   | `/nick 脆脆`       |

#### 💬 对话管理
| 命令           | 描述          | 示例        |
|--------------|-------------|-----------|
| `/new`       | 开始新的对话会话    | `/new`    |
| `/save` | 保存当前对话并自动总结 | `/save`   |
| `/dialog`    | 加载历史对话      | `/dialog` |
| `/undo`      | 撤销上一条消息     | `/undo`   |
| `/regen`     | 重新生成AI回复    | `/regen`  |

#### ⚙️ 设置配置
| 命令 | 描述 | 示例 |
|------|------|------|
| `/setting` | 个人设置菜单 | `/setting` |
| `/api` | 切换LLM模型 | `/api` |
| `/preset` | 管理对话预设 | `/preset` |
| `/stream` | 切换流式输出模式 | `/stream` |

#### 📊 高级功能
| 命令              | 描述         | 示例                  |
|-----------------|------------|---------------------|
| `/c  [参数] [指令]` | 加密货币分析     | `/c  long 帮我分析一下大饼` |
| `/director`     | 导演模式（快速回复） | `/director`         |


**加密货币分析参数说明：**
- `long` - 多头分析倾向
- `short` - 空头分析倾向  
- 无参数 - 中性分析

### 👥 群组命令

#### 🛠️ 群组管理（需要管理员权限）
| 命令 | 描述 | 示例 |
|------|------|------|
| `/switch` | 切换群组角色 | `/switch` |
| `/rate [0-1]` | 设置回复概率 | `/rate 0.3` |
| `/kw` | 管理关键词触发 | `/kw` |
| `/e` | 启用群聊话题讨论 | `/e` |
| `/d` | 禁用群聊话题讨论 | `/d` |

#### 📊 群组功能
| 命令              | 描述        | 示例             |
|-----------------|-----------|----------------|
| `/cc [币种] [参数]` | 群聊加密货币分析  | `/cc btc long` |
| `/remake`       | 重置群聊对话上下文 | `/remake`      |
| `/fuck`         | 图片分析      | `/fuck`        |

### 🔐 管理员命令

| 命令 | 描述 | 示例 |
|------|------|------|
| `/addf [用户ID/all] [数量]` | 增加用户额度 | `/addf 123456 100` |
| `/sett [用户ID] [等级]` | 修改用户等级 | `/sett 123456 2` |
| `/q [查询]` | 数据库查询分析 | `/q 查看用户统计` |



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
# 1. 在 agent/tools.py 中定义新工具
#    确保工具是异步的 (async def) 并且返回一个包含 'display' 和 'llm_feedback' 的字典。

class MyCustomTools:
    @staticmethod
    async def my_awesome_tool(param1: str, param2: int) -> dict:
        """
        我的自定义工具的详细描述。
        Description: 工具功能的简短描述。
        Type: Query/Analysis/Update
        Parameters:
            - param1 (string): 参数1的描述。
            - param2 (integer): 参数2的描述。
        Return Value: 一个包含 'display' 和 'llm_feedback' 的字典。
        Invocation: {"tool_name": "my_awesome_tool", "parameters": {"param1": "hello", "param2": 123}}
        """
        # ... 工具逻辑 ...
        result_for_user = f"给用户看的结果: {param1}, {param2}"
        feedback_for_llm = f"Tool executed with {param1} and {param2}."
        return {"display": result_for_user, "llm_feedback": feedback_for_llm}

# 2. 在 agent/tools.py 的底部将工具函数添加到映射中
MY_CUSTOM_TOOLS = {
    "my_awesome_tool": MyCustomTools.my_awesome_tool,
}

# 3. 在 agent/tools_registry.py 中注册新工具
#    首先，将新的工具字典导入
from agent.tools import MY_CUSTOM_TOOLS

#    然后，创建一个新的注册表类 (如果需要) 或添加到现有注册表中
class MyCustomToolRegistry:
    TOOLS: Dict[str, Dict[str, Any]] = {
        "my_awesome_tool": {
            "description": "我的自定义工具的详细描述。",
            "type": "query",
            "parameters": {
                "param1": {"type": "string", "description": "参数1"},
                "param2": {"type": "integer", "description": "参数2"}
            },
            "output_format": "一个描述工具输出的字符串。",
            "example": {
                "tool_name": "my_awesome_tool",
                "parameters": {"param1": "example", "param2": 1}
            },
            "return_value": "工具成功执行后返回值的描述。"
        }
    }
    # ... get_tool 和 get_prompt_text 方法 ...

# 4. 最后，在 agent/tools_registry.py 的 ALL_TOOLS 字典中合并你的新工具
for tool_name, tool_func in MY_CUSTOM_TOOLS.items():
    if tool_name not in ALL_TOOLS:
        ALL_TOOLS[tool_name] = tool_func
```




### ⚙️ 配置系统

#### 1. 分层配置
```
config/
├── default_config.json  # 默认配置
├── config.json          # 标准配置
└── config_local.json    # 本地配置（敏感信息）
```

#### 2. 配置访问
```python
# 使用 config_utils 模块访问配置
from utils.config_utils import get_config, get_api_config

# 获取简单配置项
api_name = get_config("api.default_api")

# 获取API配置
api_key, base_url, model = get_api_config("gemini-2")
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
A: 在 `config/config_local.json` 中配置 API 密钥和端点，支持 OpenAI、Claude、Gemini 等

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

**Q: 如何启用内联查询功能？**
A: 在 BotFather 中为机器人启用内联模式，详见 `docs/inline_query_usage.md`

## 🚀 未来规划
- [ ] 🔊 **语音支持**：语音消息识别和合成
- [ ] 📊 **高级分析**：用户行为分析和个性化推荐
- [ ] 🎮 **游戏化功能**：积分系统、成就系统
- [ ] 🤝 **社区功能**：用户间的角色分享和交流
- [x] 💭 **对话记忆优化**：分层总结机制，减少token消耗
- [ ] ⏰ **时间感知**：对话中的实时时间感知
- [x] 👥 **群聊用户画像**：通过LLM分析构建用户画像
- [ ] 🔄 **Web实时CLI输出**：使用WebSocket实现CLI输出的实时流式传输

## 📞 支持与反馈

- 📧 **联系开发者**：[@Xi_cuicui](https://t.me/Xi_cuicui)

---

⭐ **如果这个项目对你有帮助，请给个 Star 支持一下！**

💖 **感谢所有贡献者和用户的支持！**
