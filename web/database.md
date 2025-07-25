CREATE TABLE "conversations"
(
    id          INTEGER not null
        constraint conversations_pk
            primary key autoincrement,
    conv_id     TEXT     not null, -- 对话ID
    user_id     INTEGER     not null,   -- 用户ID
    character   TEXT     not null,   -- 角色
    preset      TEXT     not null,   -- 预设
    summary     TEXT,   -- 摘要
    create_at   TEXT,   -- 创建时间
    update_at   TEXT,   -- 更新时间
    delete_mark INTEGER,   -- 删除标记
    turns       integer -- 对话轮数
);

CREATE TABLE "dialogs"
(
    id                integer not null
        primary key autoincrement,
    conv_id           TEXT     not null, -- 对话ID
    role              TEXT     not null,   -- 身份(assistant/user)
    raw_content       TEXT     not null,   -- 原始文本内容
    turn_order        INTEGER     not null,   -- 对话轮数
    created_at        TEXT     not null,   -- 创建时间
    processed_content TEXT,   -- 处理后的内容
    msg_id            integer -- telegram消息ID
);

CREATE TABLE group_dialogs
(
    group_id           integer, -- 群组ID
    msg_user           integer, -- 消息用户ID
    trigger_type       TEXT, -- 触发类型
    msg_text           TEXT, -- 消息文本内容
    msg_user_name      TEXT, -- 消息用户名称
    msg_id             integer, -- telegram消息ID
    raw_response       TEXT, -- 原始响应内容
    processed_response TEXT, -- 处理后的响应内容
    delete_mark        TEXT, -- 删除标记
    group_name         TEXT, -- 群组名称
    create_at          TEXT -- 创建时间
);

CREATE TABLE group_user_conversations
(
    user_id     integer, -- 用户ID
    group_id    integer, -- 群组ID
    user_name   TEXT, -- 用户名称
    conv_id     TEXT, -- 对话ID
    delete_mark integer, -- 删除标记
    create_at   TEXT, -- 创建时间
    update_at   TEXT, -- 更新时间
    turns       INTEGER, -- 对话轮数
    group_name  TEXT -- 群组名称
);

CREATE TABLE "group_user_dialogs"
(
    id                INTEGER primary key, -- 主键ID
    conv_id           TEXT, -- 对话ID
    role              TEXT, -- 身份(assistant/user)
    raw_content       TEXT, -- 原始文本内容
    turn_order        INTEGER, -- 对话轮数
    created_at        TEXT, -- 创建时间
    processed_content TEXT -- 处理后的内容
);

CREATE TABLE groups (
    group_id        integer, -- 群组ID
    members_list    TEXT, -- 管理列表
    call_count      integer, -- llm调用次数
    keywords        TEXT, -- 触发回复关键词
    active          INT, -- 活跃状态
    api             TEXT, -- API配置
    char            TEXT, -- 角色配置
    preset          TEXT, -- 预设
    input_token     integer, -- 输入token数量
    group_name      TEXT, -- 群组名称
    update_time     TEXT, -- 更新时间
    rate            REAL, -- 触发几率
    output_token    integer, -- 输出令牌数量
    disabled_topics TEXT, -- 被禁用话题
);

CREATE TABLE "user_config"
(
    uid     INT, -- 用户ID
    char    TEXT, -- 角色配置
    api     TEXT, -- API配置
    preset  TEXT, -- 预设
    conv_id TEXT, -- 会话ID
    stream  TEXT, -- 是否流式传输
    nick    text -- 昵称
);

CREATE TABLE user_sign
(
    user_id    integer, -- 用户ID
    last_sign  TEXT, -- 上次签到时间
    sign_count integer, -- 签到次数
    frequency  integer -- 临时额度
);

CREATE TABLE users
(
    uid              integer, -- 用户ID
    first_name       TEXT, -- 名
    last_name        TEXT, -- 姓
    user_name        TEXT, -- 用户名
    create_at        TEXT, -- 创建时间
    conversations    integer, -- 对话数量
    dialog_turns     integer, -- 总对话轮数
    update_at        TEXT, -- 更新时间
    input_tokens     integer, -- 输入token数量
    output_tokens    integer, -- 输出token数量
    account_tier     integer, -- 账号等级
    remain_frequency integer, -- 剩余额度
    balance          REAL -- 余额
);
