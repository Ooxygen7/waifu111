from flask import Blueprint, render_template, request, current_app
from web.factory import admin_required, format_datetime
from bot_core.public_functions.frequency_manager import get_dashboard_stats
from utils import db_utils as db

admin_bp = Blueprint("admin", __name__)

def format_tokens_m(value):
    """将数字格式化为以M为单位的字符串，如果小于1M则正常显示。"""
    if value is None:
        return "0"
    value = int(value)
    if value < 1_000_000:
        return f"{value:,}"
    else:
        return f"{value / 1_000_000:.2f}M"

@admin_bp.record_once
def on_load(state):
    """在蓝图注册时，将自定义过滤器添加到Jinja2环境中。"""
    state.app.jinja_env.filters['format_tokens_m'] = format_tokens_m

@admin_bp.route("/")
@admin_required
def index():
    """主页 - 显示统计信息"""
    time_range = request.args.get("time_range", "7d")
    stats = get_dashboard_stats(time_range)
    return render_template("index.html", stats=stats)


@admin_bp.route("/users")
@admin_required
def users():
    """用户管理页面"""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    search_term = request.args.get("search", "")
    sort_by = request.args.get("sort_by", "create_at")
    sort_order = request.args.get("sort_order", "desc")
    query = "SELECT * FROM users"
    params = []
    if search_term:
        query += " WHERE uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?"
        search_param = f"%{search_term}%"
        params.extend([search_param, search_param, search_param, search_param])
    if sort_by and sort_order:
        query += f" ORDER BY {sort_by} {sort_order}"
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    users_data = db.query_db(query, tuple(params))
    count_query = "SELECT COUNT(*) FROM users"
    count_params = []
    if search_term:
        count_query += " WHERE uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?"
        count_params.extend([search_param, search_param, search_param, search_param])
    total_result = db.query_db(count_query, tuple(count_params))
    total_users = total_result[0][0] if total_result else 0
    total_pages = (total_users + per_page - 1) // per_page
    users_list = []
    if users_data:
        columns = [
            "uid",
            "first_name",
            "last_name",
            "user_name",
            "create_at",
            "conversations",
            "dialog_turns",
            "update_at",
            "input_tokens",
            "output_tokens",
            "account_tier",
            "remain_frequency",
            "balance",
        ]
        for row in users_data:
            user_dict = {columns[i]: row[i] for i in range(len(columns))}
            users_list.append(user_dict)

    def next_sort_order(column):
        if column == sort_by:
            return "asc" if sort_order == "desc" else "desc"
        return "desc"

    return render_template(
        "users.html",
        users=users_list,
        page=page,
        total_pages=total_pages,
        format_datetime=format_datetime,
        search_term=search_term,
        sort_by=sort_by,
        sort_order=sort_order,
        next_sort_order=next_sort_order,
        per_page=per_page,
        total_users=total_users,
    )


@admin_bp.route("/conversations")
@admin_required
def conversations():
    """对话管理页面"""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    sort_by = request.args.get("sort_by", "update_at")
    sort_order = request.args.get("sort_order", "desc")
    per_page = 20
    offset = (page - 1) * per_page
    allowed_sort_fields = [
        "conv_id",
        "user_id",
        "character",
        "preset",
        "turns",
        "create_at",
        "update_at",
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = "update_at"
    order = "ASC" if sort_order.lower() == "asc" else "DESC"
    query = """
        SELECT c.id, c.conv_id, c.user_id, c.character, c.preset, c.summary,
               c.create_at, c.update_at, c.delete_mark, c.turns,
               u.first_name, u.last_name, u.user_name
        FROM conversations c
        LEFT JOIN users u ON c.user_id = u.uid
    """
    params = []
    if search:
        query += """ WHERE (u.user_name LIKE ? OR
                           u.first_name LIKE ? OR
                           u.last_name LIKE ? OR
                           CAST(c.user_id AS TEXT) LIKE ?)"""
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param, search_param])
    query += f" ORDER BY c.{sort_by} {order} LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    conversations_data = db.query_db(query, tuple(params))
    count_query = (
        "SELECT COUNT(*) FROM conversations c LEFT JOIN users u ON c.user_id = u.uid"
    )
    count_params = []
    if search:
        count_query += """ WHERE (u.user_name LIKE ? OR
                                 u.first_name LIKE ? OR
                                 u.last_name LIKE ? OR
                                 CAST(c.user_id AS TEXT) LIKE ?)"""
        search_param = f"%{search}%"
        count_params.extend([search_param, search_param, search_param, search_param])
    total_result = db.query_db(count_query, tuple(count_params))
    total_conversations = total_result[0][0] if total_result else 0
    total_pages = (total_conversations + per_page - 1) // per_page
    conversations_list = []
    if conversations_data:
        columns = [
            "id",
            "conv_id",
            "user_id",
            "character",
            "preset",
            "summary",
            "create_at",
            "update_at",
            "delete_mark",
            "turns",
            "first_name",
            "last_name",
            "user_name",
        ]
        for row in conversations_data:
            conv_dict = {columns[i]: row[i] for i in range(len(columns))}
            conversations_list.append(conv_dict)

    def next_sort_order(column):
        if column == sort_by:
            return "asc" if sort_order == "desc" else "desc"
        return "desc"

    return render_template(
        "conversations.html",
        conversations=conversations_list,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        total_conversations=total_conversations,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        next_sort_order=next_sort_order,
        format_datetime=format_datetime,
    )


@admin_bp.route("/dialogs/<string:conv_id>")
@admin_required
def dialogs(conv_id):
    """查看对话详情"""
    conversation_data = db.query_db(
        "SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)
    )
    if not conversation_data:
        return "对话不存在", 404
    conv_columns = [
        "id",
        "conv_id",
        "user_id",
        "character",
        "preset",
        "summary",
        "create_at",
        "update_at",
        "delete_mark",
        "turns",
    ]
    conversation = {
        conv_columns[i]: conversation_data[0][i] for i in range(len(conv_columns))
    }
    search_keyword = request.args.get("search", "").strip()
    if search_keyword:
        dialogs_data = db.query_db(
            """SELECT * FROM dialogs
               WHERE conv_id = ? AND (
                   raw_content LIKE ? OR
                   processed_content LIKE ?
               )
               ORDER BY turn_order ASC""",
            (conv_id, f"%{search_keyword}%", f"%{search_keyword}%"),
        )
    else:
        dialogs_data = db.query_db(
            "SELECT * FROM dialogs WHERE conv_id = ? ORDER BY turn_order ASC",
            (conv_id,),
        )
    dialogs_list = []
    if dialogs_data:
        dialog_columns = [
            "id",
            "conv_id",
            "role",
            "raw_content",
            "turn_order",
            "created_at",
            "processed_content",
            "msg_id",
        ]
        for row in dialogs_data:
            dialog_dict = {
                dialog_columns[i]: row[i] for i in range(len(dialog_columns))
            }
            dialogs_list.append(dialog_dict)
    return render_template(
        "dialogs.html",
        conversation=conversation,
        dialogs=dialogs_list,
        format_datetime=format_datetime,
        search_keyword=search_keyword,
    )


@admin_bp.route("/groups")
@admin_required
def groups():
    """群组管理页面"""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    search_term = request.args.get("search", "")
    sort_by = request.args.get("sort_by", "update_time")
    sort_order = request.args.get("sort_order", "desc")
    allowed_sort_fields = [
        "group_id",
        "group_name",
        "call_count",
        "api",
        "char",
        "preset",
        "rate",
        "input_token",
        "output_token",
        "active",
        "update_time",
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = "update_time"
    sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"
    query = "SELECT * FROM groups"
    params = []
    if search_term:
        query += " WHERE group_id LIKE ? OR group_name LIKE ? OR members_list LIKE ? OR api LIKE ? OR char LIKE ? OR preset LIKE ?"
        search_param = f"%{search_term}%"
        params.extend(
            [
                search_param,
                search_param,
                search_param,
                search_param,
                search_param,
                search_param,
            ]
        )
    query += f" ORDER BY {sort_by} {sort_order}"
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    groups_data = db.query_db(query, tuple(params))
    count_query = "SELECT COUNT(*) FROM groups"
    count_params = []
    if search_term:
        count_query += " WHERE group_id LIKE ? OR group_name LIKE ? OR members_list LIKE ? OR api LIKE ? OR char LIKE ? OR preset LIKE ?"
        count_params.extend(
            [
                search_param,
                search_param,
                search_param,
                search_param,
                search_param,
                search_param,
            ]
        )
    total_result = db.query_db(count_query, tuple(count_params))
    total_groups = total_result[0][0] if total_result else 0
    total_pages = (total_groups + per_page - 1) // per_page
    groups_list = []
    if groups_data:
        columns = [
            "group_id",
            "members_list",
            "call_count",
            "keywords",
            "active",
            "api",
            "char",
            "preset",
            "input_token",
            "group_name",
            "update_time",
            "rate",
            "output_token",
            "disabled_topics",
        ]
        for row in groups_data:
            group_dict = {columns[i]: row[i] for i in range(len(columns))}
            groups_list.append(group_dict)

    def next_sort_order(column):
        if column == sort_by:
            return "asc" if sort_order == "DESC" else "desc"
        return "desc"

    return render_template(
        "groups.html",
        groups=groups_list,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_groups=total_groups,
        format_datetime=format_datetime,
        search_term=search_term,
        sort_by=sort_by,
        sort_order=sort_order,
        next_sort_order=next_sort_order,
    )


@admin_bp.route("/group_dialogs/<group_id>")
@admin_required
def group_dialogs(group_id):
    try:
        group_id = int(group_id)
    except ValueError:
        return "Invalid group ID", 400
    """查看群组对话"""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    per_page = 50
    offset = (page - 1) * per_page
    group_data = db.query_db("SELECT * FROM groups WHERE group_id = ?", (group_id,))
    if not group_data:
        return "群组不存在", 404
    group_columns = [
        "group_id",
        "members_list",
        "call_count",
        "keywords",
        "active",
        "api",
        "char",
        "preset",
        "input_token",
        "group_name",
        "update_time",
        "rate",
        "output_token",
        "disabled_topics",
    ]
    group = {group_columns[i]: group_data[0][i] for i in range(len(group_columns))}
    if search:
        # When searching, we need to find the original page of each message.
        # We use a subquery with ROW_NUMBER() to get the original position.
        query = """
            WITH ranked_dialogs AS (
                SELECT *,
                       ROW_NUMBER() OVER (ORDER BY create_at DESC) as rn
                FROM group_dialogs
                WHERE group_id = ?
            )
            SELECT *,
                   ( (rn - 1) / ? ) + 1 as original_page
            FROM ranked_dialogs
            WHERE msg_text LIKE ?
            ORDER BY create_at DESC
            LIMIT ? OFFSET ?
        """
        dialogs_data = db.query_db(
            query,
            (group_id, per_page, f"%{search}%", per_page, offset)
        )
        total_result = db.query_db(
            "SELECT COUNT(*) FROM group_dialogs WHERE group_id = ? AND msg_text LIKE ?",
            (group_id, f"%{search}%"),
        )
    else:
        dialogs_data = db.query_db(
            "SELECT * FROM group_dialogs WHERE group_id = ? ORDER BY create_at DESC LIMIT ? OFFSET ?",
            (group_id, per_page, offset),
        )
        total_result = db.query_db(
            "SELECT COUNT(*) FROM group_dialogs WHERE group_id = ?", (group_id,)
        )
    total_dialogs = total_result[0][0] if total_result else 0
    total_pages = (total_dialogs + per_page - 1) // per_page
    dialogs_list = []
    if dialogs_data:
        if search:
            dialog_columns = [
                "group_id", "msg_user", "trigger_type", "msg_text",
                "msg_user_name", "msg_id", "raw_response",
                "processed_response", "delete_mark", "group_name",
                "create_at", "rn", "original_page"
            ]
        else:
            dialog_columns = [
                "group_id", "msg_user", "trigger_type", "msg_text",
                "msg_user_name", "msg_id", "raw_response",
                "processed_response", "delete_mark", "group_name",
                "create_at"
            ]
        for row in dialogs_data:
            dialog_dict = {
                dialog_columns[i]: row[i] for i in range(len(dialog_columns))
            }
            dialogs_list.append(dialog_dict)
    return render_template(
        "group_dialogs.html",
        group=group,
        dialogs=dialogs_list,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_dialogs=total_dialogs,
        search=search if search else None,
        format_datetime=format_datetime,
    )


@admin_bp.route("/search")
@admin_required
def search():
    """全局搜索页面"""
    query = request.args.get("q", "")
    if not query:
        return render_template(
            "search.html", results={}, query="", format_datetime=format_datetime
        )
    results = {"dialogs": [], "users": [], "groups": [], "conversations": []}
    dialogs_data = db.query_db(
        "SELECT d.*, c.character, c.user_id, u.user_name, u.first_name, u.last_name FROM dialogs d LEFT JOIN conversations c ON d.conv_id = c.conv_id LEFT JOIN users u ON c.user_id = u.uid WHERE d.raw_content LIKE ? OR d.processed_content LIKE ? ORDER BY d.created_at DESC",
        (f"%{query}%", f"%{query}%"),
    )
    if dialogs_data:
        dialog_columns = [
            "id",
            "conv_id",
            "role",
            "raw_content",
            "turn_order",
            "created_at",
            "processed_content",
            "msg_id",
            "character",
            "user_id",
            "user_name",
            "first_name",
            "last_name",
        ]
        for row in dialogs_data:
            dialog_dict = {
                dialog_columns[i]: row[i] for i in range(len(dialog_columns))
            }
            first_name = dialog_dict.get("first_name", "") or ""
            last_name = dialog_dict.get("last_name", "") or ""
            dialog_dict["user_name"] = (
                f"{first_name} {last_name}".strip()
                or dialog_dict.get("user_name", "未设置")
            )
            dialog_dict["type"] = "private"
            results["dialogs"].append(dialog_dict)
    group_dialogs_data = db.query_db(
        "SELECT gd.group_id, gd.msg_user, gd.trigger_type, gd.msg_text, gd.msg_user_name, gd.msg_id, gd.raw_response, gd.processed_response, gd.delete_mark, gd.group_name, gd.create_at, g.group_name as groups_group_name, ROW_NUMBER() OVER (ORDER BY gd.create_at DESC) as id FROM group_dialogs gd LEFT JOIN groups g ON gd.group_id = g.group_id WHERE gd.msg_text LIKE ? OR gd.raw_response LIKE ? OR gd.processed_response LIKE ? ORDER BY gd.create_at DESC",
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    )
    if group_dialogs_data:
        group_dialog_columns = [
            "group_id",
            "msg_user",
            "trigger_type",
            "msg_text",
            "msg_user_name",
            "msg_id",
            "raw_response",
            "processed_response",
            "delete_mark",
            "group_name",
            "create_at",
            "groups_group_name",
            "id",
        ]
        for row in group_dialogs_data:
            group_dialog_dict = {
                group_dialog_columns[i]: row[i]
                for i in range(len(group_dialog_columns))
            }
            group_dialog_dict["group_name"] = (
                group_dialog_dict.get("groups_group_name")
                or group_dialog_dict.get("group_name")
                or "未知群组"
            )
            group_dialog_dict["type"] = "group"
            results["dialogs"].append(group_dialog_dict)
    users_data = db.query_db(
        "SELECT u.uid, u.first_name, u.last_name, u.user_name, u.create_at, u.conversations as conversations_orig, u.dialog_turns as dialog_turns_orig, u.update_at, u.input_tokens, u.output_tokens, u.account_tier, u.remain_frequency, u.balance, COUNT(DISTINCT c.conv_id) as conversations, SUM(CASE WHEN d.id IS NOT NULL THEN 1 ELSE 0 END) as dialog_turns FROM users u LEFT JOIN conversations c ON u.uid = c.user_id LEFT JOIN dialogs d ON c.conv_id = d.conv_id WHERE u.user_name LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ? OR CAST(u.uid AS TEXT) LIKE ? GROUP BY u.uid ORDER BY u.create_at DESC",
        (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"),
    )
    if users_data:
        user_columns = [
            "uid",
            "first_name",
            "last_name",
            "user_name",
            "create_at",
            "conversations_orig",
            "dialog_turns_orig",
            "update_at",
            "input_tokens",
            "output_tokens",
            "account_tier",
            "remain_frequency",
            "balance",
            "conversations",
            "dialog_turns",
        ]
        for row in users_data:
            user_dict = {user_columns[i]: row[i] for i in range(len(user_columns))}
            results["users"].append(user_dict)
    groups_data = db.query_db(
        "SELECT g.group_id, g.group_name, g.char, g.call_count, g.active, g.update_time, COUNT(DISTINCT gd.msg_id) as dialog_count FROM groups g LEFT JOIN group_dialogs gd ON g.group_id = gd.group_id WHERE g.group_name LIKE ? OR CAST(g.group_id AS TEXT) LIKE ? GROUP BY g.group_id ORDER BY g.update_time DESC",
        (f"%{query}%", f"%{query}%"),
    )
    if groups_data:
        group_columns = [
            "group_id",
            "group_name",
            "char",
            "call_count",
            "active",
            "update_time",
            "dialog_count",
        ]
        for row in groups_data:
            group_dict = {group_columns[i]: row[i] for i in range(len(group_columns))}
            results["groups"].append(group_dict)
    conversations_data = db.query_db(
        "SELECT c.conv_id, c.user_id, c.character, c.preset, c.summary, c.create_at, c.update_at, u.user_name, u.first_name, u.last_name, COUNT(d.id) as turns FROM conversations c LEFT JOIN users u ON c.user_id = u.uid LEFT JOIN dialogs d ON c.conv_id = d.conv_id WHERE c.character LIKE ? OR c.preset LIKE ? OR c.summary LIKE ? OR u.user_name LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ? OR CAST(c.user_id AS TEXT) LIKE ? GROUP BY c.conv_id ORDER BY c.update_at DESC",
        (
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
        ),
    )
    if conversations_data:
        conversation_columns = [
            "conv_id",
            "user_id",
            "character",
            "preset",
            "summary",
            "create_at",
            "update_at",
            "user_name",
            "first_name",
            "last_name",
            "turns",
        ]
        for row in conversations_data:
            conv_dict = {
                conversation_columns[i]: row[i]
                for i in range(len(conversation_columns))
            }
            results["conversations"].append(conv_dict)
    return render_template(
        "search.html", results=results, query=query, format_datetime=format_datetime
    )


@admin_bp.route("/config")
@admin_required
def config_management():
    """配置文件管理页面"""
    return render_template("config.html")