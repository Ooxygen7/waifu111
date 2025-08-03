import random
from typing import Optional, List
import utils.db_utils as db
from bot_core.models import User, Conversation, DialogMessage

class UserRepository:
    """
    负责所有与用户相关的数据库操作。
    它封装了对 db_utils 的直接调用，并返回 User 数据模型。
    """

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        通过用户ID获取一个完整的用户对象。

        Args:
            user_id: 用户的Telegram ID。

        Returns:
            一个包含所有用户信息的 User 对象，如果用户不存在则返回 None。
        """
        if not db.user_config_check(user_id):
            return None

        # 从不同表中获取数据
        user_info = db.user_info_get(user_id)
        user_config = db.user_config_get(user_id)
        sign_info = db.user_sign_info_get(user_id)

        # 将多个字典合并到一个字典中，以便 pydantic 模型可以一次性解析
        # 注意：键名需要与 User 模型中的字段名或别名匹配
        combined_data = {
            'uid': user_id,
            **user_info,
            **user_config,
            **sign_info
        }
        
        # 使用 pydantic 模型进行数据验证和转换
        return User.model_validate(combined_data)

    def create_user(self, user_id: int, first_name: str, last_name: str, user_name: str) -> Optional[User]:
        """
        创建一个新用户，并返回完整的 User 对象。

        Args:
            user_id: 用户ID
            first_name: 用户的 first_name
            last_name: 用户的 last_name
            user_name: 用户的 username

        Returns:
            创建成功后返回完整的 User 对象，否则返回 None。
        """
        if db.user_config_check(user_id):
            return self.get_user_by_id(user_id)

        # 创建基础用户信息和配置
        if not db.user_info_create(user_id, first_name, last_name, user_name):
            return None
        if not db.user_config_create(user_id):
            return None
        
        # 创建成功后，获取并返回完整的用户对象
        return self.get_user_by_id(user_id)

    def get_or_create_user(self, user_id: int, first_name: str, last_name: str, user_name: str) -> Optional[User]:
        """
        获取一个用户，如果不存在则创建。

        这是对 get_user_by_id 和 create_user 的便捷封装。
        """
        user = self.get_user_by_id(user_id)
        if user:
            return user
        return self.create_user(user_id, first_name, last_name, user_name)

    def update_user(self, user: User) -> bool:
        """
        使用 User 模型对象更新数据库中的用户信息。
        注意：这个方法目前只更新 users 表中的字段。
        可以根据需要扩展以更新 user_config 等。
        """
        # 更新 users 表
        db.user_info_update(user.id, 'first_name', user.first_name)
        db.user_info_update(user.id, 'last_name', user.last_name)
        db.user_info_update(user.id, 'user_name', user.user_name)
        
        # 更新 user_config 表
        db.user_config_arg_update(user.id, 'nick', user.nick)
        db.user_config_arg_update(user.id, 'api', user.api)
        db.user_config_arg_update(user.id, 'char', user.character)
        db.user_config_arg_update(user.id, 'preset', user.preset)
        db.user_config_arg_update(user.id, 'stream', "yes" if user.stream else "no")
        
        return True


class ConversationRepository:
    """
    负责所有与会话相关的数据库操作。
    """
    def get_conversation_by_id(self, conv_id: int) -> Optional[Conversation]:
        """
        通过会话ID获取一个完整的会话对象，包括对话历史。
        """
        # 1. 获取会话主表信息
        conv_command = "SELECT conv_id, user_id, character, preset, delete_mark, create_at, update_at FROM conversations WHERE conv_id = ?"
        conv_result = db.query_db(conv_command, (conv_id,))
        if not conv_result:
            return None

        conv_row = conv_result[0]
        conv_data = {
            "conv_id": conv_row[0],
            "user_id": conv_row[1],
            "character": conv_row[2],
            "preset": conv_row[3],
            "delete_mark": conv_row[4] == 'yes',
            "created_at": conv_row[5],
            "updated_at": conv_row[6]
        }

        # 2. 获取对话摘要
        summaries = db.dialog_summary_get(conv_id) or []

        # 3. 合并基础数据并创建模型
        combined_data = {
            **conv_data,
            'summaries': summaries,
            'turns': db.dialog_turn_get(conv_id, 'private')
        }
        conversation = Conversation.model_validate(combined_data)

        # 4. 获取并填充对话历史
        dialog_command = "SELECT role, turn_order, raw_content, processed_content, msg_id, created_at FROM dialogs WHERE conv_id = ? ORDER BY turn_order ASC"
        dialog_results = db.query_db(dialog_command, (conv_id,))
        
        if dialog_results:
            history = []
            for row in dialog_results:
                msg_data = {
                    "role": row[0],
                    "turn": row[1],
                    "raw_content": row[2],
                    "processed_content": row[3],
                    "message_id": row[4],
                    "created_at": row[5]
                }
                history.append(DialogMessage.model_validate(msg_data))
            conversation.history = history

        return conversation

    def create_private_conversation(self, user: User) -> Optional[Conversation]:
        """
        为指定用户创建一个新的私人会话。
        """
        max_attempts = 5
        for _ in range(max_attempts):
            new_conv_id = random.randint(10000000, 99999999)
            if (db.conversation_private_create(new_conv_id, user.id, user.character, user.preset) and
                    db.user_config_arg_update(user.id, 'conv_id', new_conv_id)):
                db.user_info_update(user.id, 'conversations', 1, True)
                return self.get_conversation_by_id(new_conv_id)
        return None

    def add_message(self, conv_id: int, role: str, turn: int, raw_content: str, processed_content: str, message_id: Optional[int]):
        """
        向指定的私人会话中添加一条消息。
        """
        db.dialog_content_add(conv_id, role, turn, raw_content, processed_content, message_id, 'private')

    def delete_message_by_id(self, message_id: int) -> bool:
        """
        通过消息ID从数据库中删除一条对话记录。

        Args:
            message_id: 要删除的消息的ID。

        Returns:
            如果删除成功则返回 True，否则返回 False。
        """
        command = "DELETE FROM dialogs WHERE msg_id = ?"
        # revise_db 返回受影响的行数，大于0表示成功
        return db.revise_db(command, (message_id,)) > 0