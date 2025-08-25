create table conversations
(
    id          INTEGER not null
        constraint conversations_pk
            primary key autoincrement,
    conv_id     ANY     not null,
    user_id     ANY     not null,
    character   ANY     not null,
    preset      ANY     not null,
    summary     ANY,
    create_at   ANY,
    update_at   ANY,
    delete_mark ANY,
    turns       integer
);

create table dialogs
(
    id                integer not null
        primary key autoincrement,
    conv_id           ANY     not null,
    role              ANY     not null,
    raw_content       ANY     not null,
    turn_order        ANY     not null,
    created_at        ANY     not null,
    processed_content ANY,
    msg_id            integer
);

create table group_dialogs
(
    group_id           integer,
    msg_user           integer,
    trigger_type       TEXT,
    msg_text           TEXT,
    msg_user_name      TEXT,
    msg_id             integer,
    raw_response       TEXT,
    processed_response TEXT,
    delete_mark        TEXT,
    group_name         TEXT,
    create_at          ANY
);

create table group_user_conversations
(
    user_id     integer,
    group_id    integer,
    user_name   TEXT,
    conv_id     integer,
    delete_mark integer,
    create_at   TEXT,
    update_at   TEXT,
    turns       INTEGER,
    group_name  ANY
);

create table group_user_dialogs
(
    conv_id           ANY,
    role              ANY,
    raw_content       ANY,
    turn_order        ANY,
    created_at        ANY,
    processed_content TEXT,
    id                INTEGER
        constraint id
            primary key
);

create table groups
(
    group_id        integer,
    members_list    ANY,
    call_count      integer,
    keywords        ANY,
    active          INT,
    api             TEXT,
    char            TEXT,
    preset          TEXT,
    input_token     integer,
    group_name      TEXT,
    update_time     ANY,
    rate            REAL,
    output_token    integer,
    disabled_topics TEXT
);



create table user_config
(
    uid     INT UNIQUE,
    char    TEXT,
    api     TEXT,
    preset  TEXT,
    conv_id INT,
    stream  TEXT,
    nick    TEXT
);

create table user_sign
(
    user_id    integer,
    last_sign  ANY,
    sign_count integer,
    frequency  integer
);

create table users
(
    uid              integer,
    first_name       TEXT,
    last_name        TEXT,
    user_name        TEXT,
    create_at        ANY,
    conversations    integer,
    dialog_turns     integer,
    update_at        ANY,
    input_tokens     integer,
    output_tokens    integer,
    account_tier     integer,
    remain_frequency integer,
    balance          REAL
);
create table dialog_summary
(
    conv_id      integer not null,
    summary_area ANY,
    content      TEXT
);



create table user_profiles
(
    user_id          integer not null,
    group_id         integer not null,
    profile_json     TEXT,
    last_updated     ANY,
    primary key (user_id, group_id)
);

-- 模拟盘交易相关表
-- 用户模拟盘账户表
create table trading_accounts
(
    user_id          integer not null,
    group_id         integer not null,
    balance          REAL default 1000.0,  -- USDT余额
    total_pnl        REAL default 0.0,     -- 总盈亏
    created_at       TEXT,
    updated_at       TEXT,
    primary key (user_id, group_id)
);

-- 用户仓位表
create table trading_positions
(
    id               integer not null primary key autoincrement,
    user_id          integer not null,
    group_id         integer not null,
    symbol           TEXT not null,        -- 交易对，如BTC/USDT
    side             TEXT not null,        -- 'long' 或 'short'
    size             REAL not null,        -- 仓位大小(USDT价值)
    entry_price      REAL not null,        -- 开仓价格
    current_price    REAL,                 -- 当前价格
    pnl              REAL default 0.0,     -- 未实现盈亏
    liquidation_price REAL,                -- 强平价格
    created_at       TEXT not null,
    updated_at       TEXT
);

-- 救济金记录表
create table begging_records
(
    user_id          integer not null,
    group_id         integer not null,
    last_begging     TEXT,                 -- 最后一次领取救济金时间
    begging_count    integer default 0,    -- 总领取次数
    primary key (user_id, group_id)
);

-- 交易历史记录表
create table trading_history
(
    id               integer not null primary key autoincrement,
    user_id          integer not null,
    group_id         integer not null,
    symbol           TEXT not null,
    side             TEXT not null,        -- 'long' 或 'short'
    action           TEXT not null,        -- 'open', 'close', 'liquidated'
    size             REAL not null,
    price            REAL not null,
    pnl              REAL default 0.0,     -- 实现盈亏(平仓时)
    created_at       TEXT not null
);

-- 价格缓存表(用于存储实时价格数据)
create table price_cache
(
    symbol           TEXT not null primary key,
    price            REAL not null,
    updated_at       TEXT not null
);

-- 贷款记录表
create table loans
(
    id               integer not null primary key autoincrement,
    user_id          integer not null,
    group_id         integer not null,
    principal        REAL not null,        -- 本金
    remaining_debt   REAL not null,        -- 剩余欠款(本金+利息)
    interest_rate    REAL default 0.002,   -- 每6小时利率(0.2%)
    initial_fee      REAL default 0.1,     -- 初始手续费(10%)
    loan_time        TEXT not null,        -- 贷款时间
    last_interest_time TEXT not null,      -- 最后一次计息时间
    status           TEXT default 'active', -- 'active', 'paid_off'
    created_at       TEXT not null,
    updated_at       TEXT
);

-- 还款记录表
create table loan_repayments
(
    id               integer not null primary key autoincrement,
    loan_id          integer not null,
    user_id          integer not null,
    group_id         integer not null,
    amount           REAL not null,        -- 还款金额
    repayment_time   TEXT not null,        -- 还款时间
    remaining_after  REAL not null,        -- 还款后剩余欠款
    created_at       TEXT not null,
    foreign key (loan_id) references loans(id)
);
