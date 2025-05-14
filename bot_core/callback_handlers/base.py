# base.py
from abc import ABC, abstractmethod
from typing import Callable

from telegram import Update
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

class CallbackMeta:
    def __init__(self,
                 name: str,
                 callback_type: str,  # 'private'/'group'/'admin'
                 group_admin_required: bool = False,
                 trigger: str = '',
                 enabled: bool = True):
        self.name = name
        self.callback_type = callback_type
        self.group_admin_required = group_admin_required
        self.trigger = trigger
        self.enabled = enabled

class BaseCallback(ABC):
    meta: CallbackMeta

    def __init__(self):
        if not hasattr(self, 'meta'):
            raise NotImplementedError('Callback must define meta attribute')
        self.handle_callback = self._build_handler()

    def _build_handler(self) -> Callable:
        func = self.handle_callback

        # 自动添加装饰器
        if self.meta.group_admin_required:
            func = Decorators.group_admin_required(func)

        return func

    @abstractmethod
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理回调的抽象方法。

        Args:
            update (Update): Telegram 更新对象。
            context (ContextTypes.DEFAULT_TYPE):  上下文对象.
            data (str): 回调数据，通常是 callback_data 的一部分。
        """
        pass
