# 内联查询处理器模块设计文档

## 概述

内联查询处理器模块为 CyberWaifu Telegram Bot 提供内联查询功能，允许用户通过 `@botname query` 的方式快速访问机器人的核心功能。该模块采用与现有命令处理器和回调处理器相同的架构模式，提供统一的基类系统和动态加载机制。

## 架构

### 核心架构原则

1. **统一架构模式**：遵循现有的 `BaseCommand` 和 `BaseCallback` 架构模式
2. **动态加载机制**：支持运行时动态发现和注册内联查询处理器
3. **元数据驱动**：通过 `InlineMeta` 类定义处理器的行为和属性
4. **模块化设计**：每个内联查询功能作为独立的处理器类实现

### 系统集成

内联查询处理器将集成到现有的 `bot_run.py` 系统中，与命令处理器和回调处理器并行工作：

```
Application
├── CommandHandlers (现有)
├── CallbackHandlers (现有)
└── InlineQueryHandlers (新增)
```

## 组件和接口

### 1. 基础架构组件

#### InlineMeta 类
```python
class InlineMeta:
    def __init__(self,
                 name: str,
                 query_type: str,  # 查询类型标识符
                 trigger: str = '',  # 触发关键词
                 description: str = '',  # 功能描述
                 enabled: bool = True,  # 是否启用
                 cache_time: int = 300):  # 缓存时间(秒)
```

**设计决策**：
- `query_type` 用于分类不同类型的内联查询（如 'char', 'preset', 'help'）
- `trigger` 支持空字符串，用于处理无关键词的通用查询
- `cache_time` 允许每个处理器自定义缓存策略

#### BaseInlineQuery 抽象基类
```python
class BaseInlineQuery(ABC):
    meta: InlineMeta
    
    def __init__(self):
        if not hasattr(self, 'meta'):
            raise NotImplementedError('InlineQuery must define meta attribute')
    
    @abstractmethod
    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> List[InlineQueryResult]:
        pass
```

**设计决策**：
- 返回 `List[InlineQueryResult]` 而非直接调用 `answer_inline_query`，便于测试和复用
- 遵循现有基类的初始化检查模式

### 2. 内联查询管理器

#### InlineQueryHandlers 类
```python
class InlineQueryHandlers:
    @staticmethod
    def get_inline_handlers(module_names: List[str]) -> List[BaseInlineQuery]:
        # 动态扫描和加载内联查询处理器
    
    @staticmethod
    async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 统一的内联查询分发处理器
```

**设计决策**：
- 采用与 `CommandHandlers` 相同的静态方法模式
- 提供统一的查询分发机制，根据查询内容路由到对应处理器

### 3. 具体处理器实现

#### CharacterInlineQuery - 角色查询处理器
```python
class CharacterInlineQuery(BaseInlineQuery):
    meta = InlineMeta(
        name='character_query',
        query_type='char',
        trigger='char',
        description='查看可用角色列表',
        enabled=True,
        cache_time=600  # 角色列表变化较少，缓存时间较长
    )
```

**功能特性**：
- 支持模糊搜索角色名称
- 显示角色基本信息和描述
- 提供角色预览而非直接切换

#### PresetInlineQuery - 预设查询处理器
```python
class PresetInlineQuery(BaseInlineQuery):
    meta = InlineMeta(
        name='preset_query',
        query_type='preset',
        trigger='preset',
        description='查看可用预设列表',
        enabled=True,
        cache_time=300
    )
```

#### HelpInlineQuery - 帮助查询处理器
```python
class HelpInlineQuery(BaseInlineQuery):
    meta = InlineMeta(
        name='help_query',
        query_type='help',
        trigger='help',
        description='获取使用帮助',
        enabled=True,
        cache_time=3600  # 帮助信息变化很少
    )
```

#### DefaultInlineQuery - 默认查询处理器
```python
class DefaultInlineQuery(BaseInlineQuery):
    meta = InlineMeta(
        name='default_query',
        query_type='default',
        trigger='',  # 空触发器，处理无匹配的查询
        description='默认查询处理',
        enabled=True,
        cache_time=60
    )
```

**设计决策**：
- 默认处理器使用空触发器，作为兜底机制
- 提供基本的使用提示和可用查询类型说明

## 数据模型

### 查询结果数据结构

```python
@dataclass
class InlineResultData:
    id: str
    title: str
    description: str
    thumb_url: Optional[str] = None
    content: str = ""
    parse_mode: Optional[str] = None
```

**设计决策**：
- 使用数据类简化结果构造
- 支持可选的缩略图和格式化内容
- 统一的结果ID生成策略

### 查询路由逻辑

```python
def parse_inline_query(query: str) -> Tuple[str, str]:
    """
    解析内联查询字符串
    返回: (query_type, search_term)
    """
    parts = query.strip().split(' ', 1)
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]
```

## 错误处理

### 错误处理策略

1. **处理器加载错误**：记录日志但不中断系统启动
2. **查询处理错误**：返回错误提示结果而非抛出异常
3. **数据访问错误**：提供降级的默认响应

### 错误响应格式

```python
def create_error_result(error_msg: str) -> List[InlineQueryResult]:
    return [
        InlineQueryResultArticle(
            id="error",
            title="查询出错",
            description=error_msg,
            input_message_content=InputTextMessageContent(
                message_text=f"查询失败：{error_msg}"
            )
        )
    ]
```

## 测试策略

### 单元测试

1. **基类测试**：验证元数据验证和抽象方法强制实现
2. **处理器测试**：测试每个具体处理器的查询逻辑
3. **路由测试**：验证查询分发的正确性

### 集成测试

1. **端到端测试**：模拟完整的内联查询流程
2. **数据库集成**：测试与现有数据库的交互
3. **缓存测试**：验证缓存机制的有效性

### 测试数据

```python
# 测试用例数据
TEST_CHARACTERS = [
    {"name": "cuicuishark_public", "display": "脆脆鲨"},
    {"name": "test_char_123", "display": "测试角色"}
]

TEST_PRESETS = [
    {"name": "Default_meeting", "display": "一般模式"},
    {"name": "NSFW_plus", "display": "烧鸡模式"}
]
```

## 实现细节

### 文件结构

```
bot_core/
└── inline_handlers/
    ├── __init__.py
    ├── base.py              # 基类定义
    ├── inline.py            # 管理器和分发逻辑
    ├── character.py         # 角色查询处理器
    ├── preset.py           # 预设查询处理器
    ├── help.py             # 帮助查询处理器
    └── default.py          # 默认查询处理器
```

### 与现有系统的集成点

1. **bot_run.py 修改**：
   - 在 `setup_handlers()` 中添加内联查询处理器注册
   - 添加 `InlineQueryHandler` 到应用程序

2. **数据访问**：
   - 复用现有的 `file_utils` 加载角色数据
   - 复用现有的 `prompts.json` 获取预设信息
   - 使用现有的数据库工具进行用户权限检查

### 性能考虑

1. **缓存策略**：
   - 角色列表缓存10分钟（变化较少）
   - 预设列表缓存5分钟
   - 帮助信息缓存1小时

2. **查询优化**：
   - 限制返回结果数量（最多50个）
   - 实现增量搜索以减少计算量
   - 使用异步I/O避免阻塞

### 安全考虑

1. **权限控制**：
   - 检查用户是否有权限查看特定角色
   - 过滤私有或受限制的内容

2. **输入验证**：
   - 限制查询字符串长度
   - 过滤特殊字符防止注入攻击

3. **速率限制**：
   - 利用Telegram内置的内联查询频率限制
   - 记录异常查询模式

## 扩展性设计

### 插件化支持

设计支持未来添加新的内联查询类型：

```python
# 未来可能的扩展
class ConversationInlineQuery(BaseInlineQuery):
    meta = InlineMeta(
        name='conversation_query',
        query_type='conv',
        trigger='conv',
        description='搜索历史对话'
    )
```

### 配置化支持

支持通过配置文件控制内联查询行为：

```json
{
  "inline_queries": {
    "enabled": true,
    "cache_time_default": 300,
    "max_results": 50,
    "handlers": {
      "character": {"enabled": true, "cache_time": 600},
      "preset": {"enabled": true, "cache_time": 300},
      "help": {"enabled": true, "cache_time": 3600}
    }
  }
}
```

这种设计确保了内联查询处理器模块与现有系统的无缝集成，同时提供了足够的灵活性和扩展性来满足未来的需求。