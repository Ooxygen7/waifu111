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
    uid     INT,
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
