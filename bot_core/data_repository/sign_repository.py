"""
sign_repository.py - 用户签到表(user_sign)相关的CRUD操作
"""

import datetime
import logging
from typing import Any

from utils.db_utils import query_db, revise_db, get_config
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class SignRepository:
    """用户签到表相关的数据库操作"""

    @staticmethod
    def user_sign_info_get(user_id: int) -> dict:
        """
        获取指定用户的签到信息

        Args:
            user_id: 用户ID

        Returns:
            dict: {
                "success": bool,
                "data": dict (user_id, last_sign, sign_count, frequency),
                "error": str (如果有错误)
            }
        """
        try:
            command = "SELECT user_id, last_sign, sign_count, frequency FROM user_sign WHERE user_id = ?"
            result = query_db(command, (user_id,))

            if result:
                sign_info = dict(zip(["user_id", "last_sign", "sign_count", "frequency"], result[0]))
                return {
                    "success": True,
                    "data": sign_info
                }
            else:
                # 如果用户没有签到记录，返回默认值
                return {
                    "success": True,
                    "data": {
                        "user_id": user_id,
                        "last_sign": 0,
                        "sign_count": 0,
                        "frequency": 0
                    }
                }
        except Exception as e:
            logger.error(f"获取用户签到信息失败: {e}")
            return {
                "success": False,
                "data": {
                    "user_id": user_id,
                    "last_sign": 0,
                    "sign_count": 0,
                    "frequency": 0
                },
                "error": str(e)
            }

    @staticmethod
    def user_sign_info_create(user_id: int) -> dict:
        """
        为指定用户创建签到信息记录

        Args:
            user_id: 用户ID

        Returns:
            dict: {
                "success": bool,
                "error": str (如果有错误)
            }
        """
        try:
            time = str(datetime.datetime.now())
            default_frequency = get_config("sign.default_frequency", 50)
            command = "INSERT INTO user_sign (user_id, last_sign, sign_count, frequency) VALUES (?, ?, ?, ?)"
            result = revise_db(command, (user_id, time, 1, default_frequency))

            return {
                "success": result > 0
            }
        except Exception as e:
            logger.error(f"为用户创建签到信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def user_sign(user_id: int) -> dict:
        """
        用户签到，更新签到时间和连续签到天数

        Args:
            user_id: 用户ID

        Returns:
            dict: {
                "success": bool,
                "error": str (如果有错误)
            }
        """
        try:
            default_frequency = get_config("sign.default_frequency", 50)
            max_frequency = get_config("sign.max_frequency", 100)
            time = str(datetime.datetime.now())

            command = f"UPDATE user_sign SET last_sign = ?, sign_count = COALESCE(sign_count, 0) + 1, frequency = MIN(COALESCE(frequency, 0) + {default_frequency}, {max_frequency}) WHERE user_id = ?"
            result = revise_db(command, (time, user_id))

            return {
                "success": result > 0
            }
        except Exception as e:
            logger.error(f"用户签到失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def user_sign_info_update(user_id: int, field: str, value: Any) -> dict:
        """
        更新用户签到信息的指定字段

        Args:
            user_id: 用户ID
            field: 要更新的字段名
            value: 新的字段值

        Returns:
            dict: {
                "success": bool,
                "error": str (如果有错误)
            }
        """
        try:
            command = f"UPDATE user_sign SET {field} = COALESCE({field}, 0) + ? WHERE user_id = ?"
            result = revise_db(command, (value, user_id))

            return {
                "success": result > 0
            }
        except Exception as e:
            logger.error(f"更新用户签到信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }