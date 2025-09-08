import logging
import asyncio
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes

# 导入插件基类
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bot_core.services.plugin_service import BasePlugin, PluginMeta

# 导入消息删除服务和实时仓位服务
from bot_core.services.messages import MessageDeletionService, RealTimePositionService
from utils.logging_utils import setup_logging

# 导入交易服务
from plugins.trading_services.order_service import order_service
from plugins.trading_services.account_service import account_service
from plugins.trading_services.position_service import position_service
from plugins.trading_services.analysis_service import analysis_service
from plugins.trading_services.loan_service import loan_service
from plugins.trading_services.price_service import price_service

setup_logging()
logger = logging.getLogger(__name__)


class TradingPlugin(BasePlugin):
    """交易插件
    
    该插件提供完整的模拟盘交易功能，包括：
    - 做多/做空开仓
    - 查看仓位
    - 平仓操作
    - 交易排行榜
    - 账户信息查询
    
    支持的命令:
        /long <交易对> <金额> - 做多开仓
        /short <交易对> <金额> - 做空开仓
        /position - 查看仓位
        /close [交易对] - 平仓
        /rank [all] - 查看排行榜
        /balance - 查看账户余额
    """
    
    def __init__(self):
        super().__init__()
        self.meta = PluginMeta(
            name="trading",
            version="1.0.0",
            description="模拟盘交易插件，提供完整的交易功能",
            author="CyberWaifu Bot Team",
            trigger="trading",  # 这个插件会处理多个命令
            command_type="group",
            menu_text="模拟盘交易",
            show_in_menu=False,  # 不在菜单中显示，因为有多个子命令
            menu_weight=30
        )
        
        # 支持的交易命令映射
        self.command_handlers = {
            'long': self.handle_long_command,
            'short': self.handle_short_command,
            'position': self.handle_position_command,
            'close': self.handle_close_command,
            'rank': self.handle_rank_command,
            'balance': self.handle_balance_command,
        }
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理交易相关命令"""
        if not update.message or not update.message.text:
            return
        
        # 解析命令
        command_text = update.message.text.strip()
        if not command_text.startswith('/'):
            return
        
        # 提取命令名称
        command_parts = command_text[1:].split()
        if not command_parts:
            return
        
        command_name = command_parts[0].split('@')[0]  # 处理@botname的情况
        
        # 查找对应的处理器
        handler = self.command_handlers.get(command_name)
        if handler:
            # 设置命令参数
            context.args = command_parts[1:]
            await handler(update, context)
    
    async def handle_long_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理做多命令"""
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ 用法错误！\n正确格式: \n"
                    "市价开仓: /long <交易对> <金额>\n"
                    "挂单开仓: /long <交易对> <金额>@<价格>\n"
                    "带止盈止损: /long <交易对> <金额>@<价格> tp@<止盈价> sl@<止损价>\n"
                    "批量开仓: /long <币种1> <币种2> <币种3> <金额>\n"
                    "例如: /long btc 100 或 /long btc 4000@100000 tp@120000 sl@90000"
                )
                return
            
            # 解析参数
            parsed_args = self._parse_trading_args(args)
            
            if not parsed_args['success']:
                await update.message.reply_text(f"❌ {parsed_args['error']}")
                return
            
            # 获取订单服务
            order_service = self.get_trading_service('order_service')
            if not order_service:
                await update.message.reply_text("❌ 交易服务不可用")
                return
            
            # 检查是否为批量开仓
            if parsed_args['is_batch']:
                results = []
                for symbol, amount in zip(parsed_args['symbols'], parsed_args['amounts']):
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "long", "open", amount
                    )
                    results.append(f"{symbol}: {result['message']}")
                
                response = "📈 批量做多结果:\n" + "\n".join(results)
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=response,
                    delay_seconds=30,
                    delete_user_message=True
                )
            else:
                # 单个开仓模式
                symbol = parsed_args['symbol']
                amount = parsed_args['amount']
                price = parsed_args.get('price')
                tp_price = parsed_args.get('tp_price')
                sl_price = parsed_args.get('sl_price')
                
                if price:
                    # 挂单模式
                    result = await order_service.create_limit_order(
                        user_id, group_id, f"{symbol}/USDT", "long", "open", amount, price
                    )
                else:
                    # 市价模式
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "long", "open", amount
                    )
                
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    delay_seconds=30,
                    delete_user_message=True
                )
        
        except Exception as e:
            logger.error(f"处理做多命令失败: {e}")
            await update.message.reply_text("❌ 处理命令失败，请稍后重试")
    
    async def handle_short_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理做空命令"""
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ 用法错误！\n正确格式: \n"
                    "市价开仓: /short <交易对> <金额>\n"
                    "挂单开仓: /short <交易对> <金额>@<价格>\n"
                    "带止盈止损: /short <交易对> <金额>@<价格> tp@<止盈价> sl@<止损价>\n"
                    "批量开仓: /short <币种1> <币种2> <币种3> <金额>\n"
                    "例如: /short btc 100 或 /short btc 4000@90000 tp@80000 sl@95000"
                )
                return
            
            # 解析参数
            parsed_args = self._parse_trading_args(args)
            
            if not parsed_args['success']:
                await update.message.reply_text(f"❌ {parsed_args['error']}")
                return
            
            # 获取订单服务
            order_service = self.get_trading_service('order_service')
            if not order_service:
                await update.message.reply_text("❌ 交易服务不可用")
                return
            
            # 检查是否为批量开仓
            if parsed_args['is_batch']:
                results = []
                for symbol, amount in zip(parsed_args['symbols'], parsed_args['amounts']):
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "short", "open", amount
                    )
                    results.append(f"{symbol}: {result['message']}")
                
                response = "📉 批量做空结果:\n" + "\n".join(results)
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=response,
                    delay_seconds=30,
                    delete_user_message=True
                )
            else:
                # 单个开仓模式
                symbol = parsed_args['symbol']
                amount = parsed_args['amount']
                price = parsed_args.get('price')
                
                if price:
                    # 挂单模式
                    result = await order_service.create_limit_order(
                        user_id, group_id, f"{symbol}/USDT", "short", "open", amount, price
                    )
                else:
                    # 市价模式
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "short", "open", amount
                    )
                
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    delay_seconds=30,
                    delete_user_message=True
                )
        
        except Exception as e:
            logger.error(f"处理做空命令失败: {e}")
            await update.message.reply_text("❌ 处理命令失败，请稍后重试")
    
    async def handle_position_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理查看仓位命令"""
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 获取仓位信息
            message = await self._get_enhanced_position_info(user_id, group_id)
            
            # 发送初始消息
            initial_message = await update.message.reply_text(
                RealTimePositionService._build_realtime_message(message, 120),
                parse_mode='HTML'
            )
            
            # 启动实时更新
            context.application.create_task(
                RealTimePositionService.start_realtime_update(
                    update=update,
                    context=context,
                    user_id=user_id,
                    group_id=group_id,
                    initial_message=initial_message
                )
            )
        
        except Exception as e:
            logger.error(f"查看仓位失败: {e}")
            await update.message.reply_text("❌ 获取仓位信息失败，请稍后重试")
    
    async def handle_close_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理平仓命令"""
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            
            # 获取仓位服务
            position_service = self.get_trading_service('position_service')
            if not position_service:
                await update.message.reply_text("❌ 仓位服务不可用")
                return
            
            # 如果没有参数，执行一键全平
            if len(args) == 0:
                result = await position_service.close_all_positions(user_id, group_id)
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    delay_seconds=30,
                    delete_user_message=True
                )
                return
            
            # 检查是否为批量平仓模式
            if len(args) >= 2:
                has_numeric = any(arg.replace('.', '').replace('u', '').replace('U', '').isdigit() for arg in args)
                if not has_numeric:
                    # 批量平仓模式
                    symbols = [arg.upper() for arg in args]
                    results = []
                    
                    for symbol in symbols:
                        try:
                            result = await position_service.close_position(
                                user_id, group_id, f"{symbol}/USDT"
                            )
                            results.append(f"{symbol}: {result['message']}")
                        except Exception as e:
                            results.append(f"{symbol}: 平仓失败 - {str(e)}")
                    
                    response = "📊 批量平仓结果:\n" + "\n".join(results)
                    await MessageDeletionService.send_and_schedule_delete(
                        update=update,
                        context=context,
                        text=response,
                        delay_seconds=30,
                        delete_user_message=True
                    )
                    return
            
            # 单个平仓模式
            symbol = args[0].upper()
            size = None
            
            if len(args) >= 2:
                try:
                    size = float(args[1].replace('u', '').replace('U', ''))
                except ValueError:
                    await update.message.reply_text("❌ 无效的平仓数量")
                    return
            
            result = await position_service.close_position(
                user_id, group_id, f"{symbol}/USDT", size=size
            )
            
            await MessageDeletionService.send_and_schedule_delete(
                update=update,
                context=context,
                text=result['message'],
                delay_seconds=30,
                delete_user_message=True
            )
        
        except Exception as e:
            logger.error(f"处理平仓命令失败: {e}")
            await update.message.reply_text("❌ 处理命令失败，请稍后重试")
    
    async def handle_rank_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理排行榜命令"""
        try:
            group_id = update.effective_chat.id
            
            # 检查是否有参数
            args = context.args
            is_global = len(args) > 0 and args[0].lower() == 'all'
            
            # 获取分析服务
            analysis_service = self.get_trading_service('analysis_service')
            if not analysis_service:
                await update.message.reply_text("❌ 分析服务不可用")
                return
            
            if is_global:
                # 获取全局排行榜数据
                result = await analysis_service.get_global_ranking_data()
                deadbeat_result = await analysis_service.get_global_deadbeat_ranking_data()
                title = "📊 <b>全球交易排行榜</b>\n"
            else:
                # 获取群组排行榜数据
                result = await analysis_service.get_ranking_data(group_id)
                deadbeat_result = await analysis_service.get_deadbeat_ranking_data(group_id)
                title = "📊 <b>群组交易排行榜</b>\n"
            
            if not result['success']:
                await update.message.reply_text("❌ 获取排行榜数据失败，请稍后重试")
                return
            
            # 构建排行榜消息
            message_parts = [title]
            
            # 盈利排行榜
            message_parts.append("💰 <b>盈利排行榜 TOP5</b>")
            if result['profit_ranking']:
                profit_lines = []
                for i, user in enumerate(result['profit_ranking'][:5], 1):
                    emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
                    profit_lines.append(
                        f"{emoji} {user['display_name']}: <b>{user['total_pnl']:.2f} USDT</b>"
                    )
                message_parts.extend(profit_lines)
            else:
                message_parts.append("暂无数据")
            
            message_parts.append("")
            
            # 亏损排行榜
            message_parts.append("💸 <b>亏损排行榜 TOP5</b>")
            if deadbeat_result.get('success') and deadbeat_result.get('deadbeat_ranking'):
                loss_lines = []
                for i, user in enumerate(deadbeat_result['deadbeat_ranking'][:5], 1):
                    emoji = ["💀", "☠️", "👻", "🔥", "💥"][i-1]
                    loss_lines.append(
                        f"{emoji} {user['display_name']}: <b>{user['total_pnl']:.2f} USDT</b>"
                    )
                message_parts.extend(loss_lines)
            else:
                message_parts.append("暂无数据")
            
            response = "\n".join(message_parts)
            await update.message.reply_text(response, parse_mode='HTML')
        
        except Exception as e:
            logger.error(f"处理排行榜命令失败: {e}")
            await update.message.reply_text("❌ 获取排行榜失败，请稍后重试")
    
    async def handle_balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理查看余额命令"""
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 获取账户服务
            account_service = self.get_trading_service('account_service')
            if not account_service:
                await update.message.reply_text("❌ 账户服务不可用")
                return
            
            # 获取账户信息
            result = await account_service.get_account_info(user_id, group_id)
            
            if result['success']:
                account = result['account']
                balance = account.get('balance', 0)
                
                # 获取浮动盈亏
                position_service = self.get_trading_service('position_service')
                if position_service:
                    positions_result = await position_service.get_positions(user_id, group_id)
                    if positions_result['success']:
                        total_unrealized_pnl = sum(
                            pos.get('unrealized_pnl', 0) for pos in positions_result['positions']
                        )
                        floating_balance = balance + total_unrealized_pnl
                        
                        message = (
                            f"💰 <b>账户信息</b>\n\n"
                            f"💵 可用余额: <b>{balance:.2f} USDT</b>\n"
                            f"📊 浮动盈亏: <b>{total_unrealized_pnl:+.2f} USDT</b>\n"
                            f"💎 浮动余额: <b>{floating_balance:.2f} USDT</b>"
                        )
                    else:
                        message = f"💰 <b>账户余额: {balance:.2f} USDT</b>"
                else:
                    message = f"💰 <b>账户余额: {balance:.2f} USDT</b>"
                
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text(f"❌ {result['message']}")
        
        except Exception as e:
            logger.error(f"处理余额命令失败: {e}")
            await update.message.reply_text("❌ 获取账户信息失败，请稍后重试")
    
    def _parse_trading_args(self, args):
        """解析交易参数，支持新的订单格式"""
        try:
            # 检查是否为批量模式
            if len(args) >= 3 and not '@' in ' '.join(args):
                try:
                    last_amount = float(args[-1].replace('u', '').replace('U', ''))
                    if last_amount > 0:
                        symbols = [arg.upper() for arg in args[:-1]]
                        amounts = [last_amount] * len(symbols)
                        return {
                            'success': True,
                            'is_batch': True,
                            'symbols': symbols,
                            'amounts': amounts
                        }
                except ValueError:
                    pass
            
            # 单个订单模式
            if len(args) < 2:
                return {'success': False, 'error': '参数不足'}
            
            symbol = args[0].upper()
            amount_str = args[1]
            
            # 解析金额和价格
            if '@' in amount_str:
                # 挂单模式
                amount_part, price_part = amount_str.split('@', 1)
                amount = float(amount_part.replace('u', '').replace('U', ''))
                price = float(price_part)
            else:
                # 市价模式
                amount = float(amount_str.replace('u', '').replace('U', ''))
                price = None
            
            # 解析止盈止损
            tp_price = None
            sl_price = None
            
            for arg in args[2:]:
                if arg.startswith('tp@'):
                    tp_price = float(arg[3:])
                elif arg.startswith('sl@'):
                    sl_price = float(arg[3:])
            
            return {
                'success': True,
                'is_batch': False,
                'symbol': symbol,
                'amount': amount,
                'price': price,
                'tp_price': tp_price,
                'sl_price': sl_price
            }
            
        except ValueError as e:
            return {'success': False, 'error': f'参数格式错误: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'解析失败: {str(e)}'}
    
    async def _get_enhanced_position_info(self, user_id: int, group_id: int) -> str:
        """获取增强的仓位信息"""
        try:
            # 获取账户服务和仓位服务
            account_service = self.get_trading_service('account_service')
            position_service = self.get_trading_service('position_service')
            
            if not account_service or not position_service:
                return "❌ 交易服务不可用"
            
            # 获取账户信息
            account_result = await account_service.get_account_info(user_id, group_id)
            if not account_result['success']:
                return f"❌ {account_result['message']}"
            
            # 获取仓位信息
            positions_result = await position_service.get_positions(user_id, group_id)
            if not positions_result['success']:
                return f"❌ {positions_result['message']}"
            
            account = account_result['account']
            positions = positions_result['positions']
            
            # 构建仓位信息消息
            balance = account.get('balance', 0)
            
            if not positions:
                return (
                    f"📊 <b>仓位信息</b>\n\n"
                    f"💰 账户余额: <b>{balance:.2f} USDT</b>\n"
                    f"📈 当前仓位: <b>无持仓</b>"
                )
            
            # 计算总的浮动盈亏
            total_unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
            floating_balance = balance + total_unrealized_pnl
            
            # 构建仓位列表
            position_lines = []
            for pos in positions:
                symbol = pos['symbol'].replace('/USDT', '')
                side = pos['side']
                size = pos['size']
                entry_price = pos['entry_price']
                current_price = pos.get('current_price', entry_price)
                unrealized_pnl = pos.get('unrealized_pnl', 0)
                
                side_emoji = "📈" if side == 'long' else "📉"
                pnl_emoji = "✅" if unrealized_pnl >= 0 else "❌"
                
                quantity = size / entry_price if entry_price > 0 else 0
                
                position_lines.append(
                    f"{side_emoji} <b>{symbol}</b> {side.upper()}\n"
                    f"   💰 数量: {quantity:.4f} {symbol}\n"
                    f"   📊 开仓价: {entry_price:.4f}\n"
                    f"   💵 当前价: {current_price:.4f}\n"
                    f"   {pnl_emoji} 盈亏: <b>{unrealized_pnl:+.2f} USDT</b>"
                )
            
            message = (
                f"📊 <b>仓位信息</b>\n\n"
                f"💰 账户余额: <b>{balance:.2f} USDT</b>\n"
                f"📊 浮动盈亏: <b>{total_unrealized_pnl:+.2f} USDT</b>\n"
                f"💎 浮动余额: <b>{floating_balance:.2f} USDT</b>\n\n"
                f"📈 <b>持仓详情:</b>\n\n" + "\n\n".join(position_lines)
            )
            
            return message
            
        except Exception as e:
            logger.error(f"获取仓位信息失败: {e}")
            return "❌ 获取仓位信息失败，请稍后重试"


# 创建插件实例
trading_plugin = TradingPlugin()