import logging
from typing import Dict, Any, Optional

from telegram import Update, User, Message, Chat
from bot_core.public_functions.error import BotError, DatabaseError
from utils import db_utils as db
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class UpdateParser:
    """
    一个用于解析Telegram Update对象的类，封装了信息提取和数据加载的逻辑。
    """

    def __init__(self, update: Update):
        self.update = update
        self.user: Optional[User] = None
        self.message: Optional[Message] = None
        self.chat: Optional[Chat] = None
        self.info: Dict[str, Any] = {}

        self._extract_base_objects()

    def _extract_base_objects(self):
        """从Update对象中提取核心对象（user, message, chat）。"""
        if self.update.message:
            self.message = self.update.message
            self.user = self.message.from_user
            self.chat = self.message.chat
        elif self.update.callback_query:
            callback = self.update.callback_query
            self.message = callback.message
            self.user = callback.from_user
            if self.message:
                self.chat = self.message.chat
        # 可以根据需要扩展以支持其他类型的更新，如 inline_query

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        解析Update对象，提取所有信息并从数据库加载相关数据。
        """
        if not self.user or not self.chat:
            logger.debug("Update对象不包含足够的信息进行解析。")
            return None

        try:
            self._extract_initial_info()

            if self.chat.type == 'private':
                self._load_private_chat_data()
            elif self.chat.type in ['group', 'supergroup']:
                self._load_group_chat_data()
            
            return self.info

        except Exception as e:
            logger.error(f"解析update信息时出错: {e}", exc_info=True)
            raise BotError(f"解析update信息错误: {e}")

    def _extract_initial_info(self):
        """提取用户、消息和聊天的基本信息。"""
        self.info.update(self._extract_user_info())
        if self.message:
            self.info.update(self._extract_message_info())
        self.info.update(self._extract_chat_info())

    def _load_private_chat_data(self):
        """加载私聊相关的数据（用户配置和详情）。"""
        user_id = self.user.id
        config = self._get_or_create_user_config(user_id)
        user_detail = db.user_info_get(user_id) or {}
        self.info.update(config)
        self.info.update(user_detail)

    def _load_group_chat_data(self):
        """加载群聊相关的数据（群组配置和会话ID）。"""
        group_id = self.chat.id
        user_id = self.user.id
        
        config = db.group_config_get(group_id)
        if config:
            self.info['api'] = config[0]
            self.info['char'] = config[1]
            self.info['preset'] = config[2]
            self.info['conv_id'] = db.conversation_group_get(group_id, user_id)
            self.info['need_update'] = db.group_check_update(group_id)
        else:
            self.info['need_update'] = True

    def _get_or_create_user_config(self, user_id: int) -> dict:
        """获取用户配置，如果不存在则创建。"""
        try:
            result = db.user_config_get(user_id)
            if not result:
                logger.info(f"为新用户 {user_id} 创建默认配置。")
                db.user_config_create(user_id)
                # 使用 self.info 中的 user_name
                if 'user_name' in self.info:
                    db.user_config_arg_update(user_id, 'nick', self.info['user_name'])
                result = db.user_config_get(user_id)
            return result or {}
        except Exception as e:
            logger.error(f"获取或创建用户配置失败, user_id: {user_id}, 错误: {e}")
            raise DatabaseError(f"获取用户配置失败: {e}")

    def _extract_user_info(self) -> Dict[str, Any]:
        """从User对象提取信息。"""
        if not self.user: return {}
        return {
            'user_id': self.user.id,
            'first_name': self.user.first_name or '',
            'last_name': self.user.last_name or '',
            'username': self.user.username or '',
            'user_name': (f"{self.user.first_name or ''} {self.user.last_name or ''}").strip()
        }

    def _extract_message_info(self) -> Dict[str, Any]:
        """从Message对象提取信息。"""
        if not self.message: return {}
        return {
            'message_id': self.message.message_id,
            'message_text': self.message.text or ''
        }

    def _extract_chat_info(self) -> Dict[str, Any]:
        """从Chat对象提取信息。"""
        if not self.chat: return {}
        info = {
            'chat_id': self.chat.id,
            'chat_type': self.chat.type
        }
        if self.chat.type in ['group', 'supergroup']:
            info['group_id'] = self.chat.id
            info['group_name'] = self.chat.title or ''
        return info


def update_info_get(update: Update) -> Optional[Dict[str, Any]]:
    """
    从Telegram的Update对象中提取并整合有用的信息。
    这是对 UpdateParser 的一个向后兼容的封装。

    Args:
        update (Update): Telegram的Update对象。

    Returns:
        dict: 包含用户、消息、群组等信息的字典。

    Raises:
        BotError: 解析Update信息时发生错误。
    """
    parser = UpdateParser(update)
    return parser.parse() or {}
