import utils.db_utils as db
import tiktoken
import logging
from utils.logging_utils import setup_logging
from bot_core.models import User
from utils.config_utils import get_api_multiple
from typing import List, Dict, Any, Optional, Tuple

setup_logging()
logger = logging.getLogger(__name__)
from datetime import datetime
def circulate_token(text: str):
    """计算给定文本的token数量。

    Args:
        text (str): 需要计算token的文本。

    Returns:
        int: 文本的token数量。如果计算失败，则返回字符串的长度。
    """
    try:
        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except Exception as e:
        print(f"错误: 计算token时发生错误 - {e}. 输出为字符串长度。")
        return len(str(text))

def update_user_usage(user: Any, messages: List[Dict[str, Any]], output: str, trigger_type: str) -> Optional[Tuple[int, int]]:
    """更新用户的token使用量和频率信息。

    Args:
        user (Any): 用户对象或群组相关对象。
        messages (List[Dict[str, Any]]): 发送给LLM的完整消息列表。
        output (str): 模型输出文本。
        trigger_type (str): 触发类型，例如 'private_chat', 'private_photo', 'group_chat', 'group_photo'。
    
    Returns:
        一个包含更新后的 (remain_frequency, temporary_frequency) 的元组，如果不是私聊场景则返回 None。
    """
    input_tokens = circulate_token(str(messages))
    output_tokens = circulate_token(output)

    # --- Private Chat & Photo Handling ---
    if trigger_type in ['private_chat', 'private_photo']:
        if not isinstance(user, User):
            logger.error(f"在 {trigger_type} 中, 'user' 参数必须是 User 对象。")
            return None

        user_id = user.id
        db.user_info_update(user_id, 'input_tokens', input_tokens, True)
        db.user_info_update(user_id, 'output_tokens', output_tokens, True)

        cost = 2 if trigger_type == 'private_photo' else get_api_multiple(user.api)
        tmp_frequency = user.temporary_frequency
        
        if tmp_frequency >= cost:
            db.user_sign_info_update(user_id, 'frequency', -cost)
            logger.debug(f"用户 {user_id} 消耗 {cost}, 扣除临时额度. 剩余: {tmp_frequency - cost}")
        else:
            remaining_cost = cost - tmp_frequency
            if tmp_frequency > 0:
                db.user_sign_info_update(user_id, 'frequency', -tmp_frequency)
            db.user_info_update(user_id, 'remain_frequency', -remaining_cost, True)
            logger.debug(f"用户 {user_id} 消耗 {cost}. 扣光临时额度 {tmp_frequency}, 再扣除常规额度 {remaining_cost}.")

        conv_id = user.active_conversation_id
        if conv_id:
            conv_turn = db.dialog_turn_get(conv_id, 'private')
            db.conversation_private_arg_update(conv_id , 'turns', conv_turn)
        db.user_info_update(user_id, 'dialog_turns', 1, True)
        logger.debug(f"已为{user_id}更新私聊使用记录\r\n输入:{input_tokens}输出:{output_tokens}")

        # --- 修复：从数据库重新获取更新后的额度信息并返回 ---
        updated_user_info = db.user_info_get(user_id)
        updated_sign_info = db.user_sign_info_get(user_id)
        
        if updated_user_info and updated_sign_info:
            return (updated_user_info.get('remain_frequency', 0), updated_sign_info.get('frequency', 0))
        else:
            # 如果获取失败，返回一个表示可能出错的值或记录日志
            logger.error(f"更新额度后无法重新获取用户 {user_id} 的信息。")
            return None

    # --- Group Chat & Photo Handling ---
    elif trigger_type == 'group_chat':
        if not hasattr(user, 'group') or not hasattr(user, 'user'):
            logger.error(f"在 {trigger_type} 中, 'user' 参数必须是一个包含 group 和 user 属性的对象。")
            return None
        group_id = user.group.id
        user_id = user.user.id
        db.group_info_update(group_id, 'call_count', 1, True)
        db.conversation_group_update(group_id, user_id, 'turns', 1)
        db.group_info_update(group_id, 'input_token', input_tokens, True)
        db.group_info_update(group_id, 'output_token', output_tokens, True)
        logger.debug(f"已为群组{group_id}更新消息使用记录\r\n输入:{input_tokens}\r\n输出:{output_tokens}")
        return None

    elif trigger_type == 'group_photo':
        if not isinstance(user, int):
            logger.error(f"在 {trigger_type} 中, 'user' 参数必须是群组ID (int)。")
            return None
        group_id = user
        db.group_info_update(group_id, 'call_count', 1, True)
        db.group_info_update(group_id, 'input_token', input_tokens, True)
        db.group_info_update(group_id, 'output_token', output_tokens, True)
        logger.debug(f"已为群组{group_id}更新图片分析使用记录\r\n输入:{input_tokens}\r\n输出:{output_tokens}")
        return None




def _get_core_stats():
    """获取核心统计数据。

    Returns:
        dict: 包含总用户数、总对话数、总消息数、总输入token、总输出token和总token的字典。
    """
    stats = {}
    
    # 获取总用户数
    stats["total_users"] = (
        db.query_db("SELECT COUNT(*) FROM users")[0][0]
        if db.query_db("SELECT COUNT(*) FROM users")
        else 0
    )
    
    # 获取总对话数
    stats["total_conversations"] = (
        db.query_db("SELECT COUNT(*) FROM conversations")[0][0]
        if db.query_db("SELECT COUNT(*) FROM conversations")
        else 0
    )
    
    # 获取总消息数
    stats["total_dialogs"] = (
        db.query_db("SELECT COUNT(*) FROM dialogs")[0][0]
        if db.query_db("SELECT COUNT(*) FROM dialogs")
        else 0
    )
    
    # 获取总群聊消息数
    stats["total_group_dialogs"] = (
        db.query_db("SELECT COUNT(*) FROM group_dialogs")[0][0]
        if db.query_db("SELECT COUNT(*) FROM group_dialogs")
        else 0
    )
    
    # 获取用户和群组的令牌总数
    user_token_stats = db.query_db(
        "SELECT SUM(input_tokens) as input_total, SUM(output_tokens) as output_total FROM users"
    )
    group_token_stats = db.query_db(
        "SELECT SUM(input_token) as input_total, SUM(output_token) as output_total FROM groups"
    )
    
    # 初始化token计数
    stats["total_input_tokens"] = 0
    stats["total_output_tokens"] = 0
    
    # 累加用户token
    if user_token_stats and user_token_stats[0]:
        stats["total_input_tokens"] += user_token_stats[0][0] or 0
        stats["total_output_tokens"] += user_token_stats[0][1] or 0
    
    # 累加群组token
    if group_token_stats and group_token_stats[0]:
        stats["total_input_tokens"] += group_token_stats[0][0] or 0
        stats["total_output_tokens"] += group_token_stats[0][1] or 0
        
    stats["total_tokens"] = stats["total_input_tokens"] + stats["total_output_tokens"]
    
    return stats

def _get_active_users_and_groups(today):
    """获取活跃用户和群组。

    Args:
        today (str): 当天的日期字符串。

    Returns:
        dict: 包含活跃用户列表和活跃群组列表的字典。
    """
    """获取活跃用户和群组"""
    stats = {}
    
    # 获取活跃用户
    active_users = db.query_db(
        """
        SELECT u.uid, u.user_name, u.first_name, u.last_name, COUNT(d.id) as message_count
        FROM users u
        JOIN conversations c ON u.uid = c.user_id
        JOIN dialogs d ON c.conv_id = d.conv_id
        WHERE date(d.created_at) = ?
        GROUP BY u.uid, u.user_name, u.first_name, u.last_name
        ORDER BY message_count DESC
        LIMIT 5
    """,
        (today,),
    )
    stats["active_users"] = active_users or []
    
    # 获取活跃群组
    active_groups = db.query_db(
        """
        SELECT g.group_id, g.group_name, COUNT(*) as message_count
        FROM groups g
        JOIN group_dialogs gd ON g.group_id = gd.group_id
        WHERE date(gd.create_at) = ?
        GROUP BY g.group_id, g.group_name
        ORDER BY message_count DESC
        LIMIT 5
    """,
        (today,),
    )
    stats["active_groups"] = active_groups or []
    
    return stats


def _get_trends(time_range):
    """获取增长趋势数据。

    Args:
        time_range (str): 时间范围，例如 '30d', '7d', '1d'。

    Returns:
        dict: 包含用户增长和对话趋势数据的字典。
    """
    """获取增长趋势数据"""
    stats = {}
    
    if time_range == "30d":
        days_back = 30
        user_date_format = "date(create_at)"
        user_group_format = "date(create_at)"
        dialog_date_format = "date(created_at)"
        dialog_group_format = "date(created_at)"
        group_date_format = "date(create_at)"
        group_group_format = "date(create_at)"
    elif time_range == "7d":
        days_back = 7
        user_date_format = "date(create_at)"
        user_group_format = "date(create_at)"
        dialog_date_format = "date(created_at)"
        dialog_group_format = "date(created_at)"
        group_date_format = "date(create_at)"
        group_group_format = "date(create_at)"
    elif time_range == "1d":
        days_back = 1
        user_date_format = "strftime('%H:00', create_at)"
        user_group_format = "strftime('%H', create_at)"
        dialog_date_format = "strftime('%H:00', created_at)"
        dialog_group_format = "strftime('%H', created_at)"
        group_date_format = "strftime('%H:00', create_at)"
        group_group_format = "strftime('%H', create_at)"
    else:
        days_back = 7
        user_date_format = "date(create_at)"
        user_group_format = "date(create_at)"
        dialog_date_format = "date(created_at)"
        dialog_group_format = "date(created_at)"
        group_date_format = "date(create_at)"
        group_group_format = "date(create_at)"

    if time_range == "1d":
        user_growth = db.query_db("""
            SELECT strftime('%H:00', create_at) as date, COUNT(*) as count
            FROM users
            WHERE date(create_at) = date('now')
            GROUP BY strftime('%H', create_at)
            ORDER BY strftime('%H', create_at)
        """)
    else:
        user_growth = db.query_db(f"""
            SELECT {user_date_format} as date, COUNT(*) as count
            FROM users
            WHERE date(create_at) >= date('now', '-{days_back} days')
            GROUP BY {user_group_format}
            ORDER BY {user_group_format}
        """)
    stats["user_growth"] = user_growth or []

    if time_range == "1d":
        dialog_trend = db.query_db("""
            SELECT strftime('%H:00', created_at) as date, COUNT(*) as count
            FROM dialogs
            WHERE date(created_at) = date('now')
            GROUP BY strftime('%H', created_at)
            ORDER BY strftime('%H', created_at)
        """)
    else:
        dialog_trend = db.query_db(f"""
            SELECT {dialog_date_format} as date, COUNT(*) as count
            FROM dialogs
            WHERE date(created_at) >= date('now', '-{days_back} days')
            GROUP BY {dialog_group_format}
            ORDER BY {dialog_group_format}
        """)
    stats["dialog_trend"] = dialog_trend or []

    if time_range == "1d":
        group_trend = db.query_db("""
            SELECT strftime('%H:00', create_at) as date, COUNT(*) as count
            FROM group_dialogs
            WHERE date(create_at) = date('now')
            GROUP BY strftime('%H', create_at)
            ORDER BY strftime('%H', create_at)
        """)
    else:
        group_trend = db.query_db(f"""
            SELECT {group_date_format} as date, COUNT(*) as count
            FROM group_dialogs
            WHERE date(create_at) >= date('now', '-{days_back} days')
            GROUP BY {group_group_format}
            ORDER BY {group_group_format}
        """)
    stats["group_trend"] = group_trend or []

    # 不再合并私聊和群聊趋势，将它们分开返回
    # 确保数据按日期排序
    stats["dialog_trend"] = sorted(dialog_trend or [])
    stats["group_trend"] = sorted(group_trend or [])

    return stats


def get_dashboard_stats(time_range="7d"):
    """获取仪表盘的所有统计数据"""
    stats = _get_core_stats()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 获取今日统计
    today_conversations = db.query_db(
        "SELECT COUNT(*) FROM conversations WHERE date(create_at) = ?", (today,)
    )
    stats["today_conversations"] = (
        today_conversations[0][0] if today_conversations else 0
    )
    
    today_dialogs = db.query_db(
        "SELECT COUNT(*) FROM dialogs WHERE date(created_at) = ?", (today,)
    )
    stats["today_dialogs"] = today_dialogs[0][0] if today_dialogs else 0
    
    today_group_dialogs = db.query_db(
        "SELECT COUNT(*) FROM group_dialogs WHERE date(create_at) = ?", (today,)
    )
    stats["today_group_dialogs"] = (
        today_group_dialogs[0][0] if today_group_dialogs else 0
    )
    
    if stats["total_dialogs"] > 0:
        today_ratio = stats["today_dialogs"] / stats["total_dialogs"]
        stats["today_input_tokens"] = int(stats["total_input_tokens"] * today_ratio)
        stats["today_output_tokens"] = int(stats["total_output_tokens"] * today_ratio)
        stats["today_total_tokens"] = (
            stats["today_input_tokens"] + stats["today_output_tokens"]
        )
    else:
        stats["today_input_tokens"] = 0
        stats["today_output_tokens"] = 0
        stats["today_total_tokens"] = 0
        
    # 获取活跃用户和群组
    active_stats = _get_active_users_and_groups(today)
    stats.update(active_stats)
    
    # 获取趋势数据
    trend_stats = _get_trends(time_range)
    stats.update(trend_stats)
    
    # 为令牌趋势计算，在函数内部临时合并消息趋势
    merged_trend = {}
    for date, count in stats.get("dialog_trend", []):
        merged_trend[date] = merged_trend.get(date, 0) + count
    for date, count in stats.get("group_trend", []):
        merged_trend[date] = merged_trend.get(date, 0) + count
    all_messages_trend = sorted(merged_trend.items())

    # 计算令牌趋势
    token_trend = []
    total_messages = stats["total_dialogs"] + stats["total_group_dialogs"]
    for item in all_messages_trend:
        if total_messages > 0:
            # 避免除以零的错误
            total_messages_in_range = sum(v for k, v in all_messages_trend)
            if total_messages_in_range > 0:
                ratio = item[1] / total_messages_in_range
                estimated_tokens = int(
                    (stats["total_input_tokens"] + stats["total_output_tokens"]) * ratio
                )
            else:
                estimated_tokens = 0
        else:
            estimated_tokens = 0
        token_trend.append((item[0], estimated_tokens))
    stats["token_trend"] = token_trend
    
    stats["time_range"] = time_range
    
    return stats
