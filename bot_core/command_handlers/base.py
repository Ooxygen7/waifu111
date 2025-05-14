from abc import ABC, abstractmethod
from typing import Callable

from telegram.ext import ContextTypes

from bot_core.public_functions.decorators import Decorators


class CommandMeta:
    def __init__(self,
                 name: str,
                 command_type: str,  # 'private'/'group'/'admin'
                 group_admin_required: bool = False,
                 bot_admin_required: bool = False,
                 trigger: str = '',
                 menu_text: str = '',
                 show_in_menu: bool = True,
                 menu_weight: int = 0,
                 enabled: bool = True):
        self.name = name
        self.command_type = command_type
        self.group_admin_required = group_admin_required
        self.bot_admin_required = bot_admin_required
        self.trigger = trigger
        self.menu_text = menu_text
        self.show_in_menu = show_in_menu
        self.menu_weight = menu_weight
        self.enabled = enabled

class BaseCommand(ABC):
    meta: CommandMeta

    def __init__(self):
        if not hasattr(self, 'meta'):
            raise NotImplementedError('Command must define meta attribute')
        self.handler = self._build_handler()

    def _build_handler(self) -> Callable:
        func = self.handle
        # 自动添加装饰器
        if self.meta.bot_admin_required:
            func = Decorators.user_admin_required(func)
        if self.meta.command_type == 'group' and self.meta.group_admin_required:
            func = Decorators.group_admin_required(func)
        # 所有命令都加错误处理和用户信息更新
        func = Decorators.handle_command_errors(func)
        func = Decorators.ensure_user_info_updated(func)
        if self.meta.command_type == 'group':
            func = Decorators.ensure_group_info_updated(func)
        return func

    @abstractmethod
    async def handle(self, update, context: ContextTypes.DEFAULT_TYPE):
        pass

class BotCommandData:  # 为了区分，改名为BotCommandData
    def __init__(self, command, description):
        self.command = command
        self.description = description

    def __repr__(self):  # 方便调试
        return f"BotCommand(command='{self.command}', description='{self.description}')"