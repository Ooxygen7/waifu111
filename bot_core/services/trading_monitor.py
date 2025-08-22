import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from telegram import Bot
from telegram.error import TelegramError
from bot_core.services.trading_service import trading_service
from utils.config_utils import get_config
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class TradingMonitor:
    """
    交易监控服务
    负责定期检查价格更新和强平监控
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.monitor_task = None
        
    async def start_monitoring(self):
        """启动监控服务"""
        if self.is_running:
            logger.warning("交易监控已在运行中")
            return
            
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("交易监控服务已启动")
        
    async def stop_monitoring(self):
        """停止监控服务"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("交易监控服务已停止")
        
    async def _monitor_loop(self):
        """监控主循环"""
        while self.is_running:
            try:
                # 检查强平
                await self._check_liquidations()
                
                # 等待10秒
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(10)  # 出错后等待10秒再继续
                
    async def _check_liquidations(self):
        """检查并处理强平"""
        try:
            liquidated_positions = await trading_service.check_liquidations()
            
            for position in liquidated_positions:
                await self._send_liquidation_notification(position)
                
        except Exception as e:
            logger.error(f"检查强平失败: {e}")
            
    async def _send_liquidation_notification(self, position: Dict):
        """发送强平通知"""
        try:
            user_id = position['user_id']
            group_id = position['group_id']
            symbol = position['symbol']
            side = position['side']
            size = position['size']
            liquidation_price = position['liquidation_price']
            current_price = position['current_price']
            
            # 构造强平通知消息
            message = (
                f"🚨 强平通知 🚨\n\n"
                f"@{user_id} 您的仓位已被强制平仓！\n\n"
                f"📊 交易对: {symbol}\n"
                f"📈 方向: {side.upper()}\n"
                f"💰 仓位大小: {size:.2f} USDT\n"
                f"⚡ 强平价: {liquidation_price:.4f}\n"
                f"💸 触发价: {current_price:.4f}\n\n"
                f"💔 您的账户余额已清零，请使用 /begging 领取救济金重新开始交易。"
            )
            
            # 发送到群组
            await self.bot.send_message(
                chat_id=group_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"强平通知已发送: 用户{user_id} 群组{group_id} {symbol} {side}")
            
        except TelegramError as e:
            logger.error(f"发送强平通知失败: {e}")
        except Exception as e:
            logger.error(f"处理强平通知失败: {e}")

# 全局监控实例
trading_monitor = None

def get_trading_monitor(bot: Bot = None) -> TradingMonitor:
    """获取交易监控实例"""
    global trading_monitor
    if trading_monitor is None and bot:
        trading_monitor = TradingMonitor(bot)
    return trading_monitor