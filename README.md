# Cyber Waifu Bot

一个基于 Telegram 的多角色 AI 聊天机器人，支持自定义角色、群组管理、关键词触发、加密货币行情分析等多种扩展功能，适合 RP 聊天、群聊娱乐与自动化管理。

测试版： https://t.me/waifucui_bot

---

## 目录结构

```
.
├── Dockerfile           # Docker 镜像构建配置
├── LICENSE              # 许可证
├── LLM_tools/           # LLM 工具调用模块
│   ├── __init__.py
│   ├── tools.py         # 工具定义
│   └── tools_registry.py# 工具注册
├── README.md            # 项目说明文档
├── bot_run.py           # 启动入口
├── bot_core/            # 机器人核心模块
│   ├── callback_handlers/  # 回调处理
│   ├── command_handlers/   # 命令处理
│   ├── message_handlers/   # 消息处理
│   └── public_functions/   # 公共功能
├── requirements.txt     # Python 依赖包列表
└── utils/               # 工具函数模块
    ├── LLM_utils.py     # OPenAI API 封装
    ├── db_utils.py      # 数据库操作
    ├── file_utils.py    # 文件处理
    ├── logging_utils.py # 日志处理
    ├── prompt_utils.py  # Prompt 处理
    └── text_utils.py    # 文本处理
```

## 核心功能

### 1. 消息处理系统
- 支持私聊和群聊消息处理
- 消息有效性检查与过期处理
- 关键词触发与自动回复
- 多角色对话管理
- 装饰器模式实现的消息预处理

### 2. 命令系统
- 丰富的私聊和群组命令
- 命令权限管理
- 动态命令菜单配置
- 基于类的命令处理架构

### 3. 角色管理
- 预设角色库
- 自定义角色创建与管理
- 角色切换功能
- 角色对话状态持久化

### 4. 扩展功能
- LLM 工具调用（支持自定义工具）
- 对话状态持久化
- 多模态支持（文本/图片）
- 完善的错误处理机制
- 详细的日志记录系统

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

## 命令手册

### 私聊命令
| 命令 | 描述 |
|------|------|
| /start | 打招呼 |
| /me | 查看个人信息 |
| /status | 查看当前配置状态 |
| /char | 选择角色 |
| /newchar | 创建私人角色 |
| /delchar | 删除私人角色 |
| /api | 选择大模型 API |
| /load | 加载保存的对话 |
| /preset | 选择 Prompt 预设 |
| /new | 新建对话 |
| /save | 保存当前对话 |
| /delete | 删除保存的对话 |
| /stream | 切换流式传输 |

### 群组命令
| 命令 | 描述 |
|------|------|
| /cremake | 重开对话 |
| /kw | 设置bot触发关键词 |
| /switch | 切换群组内的角色 |
| /rate | 设置触发频率 |

## 开发指南

### 架构设计
1. **核心模块**：bot_core 包含所有核心功能
   - callback_handlers: 处理回调查询
   - command_handlers: 处理命令
   - message_handlers: 处理消息
   - public_functions: 提供公共功能

2. **工具模块**：utils 提供各种实用功能
   - LLM_utils: 大语言模型 API 封装
   - db_utils: 数据库操作
   - file_utils: 文件处理
   - logging_utils: 日志处理
   - market_utils: 加密货币行情
   - prompt_utils: Prompt 处理
   - text_utils: 文本处理

3. **主程序**：bot_run.py 负责初始化和启动
   - 注册命令处理器
   - 注册消息处理器
   - 注册回调处理器
   - 全局错误处理

### 扩展开发
1. 添加新命令：在 bot_core/command_handlers/ 中实现新的命令类
2. 添加新消息处理器：在 bot_core/message_handlers/ 中实现
3. 添加新工具函数：在 utils/ 下创建新模块
4. 添加新角色：在 characters/ 目录下添加角色配置

### 错误处理
系统实现了多层次的错误处理机制：
1. Telegram API 相关错误
2. Bot 运行时错误
3. 配置错误
4. 数据库错误
5. 其他未捕获的异常

## 贡献规范
1. 使用 GitHub Flow 工作流
2. 提交前运行代码检查
3. 更新文档和测试用例

## 常见问题

### Q: 如何获取 Telegram Bot Token?
A: 通过 @BotFather 创建机器人获取

### Q: 如何调试机器人?
A: 查看 bot.log 文件获取详细日志

### Q: 如何处理群组中的图片消息?
A: 系统已支持图片处理，但需要配置支持多模态的 API

## 未来规划
- Web 管理后台
- 增强群管功能
- 多模态支持优化
- 国际化适配
- 更多 LLM API 支持

---

如有建议或需求，欢迎 issue 或 PR！
