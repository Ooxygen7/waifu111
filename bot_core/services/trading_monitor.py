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
        update_counter = 0
        while self.is_running:
            try:
                # 每30秒更新一次强平价格（3个循环周期）
                if update_counter % 3 == 0:
                    await self._update_liquidation_prices()
                
                # 检查强平
                await self._check_liquidations()
                
                update_counter += 1
                # 等待10秒
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(10)  # 出错后等待10秒再继续
                
    async def _update_liquidation_prices(self):
        """更新所有仓位的强平价格"""
        try:
            result = await trading_service.update_all_liquidation_prices()
            if result["success"]:
                logger.debug(f"已更新 {result['updated_count']}/{result['total_positions']} 个仓位的强平价格")
            else:
                logger.error(f"更新强平价格失败: {result.get('error', '未知错误')}")
        except Exception as e:
            logger.error(f"更新强平价格失败: {e}")
    
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
            from utils.db_utils import user_info_get
            
            user_id = position['user_id']
            group_id = position['group_id']
            symbol = position['symbol']
            side = position['side']
            size = position['size']
            floating_balance = position.get('floating_balance', 0)
            threshold = position.get('threshold', 200)
            leverage_ratio = position.get('leverage_ratio', 0)
            threshold_ratio = position.get('threshold_ratio', 0.2)
            
            # 获取用户信息以构造正确的用户提及
            user_info = user_info_get(user_id)
            if user_info and (user_info.get('first_name') or user_info.get('last_name')):
                user_display_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
                user_mention = f"[{user_display_name}](tg://user?id={user_id})"
            else:
                user_mention = f"[用户{user_id}](tg://user?id={user_id})"
            
            # 构造强平通知消息
            message = (
                f"🚨 强平通知 🚨\n\n"
                f"{user_mention} ，恭喜您！您的所有仓位已被清算！\n\n"
                f"📊 触发仓位: {symbol} {side.upper()}\n"
                f"⚖️ 杠杆倍数: {leverage_ratio:.2f}x\n"
                f"⚠️ 强平阈值: {threshold:.2f} USDT (本金的{threshold_ratio*100:.1f}%)\n\n"
                f"📉 当前余额: {floating_balance:.2f} USDT\n"
                f"💔 您的资金已成为流动性。\n"
                f"🆘 使用 /begging 可以领取救济金重新开始交易。"
            )
            
            # 发送到群组
            await self.bot.send_message(
                chat_id=group_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"强平通知已发送: 用户{user_id} 群组{group_id} 浮动余额{floating_balance:.2f} < 阈值{threshold:.2f}")
            
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