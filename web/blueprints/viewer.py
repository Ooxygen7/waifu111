from flask import Blueprint, render_template, request, flash, redirect, url_for
from web.factory import viewer_required, get_admin_ids, format_datetime
from utils import db_utils as db
from datetime import datetime

viewer_bp = Blueprint("viewer", __name__, url_prefix="/viewer")


@viewer_bp.route("/")
@viewer_required
def viewer_index():
    """浏览者首页 - 显示基础统计信息（过滤管理员数据）"""
    admin_ids = get_admin_ids()
    admin_ids_str = ",".join(map(str, admin_ids))
    stats = {}
    stats["total_users"] = (
        db.query_db(f"SELECT COUNT(*) FROM users WHERE uid NOT IN ({admin_ids_str})")[
            0
        ][0]
        if db.query_db(f"SELECT COUNT(*) FROM users WHERE uid NOT IN ({admin_ids_str})")
        else 0
    )
    stats["total_conversations"] = (
        db.query_db(
            f"SELECT COUNT(*) FROM conversations WHERE user_id NOT IN ({admin_ids_str})"
        )[0][0]
        if db.query_db(
            f"SELECT COUNT(*) FROM conversations WHERE user_id NOT IN ({admin_ids_str})"
        )
        else 0
    )
    stats["total_dialogs"] = (
        db.query_db(
            f"SELECT COUNT(*) FROM dialogs d JOIN conversations c ON d.conv_id = c.conv_id WHERE c.user_id NOT IN ({admin_ids_str})"
        )[0][0]
        if db.query_db(
            f"SELECT COUNT(*) FROM dialogs d JOIN conversations c ON d.conv_id = c.conv_id WHERE c.user_id NOT IN ({admin_ids_str})"
        )
        else 0
    )
    today = datetime.now().strftime("%Y-%m-%d")
    today_conversations = db.query_db(
        f"SELECT COUNT(*) FROM conversations WHERE date(create_at) = ? AND user_id NOT IN ({admin_ids_str})",
        (today,),
    )
    stats["today_conversations"] = (
        today_conversations[0][0] if today_conversations else 0
    )
    today_dialogs = db.query_db(
        f"SELECT COUNT(*) FROM dialogs d JOIN conversations c ON d.conv_id = c.conv_id WHERE date(d.created_at) = ? AND c.user_id NOT IN ({admin_ids_str})",
        (today,),
    )
    stats["today_dialogs"] = today_dialogs[0][0] if today_dialogs else 0
    active_users = db.query_db(
        f"""
        SELECT u.uid, u.user_name, u.first_name, u.last_name, COUNT(d.id) as message_count
        FROM users u
        JOIN conversations c ON u.uid = c.user_id
        JOIN dialogs d ON c.conv_id = d.conv_id
        WHERE date(d.created_at) = ? AND u.uid NOT IN ({admin_ids_str})
        GROUP BY u.uid, u.user_name, u.first_name, u.last_name
        ORDER BY message_count DESC
        LIMIT 5
    """,
        (today,),
    )
    stats["active_users"] = active_users or []
    return render_template("viewer_index.html", stats=stats)


@viewer_bp.route("/users")
@viewer_required
def viewer_users():
    """浏览者用户列表页面（排除管理员和群聊）"""
    admin_ids = get_admin_ids()
    admin_ids_str = ",".join(map(str, admin_ids))
    page = request.args.get("page", 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    search_term = request.args.get("search", "")
    sort_by = request.args.get("sort_by", "create_at")
    sort_order = request.args.get("sort_order", "desc")
    query = f"SELECT * FROM users WHERE uid NOT IN ({admin_ids_str})"
    params = []
    if search_term:
        query += " AND (uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
        search_param = f"%{search_term}%"
        params.extend([search_param, search_param, search_param, search_param])
    if sort_by and sort_order:
        query += f" ORDER BY {sort_by} {sort_order}"
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    users_data = db.query_db(query, tuple(params))
    count_query = f"SELECT COUNT(*) FROM users WHERE uid NOT IN ({admin_ids_str})"
    count_params = []
    if search_term:
        count_query += " AND (uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
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
        "viewer_users.html",
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


@viewer_bp.route("/conversations")
@viewer_required
def viewer_conversations():
    """浏览者对话管理页面（排除管理员）"""
    admin_ids = get_admin_ids()
    admin_ids_str = ",".join(map(str, admin_ids))
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
    query = f"""
        SELECT c.id, c.conv_id, c.user_id, c.character, c.preset, c.summary,
               c.create_at, c.update_at, c.delete_mark, c.turns,
               u.first_name, u.last_name, u.user_name
        FROM conversations c
        LEFT JOIN users u ON c.user_id = u.uid
        WHERE c.user_id NOT IN ({admin_ids_str})
    """
    params = []
    if search:
        query += """ AND (u.user_name LIKE ? OR
                           u.first_name LIKE ? OR
                           u.last_name LIKE ? OR
                           CAST(c.user_id AS TEXT) LIKE ?)"""
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param, search_param])
    query += f" ORDER BY c.{sort_by} {order} LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    conversations_data = db.query_db(query, tuple(params))
    count_query = f"SELECT COUNT(*) FROM conversations c LEFT JOIN users u ON c.user_id = u.uid WHERE c.user_id NOT IN ({admin_ids_str})"
    count_params = []
    if search:
        count_query += """ AND (u.user_name LIKE ? OR
                               u.first_name LIKE ? OR
                               u.last_name LIKE ? OR
                               CAST(c.user_id AS TEXT) LIKE ?)"""
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
        "viewer_conversations.html",
        conversations=conversations_list,
        page=page,
        total_pages=total_pages,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        next_sort_order=next_sort_order,
    )


@viewer_bp.route("/dialogs/<conv_id>")
@viewer_required
def viewer_dialogs(conv_id):
    """浏览者对话详情页面（排除管理员对话）"""
    admin_ids = get_admin_ids()
    admin_ids_str = ",".join(map(str, admin_ids))
    conv_check = db.query_db(
        f"SELECT user_id FROM conversations WHERE conv_id = ? AND user_id NOT IN ({admin_ids_str})",
        (conv_id,),
    )
    if not conv_check:
        flash("对话不存在或您没有权限查看", "error")
        return redirect(url_for("viewer.viewer_conversations"))
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    per_page = 50
    offset = (page - 1) * per_page
    conversation = db.query_db(
        """
        SELECT c.*, u.first_name, u.last_name, u.user_name
        FROM conversations c
        LEFT JOIN users u ON c.user_id = u.uid
        WHERE c.conv_id = ?
    """,
        (conv_id,),
    )
    if not conversation:
        flash("对话不存在", "error")
        return redirect(url_for("viewer.viewer_conversations"))
    conversation = conversation[0]
    if search:
        query = """SELECT * FROM dialogs
                   WHERE conv_id = ? AND (
                       raw_content LIKE ? OR
                       processed_content LIKE ?
                   )
                   ORDER BY turn_order ASC LIMIT ? OFFSET ?"""
        search_param = f"%{search}%"
        params = [conv_id, search_param, search_param, per_page, offset]
    else:
        query = "SELECT * FROM dialogs WHERE conv_id = ? ORDER BY turn_order ASC LIMIT ? OFFSET ?"
        params = [conv_id, per_page, offset]
    dialogs_data = db.query_db(query, tuple(params))
    count_query = "SELECT COUNT(*) FROM dialogs WHERE conv_id = ?"
    count_params = [conv_id]
    if search:
        count_query += " AND (raw_content LIKE ? OR processed_content LIKE ?)"
        count_params.extend([search_param, search_param])
    total_result = db.query_db(count_query, tuple(count_params))
    total_dialogs = total_result[0][0] if total_result else 0
    total_pages = (total_dialogs + per_page - 1) // per_page
    dialogs_list = []
    if dialogs_data:
        columns = [
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
            dialog_dict = {columns[i]: row[i] for i in range(len(columns))}
            dialogs_list.append(dialog_dict)
    return render_template(
        "viewer_dialogs.html",
        conversation=conversation,
        dialogs=dialogs_list,
        page=page,
        total_pages=total_pages,
        search=search,
        search_keyword=search,
        conv_id=conv_id,
        format_datetime=format_datetime,
    )