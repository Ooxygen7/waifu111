
import logging
from typing import Union

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from bot_core.services.utils.error import BotError
from utils import file_utils as file, db_utils as db
from bot_core.data_repository import UsersRepository as UserRepo
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class Inline:
    """
    用于处理和生成 Telegram 机器人菜单的类。
    该类封装了 API 列表、预设列表、对话列表和角色列表的生成逻辑。
    所有方法均为静态方法，可直接通过类名调用。
    """

    @staticmethod
    def print_api_list(tier: int) -> Union[str, InlineKeyboardMarkup]:
        """
        显示API列表，根据用户账户等级过滤API选项。

        Args:
            tier: 用户账户等级。

        Returns:
            Union[str, InlineKeyboardMarkup]: 如果没有符合条件的API返回提示，否则返回键盘标记。
        """
        try:
            api_list = file.load_config()['api']
            if not api_list:
                return "没有可用的api。"

            # 过滤API列表，只保留group小于或等于用户tier的API
            filtered_api_list = [api for api in api_list if api.get('group', 0) <= tier]

            if not filtered_api_list:
                return "没有符合您账户等级的可用api。"

            keyboard = [
                [InlineKeyboardButton(api['name'], callback_data=f"set_api_{api['name']}")]
                for api in filtered_api_list
            ]
            return InlineKeyboardMarkup(keyboard)
        except Exception as e:
            logger.error(f"获取API列表失败, 错误: {str(e)}")
            raise BotError(f"获取API列表失败: {str(e)}")

    @staticmethod
    def print_preset_list() -> Union[str, InlineKeyboardMarkup]:
        """
        显示预设列表。

        Returns:
            Union[str, InlineKeyboardMarkup]: 如果没有预设返回提示，否则返回键盘标记。
        """
        try:
            preset_list = file.load_prompts()
            if not preset_list:
                return "没有可用的预设。"
            keyboard = [
                [InlineKeyboardButton(preset['display'], callback_data=f"set_preset_{preset['name']}")]
                for preset in preset_list
            ]
            return InlineKeyboardMarkup(keyboard)
        except Exception as e:
            logger.error(f"获取预设列表失败, 错误: {str(e)}")
            raise BotError(f"获取预设列表失败: {str(e)}")

    @staticmethod
    def print_conversations(user_id: int, conv_type: str = 'load') -> Union[str, InlineKeyboardMarkup]:
        """
        显示用户对话列表。

        Args:
            user_id (int): Telegram用户id。
            conv_type (str): 操作类型，load或delete。

        Returns:
            Union[str, InlineKeyboardMarkup]: 如果没有对话返回提示，否则返回键盘标记。
        """
        try:
            # conv_list = db.user_conversations_get(user_id)
            conv_dict = UserRepo.user_conversations_get(user_id)
            if not conv_dict.get("success"):
                return f"获取对话列表出错！\n{conv_dict.get('error', '')}"
            else:
                conv_list = conv_dict.get("data", [])
            logger.info(f"获取用户对话列表(dialog), user_id: {user_id}")
            if not conv_list:
                return "没有可用的对话。"
            keyboard = [
                [InlineKeyboardButton(f"{conv[1]}： {conv[2]}",
                                      callback_data=f"{'set' if conv_type == 'load' else 'del'}_conv_{conv[0]}")]
                for conv in conv_list
            ]
            return InlineKeyboardMarkup(keyboard)
        except Exception as e:
            logger.error(f"获取用户对话列表失败, user_id: {user_id}, 错误: {str(e)}")
            raise BotError(f"获取用户对话列表失败: {str(e)}")

    @staticmethod
    def print_dialog_conversations(user_id: int) -> Union[str, InlineKeyboardMarkup]:
        """
        显示用户对话列表，用于dialog命令。显示格式为{角色名}-{对话轮数}-{更新时间}。

        Args:
            user_id (int): Telegram用户id。

        Returns:
            Union[str, InlineKeyboardMarkup]: 如果没有对话返回提示，否则返回键盘标记。
        """
        try:
            # conv_list = db.user_conversations_get_for_dialog(user_id)
            conv_dict = UserRepo.user_conversations_get(user_id)
            logger.debug(f"conv_dict: {conv_dict}")
            if not conv_dict.get("success"):
                return f"获取对话列表出错！\n{conv_dict.get('error', '')}"
            else:
                conv_list = conv_dict.get("data", [])
            logger.info(f"获取用户对话列表(dialog), user_id: {user_id}")
            if not conv_list:
                return "没有可用的对话。"
            
            keyboard = []
            for conv in conv_list:
                conv_id, character, turns, update_at, summary = conv
                # 格式化更新时间，只显示日期和时间
                try:
                    from datetime import datetime
                    update_time = datetime.fromisoformat(update_at).strftime("%m-%d %H:%M")
                except:
                    update_time = update_at[:16] if len(update_at) > 16 else update_at
                
                # 显示格式：{角色名}-{对话轮数}-{更新时间}
                display_text = f"{character.split('_')[0]}-{turns}轮-{update_time}"
                keyboard.append([
                    InlineKeyboardButton(display_text, callback_data=f"dialog_show_{conv_id}")
                ])
            
            return InlineKeyboardMarkup(keyboard)
        except Exception as e:
            logger.error(f"获取用户对话列表失败(dialog), user_id: {user_id}, 错误: {str(e)}")
            raise BotError(f"获取用户对话列表失败: {str(e)}")

    @staticmethod
    def print_char_list(operate_type: str, chat_type: str, _id: int, page: int = 1) -> Union[str, InlineKeyboardMarkup]:
        """
        筛选角色列表，支持分页显示。

        Args:
            operate_type (str): 操作类型，load或delete。
            chat_type (str): 消息类型，私聊或群聊。
            _id (int): 私聊或群聊id。
            page (int): 页码，从1开始。

        Returns:
            Union[str, InlineKeyboardMarkup]: 筛选后的inline按钮或提示字符串。
        """
        try:
            char_list = file.list_all_characters()
            filtered_chars = []
            
            # 筛选符合条件的角色
            for char in char_list:
                if operate_type == 'load' and chat_type == 'private':
                    if char.endswith("_public") or char.endswith(f"_{_id}"):
                        filtered_chars.append(char)
                elif operate_type == 'del' and chat_type == 'private':
                    if char.endswith(f"_{_id}"):
                        filtered_chars.append(char)
                elif operate_type == 'load' and chat_type == 'group':
                    if char.endswith("_public") or char.endswith(f"_{_id}"):
                        filtered_chars.append(char)
                elif operate_type == 'del' and chat_type == 'group':
                    if char.endswith(f"_{_id}"):
                        filtered_chars.append(char)

            if not filtered_chars:
                return "没有可操作的角色。"

            # 分页设置
            chars_per_page = 6
            total_chars = len(filtered_chars)
            total_pages = (total_chars + chars_per_page - 1) // chars_per_page
            
            # 确保页码在有效范围内
            page = max(1, min(page, total_pages))
            
            # 计算当前页的角色范围
            start_idx = (page - 1) * chars_per_page
            end_idx = min(start_idx + chars_per_page, total_chars)
            current_page_chars = filtered_chars[start_idx:end_idx]
            
            # 构建角色按钮
            keyboard = []
            for char in current_page_chars:
                if operate_type == 'load' and chat_type == 'private':
                    keyboard.append([InlineKeyboardButton(char.split('_')[0], callback_data=f"set_char_{char}")])
                elif operate_type == 'del' and chat_type == 'private':
                    keyboard.append([InlineKeyboardButton(char.split('_')[0], callback_data=f"del_char_{char}")])
                elif operate_type == 'load' and chat_type == 'group':
                    keyboard.append([InlineKeyboardButton(char.split('_')[0], callback_data=f"group_char_{char}_{_id}")])
                elif operate_type == 'del' and chat_type == 'group':
                    keyboard.append([InlineKeyboardButton(char.split('_')[0], callback_data=f"group_delchar_{char}_{_id}")])

            # 添加分页导航按钮
            if total_pages > 1:
                nav_buttons = []
                
                # 上一页按钮
                if page > 1:
                    prev_callback = f"char_page_{operate_type}_{chat_type}_{_id}_{page-1}"
                    nav_buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=prev_callback))
                
                # 页码显示
                nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
                
                # 下一页按钮
                if page < total_pages:
                    next_callback = f"char_page_{operate_type}_{chat_type}_{_id}_{page+1}"
                    nav_buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=next_callback))
                
                keyboard.append(nav_buttons)

            return InlineKeyboardMarkup(keyboard)
        except Exception as e:
            logger.error(f"获取角色列表失败, 错误: {str(e)}")
            raise BotError(f"获取角色列表失败: {str(e)}")

    @staticmethod
    def print_setting_menu() -> InlineKeyboardMarkup:
        """
        生成设置菜单的键盘标记。
        Returns:
            InlineKeyboardMarkup: 设置菜单的键盘标记。
        """
        keyboard = [
            [InlineKeyboardButton("对话设置", callback_data="setting_dialog")],
            [InlineKeyboardButton("角色及预设管理", callback_data="setting_char_preset")],
            [InlineKeyboardButton("状态查询", callback_data="setting_status")]
        ]
        return InlineKeyboardMarkup(keyboard)
