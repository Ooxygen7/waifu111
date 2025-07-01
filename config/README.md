# 配置系统说明

## 概述

本项目使用分层配置系统，将硬编码的默认值移至专门的配置文件，并优化了模块间的依赖关系，减少循环导入问题。

## 配置文件结构

配置系统包含以下文件：

1. `default_config.json` - 包含所有默认配置值
2. `config.json` - 标准配置文件，可被版本控制
3. `config_local.json` - 本地配置文件，优先级高于标准配置，通常包含敏感信息（如API密钥）

## 配置加载顺序

配置加载遵循以下优先级（从低到高）：

1. 默认配置 (`default_config.json`)
2. 标准配置 (`config.json`)
3. 本地配置 (`config_local.json`)

这意味着本地配置会覆盖标准配置，标准配置会覆盖默认配置。

## 使用方法

### 在代码中访问配置

使用 `config_utils` 模块访问配置：

```python
from utils.config_utils import get_config

# 获取简单配置项
api_name = get_config("api.default_api")

# 获取带默认值的配置项
max_tokens = get_config("api.max_tokens", 8000)

# 获取文件路径
from utils.config_utils import get_path
prompt_path = get_path("prompt_path")
```

### 常用配置常量

一些常用的配置值已作为常量导出，可直接导入使用：

```python
from utils.config_utils import BOT_TOKEN, ADMIN_LIST, DEFAULT_API, DEFAULT_CHAR, DEFAULT_PRESET
```

### API配置

获取API配置的专用函数：

```python
from utils.config_utils import get_api_config

# 获取默认API的配置
api_key, base_url, model = get_api_config()

# 获取指定API的配置
api_key, base_url, model = get_api_config("gemini-2")
```

## 配置项说明

### API配置

```json
"api": {
  "default_api": "gemini-2",  // 默认使用的API
  "max_tokens": 8000,         // 最大token数
  "semaphore_limit": 5        // API并发请求限制
}
```

### 用户配置

```json
"user": {
  "default_char": "cuicuishark_public",  // 默认角色
  "default_preset": "Default_meeting",   // 默认预设
  "default_stream": "no",                // 默认是否开启流式传输
  "default_frequency": 200,              // 用户默认的每日免费使用次数
  "default_balance": 1.5                 // 用户默认的初始余额
}
```

### 对话配置

```json
"dialog": {
  "private_history_limit": 70,  // 私聊历史记录限制
  "group_history_limit": 10     // 群聊历史记录限制
}
```

### 缓存配置

```json
"cache": {
  "ttl": 3600  // 缓存过期时间（秒）
}
```

### 群组配置

```json
"group": {
  "default_rate": 0.05  // 默认群组回复率
}
```

### 签到配置

```json
"sign": {
  "default_frequency": 50,  // 签到默认增加的使用次数
  "max_frequency": 100      // 签到最大累积使用次数
}
```

### 数据库配置

```json
"database": {
  "default_path": "./data/data.db",  // 默认数据库路径
  "max_connections": 5               // 最大连接数
}
```

### 路径配置

```json
"paths": {
  "config_path": "./config/config.json",        // 标准配置文件路径
  "config_local": "./config/config_local.json", // 本地配置文件路径
  "characters_path": "./characters",            // 角色文件目录
  "prompt_path": "./prompts/prompts.json"       // 提示词文件路径
}
```

## 扩展配置

要添加新的配置项：

1. 在 `default_config.json` 中添加默认值
2. 在代码中使用 `get_config()` 函数获取配置值
3. 如需覆盖默认值，在 `config.json` 或 `config_local.json` 中添加相应配置