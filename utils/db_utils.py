import datetime
import json
import logging
import os
import sqlite3
import threading
from sqlite3 import Error
from typing import Any, List, Optional, Tuple

from utils.config_utils import get_config, get_path
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# 从配置系统获取默认值
DEFAULT_API = get_config("api.default_api")  # 默认使用的LLM API
DEFAULT_PRESET = get_config("user.default_preset")  # 默认预设名称
DEFAULT_CHAR = get_config("user.default_char")  # 默认角色名称
DEFAULT_STREAM = get_config("user.default_stream")  # 默认是否开启流式传输 ('yes'/'no')
DEFAULT_FREQUENCY = get_config("user.default_frequency")  # 用户默认的每日免费使用次数
DEFAULT_BALANCE = get_config("user.default_balance")  # 用户默认的初始余额


class DatabaseConnectionPool:
    """
    数据库连接池，使用单例模式实现。

    提供数据库连接的获取、释放和管理功能，确保线程安全。
    """

    _instance: Optional["DatabaseConnectionPool"] = None
    _lock = threading.Lock()

    def __new__(
        cls, db_file: Optional[str] = None, max_connections: Optional[int] = None
    ) -> "DatabaseConnectionPool":
        """
        实现单例模式，确保全局只有一个连接池实例。

        Args:
            db_file: 数据库文件路径，如果为None则使用配置中的路径
            max_connections: 连接池中的最大连接数，如果为None则使用配置中的值

        Returns:
            DatabaseConnectionPool: 单例实例
        """
        # 优先使用传入的参数，其次是环境变量，最后是配置文件
        if db_file is None:
            db_file = os.environ.get("DB_PATH", get_config("database.default_path"))

        # 获取最大连接数
        if max_connections is None:
            max_connections = get_config("database.max_connections", 5)
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
                cls._instance.db_file = db_file
                cls._instance.max_connections = max_connections
                cls._instance.connections: List[sqlite3.Connection] = []
                cls._instance.connection_locks: List[threading.Lock] = []
                cls._instance.initialize_pool()
        return cls._instance

    def initialize_pool(self):
        """
        根据 max_connections 初始化连接池中的数据库连接。
        """
        for _ in range(self.max_connections):
            try:
                conn = sqlite3.connect(self.db_file, check_same_thread=False)
                self.connections.append(conn)
                self.connection_locks.append(threading.Lock())
            except Error as e:
                print(f"初始化连接池时发生错误: {e}")

    def get_connection(self) -> Tuple[Optional[sqlite3.Connection], int]:
        """
        从连接池中获取一个可用的数据库连接及其索引。

        如果所有池中连接都在使用，则尝试创建一个临时连接。

        Returns:
            Tuple[Optional[sqlite3.Connection], int]: 一个元组 (connection, index)。
                如果成功获取连接，connection 是 sqlite3.Connection 对象，index 是连接在池中的索引（临时连接为 -1）。
                如果获取失败，connection 是 None，index 是 -1。
        """
        for i, lock in enumerate(self.connection_locks):
            if lock.acquire(blocking=False):
                return self.connections[i], i
        # 如果所有连接都在使用中，创建一个临时连接
        try:
            temp_conn = sqlite3.connect(self.db_file, check_same_thread=False)
            return temp_conn, -1  # -1 表示这是一个临时连接
        except Error as e:
            print(f"创建临时连接时发生错误: {e}")
            return None, -1

    def release_connection(self, index: int):
        """
        释放连接池中指定索引的连接锁，使其可被其他线程使用。

        此方法不关闭连接，仅释放锁。

        Args:
            index: 要释放的连接在池中的索引
        """
        if 0 <= index < len(self.connection_locks):
            self.connection_locks[index].release()

    def close_all(self):
        """关闭连接池中的所有数据库连接，并清空连接列表。应在应用退出时调用。"""
        for conn in self.connections:
            try:
                conn.close()
            except Error:
                pass
        self.connections = []
        self.connection_locks = []


# 创建全局连接池实例
db_pool = DatabaseConnectionPool()


def create_connection() -> Optional[sqlite3.Connection]:
    """
    获取一个数据库连接。

    Note:
        主要为兼容旧代码，推荐直接使用连接池。

    Returns:
        Optional[sqlite3.Connection]: 数据库连接对象
    """
    conn, _ = db_pool.get_connection()
    return conn


def execute_db_operation(operation_type: str, command: str, params: Tuple = ()):
    """
    执行数据库操作的通用函数。

    Args:
        operation_type: 操作类型，可以是 "query" 或 "update"
        command: 要执行的 SQL 命令
        params: SQL 命令的参数

    Returns:
        Union[List[Any], int]: 如果是查询操作，返回结果列表；如果是更新操作，返回受影响的行数。
            发生错误时，查询返回空列表，更新返回0。
    """
    conn, conn_index = db_pool.get_connection()
    if not conn:
        print(f"数据库错误: 无法获取连接以执行 {operation_type} 操作: {command}")
        return [] if operation_type == "query" else 0

    try:
        cursor = conn.cursor()
        cursor.execute(command, params)

        if operation_type == "update":
            conn.commit()
            result = cursor.rowcount
        else:  # query
            result = cursor.fetchall()

        return result
    except sqlite3.Error as e:
        print(f"数据库 {operation_type} 操作失败: {command} 参数: {params} 错误: {e}")
        return [] if operation_type == "query" else 0
    finally:
        if conn_index >= 0:  # 如果是连接池中的连接，释放它
            db_pool.release_connection(conn_index)
        else:  # 如果是临时连接，关闭它
            if conn:  # 确保临时连接存在才关闭
                conn.close()


def revise_db(command: str, params: Tuple = ()) -> int:
    """
    执行数据库更新操作。

    Args:
        command: SQL 更新命令
        params: SQL 命令的参数

    Returns:
        int: 受影响的行数
    """
    return execute_db_operation("update", command, params)


def query_db(command: str, params: Tuple = ()) -> List[Any]:
    """
    执行数据库查询操作。

    Args:
        command: SQL 查询命令
        params: SQL 命令的参数

    Returns:
        List[Any]: 查询结果列表
    """
    return execute_db_operation("query", command, params)


def user_config_get(userid: int) -> dict:
    """
    获取用户的完整配置信息。

    Args:
        userid: 用户ID

    Returns:
        dict: 包含 char, api, preset, conv_id, stream, user_id, user_nick 的配置字典
    """
    command = (
        "SELECT char, api, preset, conv_id,stream,nick FROM user_config WHERE uid = ?"
    )
    result = query_db(command, (userid,))
    return (
        {
            "char": result[0][0],
            "api": result[0][1],
            "preset": result[0][2],
            "conv_id": result[0][3],
            "stream": result[0][4],
            "user_id": userid,
            "user_nick": result[0][5],
        }
        if result
        else {}
    )


def user_conv_id_get(user_id: int) -> int:
    """
    获取用户当前激活的对话ID。

    Args:
        user_id: 用户ID

    Returns:
        int: 对话ID，如果未找到或未设置则返回0
    """
    command = "SELECT conv_id FROM user_config WHERE uid = ?"
    result = query_db(command, (user_id,))
    return result[0][0] if result and result[0] and result[0][0] is not None else 0


def user_api_get(userid: int) -> str:
    """
    获取用户配置的API。

    Args:
        userid: 用户ID

    Returns:
        str: 用户配置的API，如果未找到或未设置则返回空字符串
    """
    command = "SELECT api FROM user_config WHERE uid = ?"
    result = query_db(command, (userid,))
    return result[0][0] if result else ""


def user_stream_get(userid: int) -> Optional[bool]:
    """
    获取用户是否开启流式传输。

    Args:
        userid: 用户ID

    Returns:
        Optional[bool]: 是否开启流式传输，如果未找到配置则返回None
    """
    command = "SELECT stream FROM user_config WHERE uid = ?"
    result = query_db(command, (userid,))
    return True if result[0][0] == "yes" else False


def user_stream_switch(userid: int) -> bool:
    """
    切换用户的流式传输设置。

    Args:
        userid: 用户ID

    Returns:
        bool: 操作是否成功
    """
    if user_stream_get(userid):
        command = "UPDATE  user_config set stream = 'no' WHERE uid = ?"
    else:
        command = "UPDATE  user_config set stream = 'yes' WHERE uid = ?"
    result = revise_db(command, (userid,))
    return result > 0


def user_config_arg_update(user_id: int, field: str, value: Any) -> bool:
    """
    更新用户配置表中的指定字段。

    Args:
        user_id: 用户ID
        field: 要更新的字段名
        value: 新的字段值

    Returns:
        bool: 操作是否成功
    """
    command = f"UPDATE user_config SET {field} = ? WHERE uid = ?"
    result = revise_db(command, (value, user_id))
    return result > 0


def user_config_create(userid: int) -> bool:
    """
    为新用户创建默认配置。

    Args:
        userid: 用户ID

    Returns:
        bool: 操作是否成功
    """
    command = (
        "INSERT INTO user_config (char, api, preset, uid,stream) VALUES (?, ?, ?, ?,?)"
    )
    result = revise_db(
        command, (DEFAULT_CHAR, DEFAULT_API, DEFAULT_PRESET, userid, DEFAULT_STREAM)
    )
    return result > 0


def user_config_check(userid: int) -> bool:
    """检查用户是否在 `users` 表中存在（通常用于判断是否是已知用户）。返回True表示存在。"""
    command = "SELECT uid FROM users WHERE uid = ?"
    result = query_db(command, (userid,))
    return bool(result)


def user_conversations_get(userid: int) -> Optional[List[Tuple]]:
    """获取用户未标记为删除的私聊对话列表。返回 (conv_id, character, summary) 元组的列表。"""
    command = "SELECT conv_id, character, summary,update_at,turns FROM conversations WHERE user_id = ? AND delete_mark = 'no'"
    result = query_db(command, (userid,))
    return result if result else None


def user_conversations_get_for_dialog(userid: int) -> Optional[List[Tuple]]:
    """获取用户未标记为删除的私聊对话列表，用于dialog命令。返回 (conv_id, character, turns, update_at, summary) 元组的列表。"""
    command = "SELECT conv_id, character, turns, update_at, summary FROM conversations WHERE user_id = ? AND delete_mark = 'no' ORDER BY update_at DESC"
    result = query_db(command, (userid,))
    return result if result else None


def user_info_get(userid: int) -> dict:
    """获取用户的基本信息。返回 (first_name, last_name, account_tier, remain_frequency, balance, uid)。"""
    command = "SELECT first_name, last_name, account_tier, remain_frequency, balance,uid FROM users WHERE uid = ?"
    result = query_db(command, (userid,))
    if result:
        return {
            "user_name": f"{(str(result[0][0] or '') + str(result[0][1] or '')).strip()}",
            "first_name": result[0][0],
            "last_name": result[0][1],
            "tier": result[0][2],
            "remain": result[0][3],
            "balance": result[0][4],
        }
    else:
        return {}


def user_info_usage_get(userid: int, column_name: str) -> Any:
    """
    获取用户 `users` 表中指定列的信息。
    警告: 此函数直接将 column_name 拼接到SQL查询中，可能存在SQL注入风险。
          应确保调用时 column_name 来自受信任的、预定义的列名集合。
          未来版本建议重构此函数以避免直接拼接。

    :param userid: 用户ID。
    :param column_name: 要查询的列名。
    :return: 指定列的值，如果查询失败或用户不存在则返回0 (或根据列类型可能为其他默认值)。
    """
    # SQL注入风险警告：column_name 未经验证直接拼接到查询中。
    # 仅在 column_name 确定安全的情况下使用。
    allowed_columns = {
        "first_name",
        "last_name",
        "user_name",
        "create_at",
        "update_at",
        "input_tokens",
        "output_tokens",
        "account_tier",
        "remain_frequency",
        "balance",
    }
    if column_name not in allowed_columns:
        print(f"错误: user_info_usage_get 查询了不允许的列名: {column_name}")
        return 0  # 或者抛出异常

    command = f"SELECT {column_name} FROM users WHERE uid = ?"
    result = query_db(command, (userid,))
    return result[0][0] if result and result[0] else 0


def user_info_create(
    userid: int, first_name: str, last_name: str, user_name: str
) -> bool:
    """创建用户信息"""
    create_at = str(datetime.datetime.now())
    command = "INSERT INTO users(uid,first_name,last_name,user_name,create_at,update_at,input_tokens,output_tokens,account_tier,remain_frequency,balance) VALUES (?, ?, ?, ?, ?, ?,?,?,?,?,?)"
    result = revise_db(
        command,
        (
            userid,
            first_name,
            last_name,
            user_name,
            create_at,
            create_at,
            0,
            0,
            0,
            DEFAULT_FREQUENCY,
            DEFAULT_BALANCE,
        ),
    )
    return result > 0


def user_info_update(userid, field: str, value: Any, increment: bool = False) -> bool:
    """
    更新用户信息
    :param userid: 用户ID
    :param field: 需要更新的字段名
    :param value: 更新值或增量值
    :param increment: 是否为增量更新，默认为 False（直接设置值）
    :return: 更新是否成功
    """
    try:
        # 尝试转换为整数，如果成功则按uid处理
        uid = int(userid)
        if increment:
            command = (
                f"UPDATE users SET {field} = COALESCE({field}, 0) + ? WHERE uid = ?"
            )
        else:
            command = f"UPDATE users SET {field} = ? WHERE uid = ?"
        userid = uid
    except ValueError:
        # 不是数字则按用户名处理，转换为小写并去除可能的前缀
        userid = str(userid).lower()[1:] if len(str(userid)) > 1 else ""
        if increment:
            command = f"UPDATE users SET {field} = COALESCE({field}, 0) + ? WHERE LOWER(user_name) = ?"
        else:
            command = f"UPDATE users SET {field} = ? WHERE LOWER(user_name) = ?"
    result = revise_db(command, (value, userid))
    return result > 0


def user_frequency_free(value: int) -> bool:
    """为所有用户的 `remain_frequency` 增加指定值。返回操作是否影响了行。"""
    command = f"UPDATE users SET remain_frequency = COALESCE(remain_frequency, 0) + ?"
    result = revise_db(command, (value,))
    return result > 0


def _update_conversation_timestamp(
    conv_id: int, create_at: str, table_name: str
) -> bool:
    """辅助函数：更新对话表的时间戳"""
    command = f"UPDATE {table_name} SET update_at = ? WHERE conv_id = ?"
    return revise_db(command, (create_at, conv_id)) > 0


def dialog_content_add(
    conv_id: int,
    role: str,
    turn_order: int,
    raw_content: str,
    processed_content: str,
    msg_id: Optional[int] = None,
    chat_type: str = "private",
) -> bool:
    """
    添加对话内容到相应的对话表，并更新对应会话表的 `update_at` 时间戳。

    :param conv_id: 会话ID。
    :param role: 角色（如 'user', 'assistant'）。
    :param turn_order: 对话轮次。
    :param raw_content: 原始对话内容。
    :param processed_content: 处理后的对话内容。
    :param msg_id: 消息ID，仅对私聊 ('private') 有效。
    :param chat_type: 对话类型，'private' 或 'group'。
    :return: 操作是否成功。
    """
    create_at = str(datetime.datetime.now())

    if chat_type == "private":
        dialog_table = "dialogs"
        conversation_table = "conversations"
        if msg_id is None:
            print("错误: 私聊对话内容添加时 msg_id 不能为空。")
            return False
        insert_command = f"INSERT INTO {dialog_table} (conv_id, role, raw_content, turn_order, created_at, processed_content, msg_id) VALUES (?, ?, ?, ?, ?, ?, ?)"
        params = (
            conv_id,
            role,
            raw_content,
            turn_order,
            create_at,
            processed_content,
            msg_id,
        )
    elif chat_type == "group":
        dialog_table = "group_user_dialogs"
        conversation_table = "group_user_conversations"
        insert_command = f"INSERT INTO {dialog_table} (conv_id, role, raw_content, turn_order, created_at, processed_content) VALUES (?, ?, ?, ?, ?, ?)"
        params = (conv_id, role, raw_content, turn_order, create_at, processed_content)
    else:
        print(f"错误: 未知的 chat_type '{chat_type}' 在 dialog_content_add 中。")
        return False

    result = revise_db(insert_command, params)
    if result:
        return _update_conversation_timestamp(conv_id, create_at, conversation_table)
    return False


def dialog_new_content_add(conv_id: int, turn: int) -> bool:
    """（似乎是未完成或特定用途的函数）在 `dialogs` 表中插入一条只有 conv_id 和 turn_order 的记录。返回操作是否成功。"""
    command = "INSERT INTO dialogs (conv_id,turn_order) values (?,?)"
    return revise_db(command, (conv_id, turn)) > 0


def dialog_latest_del(conv_id: int) -> int:
    """
    删除指定conv_id中turn_order最大的记录
    参数:
        conv_id: 会话ID
    返回:
        受影响的行数（通常为1，如果删除成功；0，如果没有记录被删除）
    """
    # 步骤1：查询指定conv_id中最大的turn_order
    query_cmd = "SELECT MAX(turn_order) FROM dialogs WHERE conv_id = ?"
    result = query_db(query_cmd, (conv_id,))

    # 检查查询结果，如果没有记录，则返回0
    max_turn_order = result[0][0] if result and result[0][0] is not None else None
    if max_turn_order is None:
        return 0

    # 步骤2：删除该conv_id中turn_order最大的记录
    delete_cmd = "DELETE FROM dialogs WHERE conv_id = ? AND turn_order = ?"
    affected_rows = revise_db(delete_cmd, (conv_id, max_turn_order))

    return affected_rows


def dialog_turn_get(conv_id: int, chat_type: str = "private") -> int:
    """
    获取指定会话的当前对话轮数。

    :param conv_id: 会话ID。
    :param chat_type: 对话类型，'private' 或 'group'。
    :return: 最大轮次数，如果不存在则返回 0。
    """
    if chat_type == "private":
        table_name = "dialogs"
    elif chat_type == "group":
        table_name = "group_user_dialogs"
    else:
        print(
            f"警告: 未知的 chat_type '{chat_type}' 在 dialog_turn_get 中，无法确定表名。"
        )
        return 0

    command = f"SELECT MAX(turn_order) FROM {table_name} WHERE conv_id = ?"
    result = query_db(command, (conv_id,))
    return result[0][0] if result and result[0][0] is not None else 0


def dialog_content_load(
    conv_id: int, chat_type: str = "private"
) -> Optional[List[Tuple]]:
    """
    加载指定会话的对话内容。

    Args:
        conv_id: 会话ID
        chat_type: 对话类型，'private' 或 'group'，其他类型将默认查询私聊对话表

    Returns:
        Optional[List[Tuple]]: 对话内容列表 (role, turn_order, processed_content)，如果不存在则返回None
    """
    if chat_type == "group":
        table_name = "group_user_dialogs"
    else:  # 默认为 'private' 或其他未知类型也查私聊表
        table_name = "dialogs"
        if chat_type != "private":
            print(
                f"警告: 未知的 chat_type '{chat_type}' 在 dialog_content_load 中，默认查询 '{table_name}' 表。"
            )

    command = f"SELECT role, turn_order, processed_content FROM {table_name} WHERE conv_id = ?"
    result = query_db(command, (conv_id,))
    return result if result else None


def dialog_last_input_get(conv_id: int) -> str:
    """
    获取指定会话的倒数第二条原始内容。

    Args:
        conv_id: 会话ID

    Returns:
        str: 倒数第二条原始内容，如果不存在则返回空字符串
    """
    command = "SELECT raw_content FROM dialogs WHERE conv_id = ? ORDER BY turn_order DESC LIMIT 2;"
    result = query_db(command, (conv_id,))
    return result[1][0] if result else ""


def conversation_private_create(
    conv_id: int, userid: int, character: str, preset: str
) -> bool:
    """
    创建一条新的私聊对话记录，并更新用户的update_at时间。

    Args:
        conv_id: 会话ID
        userid: 用户ID
        character: 角色名称
        preset: 预设名称

    Returns:
        bool: 操作是否成功
    """
    create_at = str(datetime.datetime.now())
    user_info_update(userid, "update_at", create_at)
    command = "INSERT INTO conversations (conv_id, user_id, character, preset, create_at, update_at, delete_mark) VALUES (?, ?, ?, ?, ?, ?, 'yes')"
    result = revise_db(
        command, (conv_id, userid, character, preset, create_at, create_at)
    )
    return result > 0


def conversation_private_save(conv_id: int) -> bool:
    """
    将私聊对话的delete_mark设置为'no'，表示保存该对话。

    Args:
        conv_id: 会话ID

    Returns:
        bool: 操作是否成功
    """
    command = "UPDATE conversations SET delete_mark = 'no' WHERE conv_id = ?"
    result = revise_db(command, (conv_id,))
    return result > 0


def conversation_private_get(conv_id: int) -> Optional[Tuple[str, str]]:
    """
    获取指定私聊对话的角色和预设。

    Args:
        conv_id: 会话ID

    Returns:
        Optional[Tuple[str, str]]: (character, preset) 元组，如果未找到则返回None
    """
    command = "SELECT character, preset FROM conversations WHERE conv_id = ?"
    result = query_db(command, (conv_id,))
    return result[0] if result else None


def conversation_latest_message_id_get(conv_id: int) -> list:
    """
    获取指定会话的最新两条消息的msg_id列表。

    Args:
        conv_id: 会话ID

    Returns:
        list: msg_id列表，如果未找到则返回空列表
    """
    command = (
        "SELECT msg_id FROM dialogs WHERE conv_id = ? ORDER BY turn_order DESC LIMIT 2;"
    )
    result = query_db(command, (conv_id,))
    if result and len(result) > 0:
        return [
            row[0] for row in result
        ]  # 提取每个元组的第一个元素（msg_id），返回列表
    else:
        return []


def conversation_delete_messages(conv_id: int, msg_id: int) -> bool:
    """
    删除指定 conv_id 和 msg_id 的消息记录。如果存在多个 msg_id 相同的行，只删除 id 最大的那一行。
    如果成功删除了记录，返回 True；否则，返回 False。
    """
    try:
        # 1. 获取具有相同 conv_id 和 msg_id 的所有记录，并按 id 降序排序
        query = (
            "SELECT id FROM dialogs WHERE conv_id = ? AND msg_id = ? ORDER BY id DESC"
        )
        rows = query_db(query, (conv_id, msg_id))
        if not rows:
            logger.debug(
                f"未找到 conv_id 为 {conv_id} 且 msg_id 为 {msg_id} 的消息记录"
            )  # 添加日志
            return False  # 没有找到匹配的记录
        # 2. 删除 id 最大的那一条记录
        max_id = rows[0][0]  # 从元组列表中获取 id
        delete_command = "DELETE FROM dialogs WHERE id = ?"
        result = revise_db(
            delete_command, (max_id,)
        )  # 执行数据库删除操作，返回受影响的行数
        if result > 0:
            logger.debug(
                f"成功删除消息记录，conv_id: {conv_id}, msg_id: {msg_id}, id: {max_id}"
            )  # 添加日志
        else:
            logger.debug(
                f"删除消息记录失败，conv_id: {conv_id}, msg_id: {msg_id}, id: {max_id}"
            )  # 添加日志
        return result > 0  # 如果影响的行数大于0，则返回 True，表示删除成功
    except Exception as e:
        logger.error(f"删除消息记录时发生错误：{e}")
        return False  # 发生错误时，返回 False


def conversation_group_config_get(
    conv_id: int, group_id: int
) -> Optional[Tuple[str, str]]:
    """
    获取指定群聊用户会话关联的群组的角色和预设。

    Args:
        conv_id: 会话ID
        group_id: 群组ID

    Returns:
        Optional[Tuple[str, str]]: (char, preset) 元组，如果未找到则返回None
    """
    if group_id:
        command = "SELECT char, preset FROM groups WHERE group_id = ?"
        result = query_db(command, (group_id,))
    else:
        command = "SELECT group_id FROM group_user_conversations WHERE conv_id = ?"
        result = query_db(command, (conv_id,))
        group_id = result[0][0]
        command = "SELECT char, preset FROM groups WHERE group_id = ?"
        result = query_db(command, (group_id,))
    return result[0] if result else None


def conversation_private_update(conv_id: int, char: str, preset: str) -> bool:
    """
    更新指定私聊对话的角色和预设。

    Args:
        conv_id: 会话ID
        char: 角色名称
        preset: 预设名称

    Returns:
        bool: 操作是否成功
    """
    command = "UPDATE conversations SET character = ?, preset = ? WHERE conv_id = ?"
    result = revise_db(command, (char, preset, conv_id))
    return result > 0


def conversation_private_arg_update(
    conv_id: int, field: str, value: Any, increment: bool = False
) -> bool:
    """
    更新私聊对话表(conversations)中的指定字段。

    Args:
        conv_id: 会话ID
        field: 要更新的字段名
        value: 新的字段值或增量值
        increment: 是否为增量更新，默认为False

    Returns:
        bool: 操作是否成功
    """
    if increment:
        command = f"UPDATE conversations SET {field} = COALESCE({field}, 0) + ? WHERE conv_id = ?"
    else:
        command = f"UPDATE conversations SET {field} = ? WHERE conv_id = ?"
    result = revise_db(command, (value, conv_id))
    return result > 0


def conversation_private_delete(conv_id: int) -> bool:
    """
    将指定私聊对话的delete_mark设置为'yes'，标记为删除。

    Args:
        conv_id: 会话ID

    Returns:
        bool: 操作是否成功
    """
    command = "UPDATE conversations SET delete_mark = ? WHERE conv_id = ?"
    result = revise_db(command, ("yes", conv_id))
    return result > 0


def conversation_private_check(conv_id: int) -> bool:
    """
    检查具有指定conv_id的私聊对话是否存在。

    Args:
        conv_id: 会话ID

    Returns:
        bool: True表示不存在，False表示存在
    """
    command = "SELECT conv_id FROM conversations WHERE conv_id = ?"
    result = query_db(command, (conv_id,))
    return not bool(result)


def conversation_private_get_user(conv_id: int) -> Optional[int]:
    """
    获取指定私聊对话的用户ID。

    Args:
        conv_id: 会话ID

    Returns:
        Optional[int]: 用户ID，如果未找到则返回None
    """
    command = "SELECT user_id FROM conversations WHERE conv_id = ?"
    result = query_db(command, (conv_id,))
    return result[0][0] if result and result[0] else None


def conversation_private_summary_add(conv_id: int, summary: str) -> bool:
    """
    为指定私聊对话添加或更新总结。

    Args:
        conv_id: 会话ID
        summary: 对话总结

    Returns:
        bool: 操作是否成功
    """
    command = "UPDATE conversations SET summary = ? WHERE conv_id = ?"
    result = revise_db(command, (summary, conv_id))
    return result > 0


def conversation_group_create(
    conv_id: int, user_id: int, user_name: str, group_id: int, group_name: str
) -> bool:
    """
    为指定用户在指定群组中创建一条新的群聊用户会话记录，并更新群组的update_time。

    Args:
        conv_id: 会话ID
        user_id: 用户ID
        user_name: 用户名
        group_id: 群组ID
        group_name: 群组名

    Returns:
        bool: 操作是否成功
    """
    create_at = str(datetime.datetime.now())
    group_info_update(group_id, "update_time", create_at)
    command = "INSERT INTO group_user_conversations (user_id, user_name, group_id, group_name, conv_id, create_at, delete_mark) VALUES (?, ?, ?, ?, ?, ?, 'no')"
    result = revise_db(
        command, (user_id, user_name, group_id, group_name, conv_id, create_at)
    )
    return result > 0


def conversation_group_check(conv_id: int) -> bool:
    """
    检查具有指定conv_id且未标记删除的群聊用户会话是否存在。

    Args:
        conv_id: 会话ID

    Returns:
        bool: True表示不存在，False表示存在
    """
    command = "SELECT conv_id FROM group_user_conversations WHERE conv_id = ? AND delete_mark = 'no'"
    result = query_db(command, (conv_id,))
    return not bool(result)


def conversation_group_get(group_id: int, user_id: int) -> Optional[int]:
    """
    获取指定用户在指定群组中未标记删除的群聊用户会话ID。

    Args:
        group_id: 群组ID
        user_id: 用户ID

    Returns:
        Optional[int]: 会话ID，如果未找到则返回None
    """
    command = "SELECT conv_id FROM group_user_conversations WHERE group_id = ? AND user_id = ? AND delete_mark = 'no'"
    result = query_db(command, (group_id, user_id))
    return result[0][0] if result else None


def conversation_group_update(
    group_id: int, user_id: int, field: str, value: Any
) -> bool:
    """
    更新指定用户在指定群组中未标记删除的群聊用户会话的指定字段。

    Args:
        group_id: 群组ID
        user_id: 用户ID
        field: 要更新的字段名
        value: 新的字段值

    Returns:
        bool: 操作是否成功
    """
    command = f"UPDATE group_user_conversations SET {field} = COALESCE({field}, 0) + ? WHERE group_id = ? AND user_id = ? AND delete_mark = 'no'"
    result = revise_db(command, (value, group_id, user_id))
    return result > 0


def conversation_group_delete(group_id: int, user_id: int) -> bool:
    """
    将指定用户在指定群组中的群聊用户会话标记为删除(delete_mark = 'yes')。

    Args:
        group_id: 群组ID
        user_id: 用户ID

    Returns:
        bool: 操作是否成功
    """
    command = "UPDATE group_user_conversations SET delete_mark = 'yes' WHERE group_id = ? AND user_id = ?"
    result = revise_db(command, (group_id, user_id))
    return result > 0


def conversation_turns_update(
    conv_id: int, turn_num: int, chat_type: str = "private"
) -> bool:
    """
    更新指定会话的对话轮数。

    :param conv_id: 会话ID。
    :param turn_num: 新的对话轮数。
    :param chat_type: 对话类型，'private' 或 'group'。
    :return: 操作是否成功。
    """
    if chat_type == "private":
        table = "conversations"
    elif chat_type == "group":
        table = "group_user_conversations"
    else:
        print(
            f"警告: 未知的 chat_type '{chat_type}' 在 conversation_turns_update 中，无法更新轮数。"
        )
        return False
    command = f"UPDATE {table} SET turns = ? WHERE conv_id = ?"
    result = revise_db(command, (turn_num, conv_id))
    return result > 0


def group_check_update(group_id: int) -> bool:
    """
    检查群组信息是否需要更新（基于上次更新时间是否超过5分钟）。

    Args:
        group_id: 群组ID

    Returns:
        bool: True表示需要更新或群组不存在，False表示不需要更新
    """
    command = "SELECT update_time FROM groups WHERE group_id = ?"
    result = query_db(command, (group_id,))
    if result:
        # 尝试解析带微秒的时间格式，如果失败则尝试不带微秒的格式
        time_str = str(result[0][0])
        try:
            update_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            update_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return update_time < datetime.datetime.now() - datetime.timedelta(minutes=5)
    return True


def group_config_get(group_id: int) -> Optional[Tuple[str, str, str]]:
    """
    获取指定群组的配置。

    Args:
        group_id: 群组ID

    Returns:
        Optional[Tuple[str, str, str]]: (api, char, preset) 元组，如果未找到则返回False
    """
    command = "SELECT api, char, preset FROM groups WHERE group_id = ?"
    result = query_db(command, (group_id,))
    return result[0] if result else False


def group_config_arg_update(group_id: int, field: str, value: Any) -> bool:
    """
    更新群组配置表中的指定字段。

    Args:
        group_id: 群组ID
        field: 要更新的字段名
        value: 新的字段值

    Returns:
        bool: 操作是否成功
    """
    command = f"UPDATE groups SET {field} = ? WHERE group_id = ?"
    result = revise_db(command, (value, group_id))
    return result > 0


def group_name_get(group_id: int) -> Optional[str]:
    """
    获取指定群组的名称。

    Args:
        group_id: 群组ID

    Returns:
        Optional[str]: 群组名称，如果未找到则返回空字符串
    """
    command = "SELECT group_name FROM groups WHERE group_id =?"
    result = query_db(command, (group_id,))
    return result[0][0] or ""


def group_admin_list_get(group_id: int) -> List[str]:
    """
    获取指定群组的管理员列表（从JSON字符串解析）。

    Args:
        group_id: 群组ID

    Returns:
        List[str]: 管理员列表，如果解析失败或无数据则返回空列表
    """
    try:
        command = "SELECT members_list FROM groups WHERE group_id = ?"
        result = query_db(command, (group_id,))
        return json.loads(result[0][0]) if result and result[0][0] else []
    except Exception as e:
        print(f"获取群管理员错误: {e}")
        return []


def group_keyword_get(group_id: int) -> List[str]:
    """
    获取指定群组的关键词列表（从JSON字符串解析）。

    Args:
        group_id: 群组ID

    Returns:
        List[str]: 关键词列表，如果解析失败或无数据则返回空列表
    """
    try:
        command = "SELECT keywords FROM groups WHERE group_id = ?"
        result = query_db(command, (group_id,))
        return json.loads(result[0][0]) if result and result[0][0] else []
    except Exception as e:
        print(f"获取群组关键词错误: {e}")
        return []


def group_keyword_set(group_id: int, keywords: List[str]) -> bool:
    """
    设置指定群组的关键词列表（序列化为JSON字符串存储）。

    Args:
        group_id: 群组ID
        keywords: 关键词列表

    Returns:
        bool: 操作是否成功
    """
    try:
        keywords_str = json.dumps(keywords, ensure_ascii=False)
        command = "UPDATE groups SET keywords = ? WHERE group_id = ?"
        result = revise_db(command, (keywords_str, group_id))
        return result > 0
    except Exception as e:
        print(f"设置群组关键词错误: {e}")
        return False


def group_info_create(group_id: int) -> bool:
    """
    为指定group_id创建一条新的群组记录，使用默认API、角色和预设。

    Args:
        group_id: 群组ID

    Returns:
        bool: 操作是否成功
    """
    command = "INSERT INTO groups (group_id, api, char, preset) VALUES (?, ?, ?, ?)"
    result = revise_db(command, (group_id, DEFAULT_API, DEFAULT_CHAR, DEFAULT_PRESET))
    return result > 0


def group_dialog_add(msg_id: int, group_id: int) -> bool:
    """
    在group_dialogs表中添加一条群聊消息记录。

    Args:
        msg_id: 消息ID
        group_id: 群组ID

    Returns:
        bool: 操作是否成功
    """
    command = "INSERT INTO group_dialogs (msg_id, group_id) VALUES (?, ?)"
    result = revise_db(command, (msg_id, group_id))
    return result > 0


def group_dialog_update(msg_id: int, field: str, value: Any, group_id: int) -> bool:
    """
    更新group_dialogs表中指定消息的指定字段。

    Args:
        msg_id: 消息ID
        field: 要更新的字段名
        value: 新的字段值
        group_id: 群组ID

    Returns:
        bool: 操作是否成功
    """
    # print(f"正在把群{group_id}的消息{msg_id}的{field}字段更新为{value}")
    command = f"UPDATE group_dialogs SET {field} = ? WHERE msg_id = ? AND group_id = ?"
    result = revise_db(command, (value, msg_id, group_id))
    return result > 0


def group_dialog_get(
    group_id: int, num: int
) -> List[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]]:
    """
    获取指定group_id的最新num条群聊消息，按msg_id降序排序。

    Args:
        group_id: 群组ID
        num: 获取消息数量

    Returns:
        List[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]]: 
            消息列表，每个元组包含(msg_text, msg_user_name, processed_response, create_at)
    """
    command = """
              SELECT msg_text, msg_user_name, processed_response, create_at
              FROM (SELECT msg_text, msg_user_name, processed_response, create_at, msg_id \
                    FROM group_dialogs \
                    WHERE group_id = ? \
                    ORDER BY msg_id DESC \
                    LIMIT ?) sub
              ORDER BY msg_id ASC \
              """
    result = query_db(command, (group_id, num))
    print(f"Querying with group_id={group_id}, num={num}, result={result}")  # 调试日志
    return result if result else []


def group_info_update(group_id: int, field: str, value: Any, increase=False) -> bool:
    """
    更新 `groups` 表中指定群组的指定字段。

    Args:
        group_id: 群组ID
        field: 要更新的字段名
        value: 新的字段值
        increase: 是否为增量更新，默认为False

    Returns:
        bool: 操作是否成功
    """
    # print(f"正在把{group_id}的{field}修改为{value}，递增{increase}")
    if not increase:
        command = f"UPDATE groups SET {field} = ? WHERE group_id = ?"
    else:
        command = (
            f"UPDATE groups SET {field} = COALESCE({field}, 0)+? WHERE group_id = ?"
        )
    result = revise_db(command, (value, group_id))
    return result > 0


def group_rate_get(group_id: int) -> float:
    """
    获取指定群组的回复频率(rate)。

    Args:
        group_id: 群组ID

    Returns:
        float: 回复频率，如果未设置或查询失败则返回配置中的默认值
    """
    command = f"SELECT rate from groups where group_id = ?"
    result = query_db(command, (group_id,))
    default_rate = get_config("group.default_rate", 0.05)
    return (
        result[0][0]
        if result and result[0] and result[0][0] is not None
        else default_rate
    )


def group_disabled_topics_get(group_id: int) -> List[str]:
    """
    获取指定群组的禁用话题列表（从JSON字符串解析）。

    Args:
        group_id: 群组ID

    Returns:
        List[str]: 禁用话题列表，如果解析失败或无数据则返回空列表（表示没有禁用话题）
    """
    try:
        command = "SELECT disabled_topics FROM groups WHERE group_id = ?"
        result = query_db(command, (group_id,))
        return json.loads(result[0][0]) if result and result[0][0] else []
    except Exception as e:
        print(f"获取群组禁用话题错误: {e}")
        return []


def group_disabled_topics_set(group_id: int, topics: List[str]) -> bool:
    """
    设置指定群组的禁用话题列表（序列化为JSON字符串存储）。

    Args:
        group_id: 群组ID
        topics: 禁用话题列表

    Returns:
        bool: 操作是否成功
    """
    try:
        topics_str = json.dumps(topics, ensure_ascii=False)
        command = "UPDATE groups SET disabled_topics = ? WHERE group_id = ?"
        result = revise_db(command, (topics_str, group_id))
        return result > 0
    except Exception as e:
        print(f"设置群组禁用话题错误: {e}")
        return False


def user_sign_info_get(user_id: int) -> dict:
    """
    获取指定用户的签到信息。

    Args:
        user_id: 用户ID

    Returns:
        dict: 用户签到信息字典，包含user_id、last_sign、sign_count、frequency字段
    """
    command = (
        f"SELECT user_id,last_sign,sign_count,frequency from user_sign where user_id =?"
    )
    result = query_db(command, (user_id,))
    if result:
        return dict(zip(["user_id", "last_sign", "sign_count", "frequency"], result[0]))
    else:
        return {"user_id": user_id, "last_sign": 0, "sign_count": 0, "frequency": 0}


def user_sign_info_create(user_id: int) -> bool:
    """
    为指定用户创建签到信息记录。

    Args:
        user_id: 用户ID

    Returns:
        bool: 操作是否成功
    """
    command = f"INSERT INTO user_sign (user_id,last_sign,sign_count,frequency) VALUES (?,?,?,?)"
    time = str(datetime.datetime.now())
    default_frequency = get_config("sign.default_frequency", 50)
    result = revise_db(command, (user_id, time, 1, default_frequency))
    return result > 0


def user_sign(user_id: int) -> bool:
    """
    用户签到，更新签到时间和连续签到天数。

    Args:
        user_id: 用户ID

    Returns:
        bool: 操作是否成功
    """
    default_frequency = get_config("sign.default_frequency", 50)
    max_frequency = get_config("sign.max_frequency", 100)
    command = f"UPDATE user_sign SET last_sign =?,sign_count = COALESCE(sign_count, 0)+1,frequency = MIN(COALESCE(frequency, 0) + {default_frequency}, {max_frequency}) WHERE user_id =?"
    time = str(datetime.datetime.now())
    result = revise_db(command, (time, user_id))
    return result > 0


def user_sign_info_update(user_id: int, field: str, value: Any) -> bool:
    """
    更新用户签到信息的指定字段。

    Args:
        user_id: 用户ID
        field: 要更新的字段名
        value: 新的字段值

    Returns:
        bool: 操作是否成功
    """
    command = f"UPDATE user_sign SET {field} = COALESCE({field}, 0)+? WHERE user_id =?"
    result = revise_db(command, (value, user_id))
    return result > 0


# 应用退出时关闭所有数据库连接
def close_all_connections():
    """关闭连接池中的所有数据库连接。应在应用退出时调用。"""
    db_pool.close_all()
