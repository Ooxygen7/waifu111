"""
user_profiles_repository.py - 用户画像表(user_profiles)相关的CRUD操作
"""

import datetime
import logging
from typing import List, Optional

from utils.db_utils import query_db, revise_db
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class UserProfilesRepository:
    """用户画像表相关的数据库操作"""

    @staticmethod
    def user_profile_get(userid: int) -> dict:
        """
        获取用户的完整个人资料信息

        Args:
            userid: 用户ID

        Returns:
            dict: {
                "success": bool,
                "data": List[dict] (包含用户画像的字典列表),
                "error": str (如果有错误)
            }
        """
        try:
            command = "SELECT * FROM user_profiles WHERE user_id = ?"
            result = query_db(command, (userid,))

            if result:
                profiles = []
                for i in result:
                    profiles.append({
                        "group_id": i[1],
                        "user_profile": str(i[2]),
                    })
                return {
                    "success": True,
                    "data": profiles
                }
            else:
                return {
                    "success": True,
                    "data": []
                }
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}")
            return {
                "success": False,
                "data": [],
                "error": str(e)
            }

    @staticmethod
    def user_has_profile(user_id: int) -> dict:
        """
        检查用户是否存在用户画像

        Args:
            user_id: 用户ID

        Returns:
            dict: {
                "success": bool,
                "data": bool (是否存在用户画像),
                "error": str (如果有错误)
            }
        """
        try:
            command = "SELECT 1 FROM user_profiles WHERE user_id = ? LIMIT 1"
            result = query_db(command, (user_id,))

            return {
                "success": True,
                "data": bool(result)
            }
        except Exception as e:
            logger.error(f"检查用户是否存在画像失败: {e}")
            return {
                "success": False,
                "data": False,
                "error": str(e)
            }

    @staticmethod
    def group_has_profile(group_id: int) -> dict:
        """
        检查群组是否存在用户画像

        Args:
            group_id: 群组ID

        Returns:
            dict: {
                "success": bool,
                "data": bool (是否存在用户画像),
                "error": str (如果有错误)
            }
        """
        try:
            command = "SELECT 1 FROM user_profiles WHERE group_id = ? LIMIT 1"
            result = query_db(command, (group_id,))

            return {
                "success": True,
                "data": bool(result)
            }
        except Exception as e:
            logger.error(f"检查群组是否存在画像失败: {e}")
            return {
                "success": False,
                "data": False,
                "error": str(e)
            }

    @staticmethod
    def group_profiles_get(group_id: int) -> dict:
        """
        获取指定群组的所有用户画像

        Args:
            group_id: 群组ID

        Returns:
            dict: {
                "success": bool,
                "data": List[dict] (用户画像列表，每个包含user_id, profile_json, user_name, first_name, last_name),
                "error": str (如果有错误)
            }
        """
        try:
            command = """
                SELECT up.user_id, up.profile_json, u.user_name, u.first_name, u.last_name
                FROM user_profiles up
                JOIN users u ON up.user_id = u.uid
                WHERE up.group_id = ?
            """
            results = query_db(command, (group_id,))

            profiles = []
            for row in results:
                profiles.append({
                    "user_id": row[0],
                    "profile_json": row[1],
                    "user_name": row[2],
                    "first_name": row[3],
                    "last_name": row[4]
                })

            return {
                "success": True,
                "data": profiles
            }
        except Exception as e:
            logger.error(f"获取群组用户画像失败: {e}")
            return {
                "success": False,
                "data": [],
                "error": str(e)
            }

    @staticmethod
    def group_profile_update_or_create(group_id: int, user_id: int, profile_json: str) -> dict:
        """
        更新或创建群组中的用户画像

        Args:
            group_id: 群组ID
            user_id: 用户ID
            profile_json: 用户画像JSON字符串

        Returns:
            dict: {
                "success": bool,
                "error": str (如果有错误)
            }
        """
        try:
            now = str(datetime.datetime.now())

            # 检查记录是否存在
            check_command = "SELECT 1 FROM user_profiles WHERE group_id = ? AND user_id = ?"
            exists = query_db(check_command, (group_id, user_id))

            if exists:
                # 更新
                command = "UPDATE user_profiles SET profile_json = ?, last_updated = ? WHERE group_id = ? AND user_id = ?"
                params = (profile_json, now, group_id, user_id)
            else:
                # 插入
                command = "INSERT INTO user_profiles (group_id, user_id, profile_json, last_updated) VALUES (?, ?, ?, ?)"
                params = (group_id, user_id, profile_json, now)

            result = revise_db(command, params)

            return {
                "success": result > 0
            }
        except Exception as e:
            logger.error(f"更新或创建群组用户画像失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }