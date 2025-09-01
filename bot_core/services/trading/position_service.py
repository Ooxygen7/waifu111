"""
仓位服务
负责仓位管理、开仓、平仓、强平等仓位相关操作
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .account_service import account_service
from .price_service import price_service
from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class PositionService:
    """
    仓位管理服务
    处理仓位的完整生命周期：开仓、平仓、强平
    """

    def __init__(self):
        logger.info("仓位服务已初始化")

    def _get_price_precision(self, price: float) -> int:
        """根据价格大小返回小数位数"""
        if price >= 0.01:
            return 4  # > 0.01 USDT, 精确到4位小数
        else:
            return 8  # < 0.01 USDT, 精确到8位小数

    def _format_price(self, price: float) -> str:
        """根据价格大小格式化价格显示"""
        precision = self._get_price_precision(price)
        return f"{price:.{precision}f}"

    async def execute_order_position(self, order: Dict) -> Dict:
        """
        根据订单执行仓位操作

        Args:
            order: 订单对象

        Returns:
            执行结果
        """
        try:
            symbol = order["symbol"]
            direction = order["direction"]
            operation = order["operation"]
            volume = order["volume"]
            order_type = order["order_type"]

            user_id = order["user_id"]
            group_id = order["group_id"]

            # 获取实时价格（市价单必须使用最新价格，不依赖缓存）
            current_price = await price_service.get_real_time_price(symbol)
            if not current_price:
                return {
                    "success": False,
                    "message": f"无法获取 {symbol} 实时价格"
                }

            # 根据操作类型执行不同逻辑
            if operation == "addition":  # 加仓
                return await self._add_position(user_id, group_id, symbol, direction, volume, current_price)
            elif operation == "reduction":  # 减仓
                return await self._reduce_position(user_id, group_id, symbol, direction, volume, current_price)
            else:
                return {
                    "success": False,
                    "message": f"不支持的操作类型: {operation}"
                }

        except Exception as e:
            logger.error(f"执行订单仓位操作失败: {e}")
            return {
                "success": False,
                "message": f"仓位操作失败: {str(e)}"
            }

    async def _add_position(self, user_id: int, group_id: int, symbol: str,
                           direction: str, volume: float, entry_price: float) -> Dict:
        """
        加仓操作

        Args:
            user_id: 用户ID
            group_id: 群组ID
            symbol: 交易对
            direction: 方向 ('bid' 或 'ask')
            volume: 仓位大小
            entry_price: 开仓价格

        Returns:
            仓位操作结果
        """
        try:
            side = 'short' if direction == 'ask' else 'long'

            # 获取账户信息
            account = account_service.get_or_create_account(user_id, group_id)

            # 获取现有仓位
            position_result = TradingRepository.get_position(user_id, group_id, symbol, side)
            existing_position = position_result["position"]

            if existing_position:
                # 加仓操作
                return await self._add_to_existing_position(user_id, group_id, existing_position, volume, entry_price)
            else:
                # 新开仓位
                return await self._open_new_position(user_id, group_id, symbol, side, volume, entry_price)

        except Exception as e:
            logger.error(f"加仓操作失败: {e}")
            return {
                "success": False,
                "message": f"加仓操作失败: {str(e)}"
            }

    async def _add_to_existing_position(self, user_id: int, group_id: int,
                                      existing_position: Dict, volume: float, entry_price: float) -> Dict:
        """加仓到现有仓位"""
        try:
            symbol = existing_position['symbol']
            side = existing_position['side']
            old_size = existing_position['size']
            old_entry = existing_position['entry_price']

            # 获取账户信息
            account = account_service.get_or_create_account(user_id, group_id)

            # 计算所需保证金
            required_margin = volume / 100  # 100倍杠杆，1%保证金
            available_balance = account['balance'] - account.get('frozen_margin', 0.0)
            if available_balance < required_margin:
                return {
                    "success": False,
                    "message": f"保证金不足，需要: {required_margin:.2f} USDT，可用余额: {available_balance:.2f} USDT"
                }

            # 计算新平均开仓价格
            new_size = old_size + volume
            new_entry_price = ((old_size * old_entry) + (volume * entry_price)) / new_size

            # 获取用户所有仓位验证总仓位价值不超过杠杆限制
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if positions_result["success"] and positions_result["positions"]:
                total_position_value = 0.0
                total_unrealized_pnl = 0.0

                for pos in positions_result["positions"]:
                    pos_size = pos['size'] if pos['symbol'] == symbol and pos['side'] == side else pos['size']
                    total_position_value += pos_size

                    # 计算其他仓位的未实现盈亏
                    if pos['symbol'] != symbol or pos['side'] != side:
                        current_price = await price_service.get_current_price(pos['symbol'])
                        if current_price:
                            pnl = self._calculate_pnl(pos['entry_price'], current_price, pos['size'], pos['side'])
                            total_unrealized_pnl += pnl

                # 新仓位价值
                total_position_value += volume

                # 计算浮动余额
                floating_balance = account['balance'] + total_unrealized_pnl
                max_allowed_value = floating_balance * 100

                if total_position_value > max_allowed_value:
                    return {
                        "success": False,
                        "message": f"加仓失败！总仓位价值 {total_position_value:.2f} USDT 超过浮动余额的100倍限制 {max_allowed_value:.2f} USDT\n当前浮动余额: {floating_balance:.2f} USDT"
                    }

            # 计算新的强平价格
            liquidation_price = await self._calculate_liquidation_price(user_id, group_id, symbol, side, new_size, new_entry_price)

            # 更新仓位
            update_result = TradingRepository.update_position(
                user_id, group_id, symbol, side, new_size, new_entry_price, liquidation_price
            )

            if not update_result["success"]:
                return {"success": False, "message": "更新仓位失败"}

            # 添加交易记录
            TradingRepository.add_trading_history(
                user_id, group_id, 'open', symbol, side, volume, entry_price, 0.0
            )

            direction_emoji = "📈" if side == 'long' else "📉"
            coin_symbol = symbol.replace('/USDT', '')

            return {
                "success": True,
                "message": f"加仓成功！\n{direction_emoji} {coin_symbol} +{volume:.2f} USDT\n平均开仓价: {new_entry_price:.4f}\n总仓位: {new_size:.2f} USDT",
                "position": {
                    "symbol": symbol,
                    "side": side,
                    "size": new_size,
                    "entry_price": new_entry_price,
                    "liquidation_price": liquidation_price
                }
            }

        except Exception as e:
            logger.error(f"加仓到现有仓位失败: {e}")
            return {
                "success": False,
                "message": f"加仓失败: {str(e)}"
            }

    async def _open_new_position(self, user_id: int, group_id: int, symbol: str,
                                side: str, volume: float, entry_price: float) -> Dict:
        """
        开辟新仓位
        """
        try:
            # 获取账户信息
            account = account_service.get_or_create_account(user_id, group_id)

            # 获取用户所有现有仓位验证总仓位价值不超过杠杆限制
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if positions_result["success"] and positions_result["positions"]:
                total_position_value = volume
                total_unrealized_pnl = 0.0

                for pos in positions_result["positions"]:
                    total_position_value += pos['size']

                    # 计算现有仓位的未实现盈亏
                    current_price = await price_service.get_current_price(pos['symbol'])
                    if current_price:
                        pnl = self._calculate_pnl(pos['entry_price'], current_price, pos['size'], pos['side'])
                        total_unrealized_pnl += pnl

                # 计算浮动余额
                floating_balance = account['balance'] + total_unrealized_pnl
                max_allowed_value = floating_balance * 100

                if total_position_value > max_allowed_value:
                    return {
                        "success": False,
                        "message": f"开仓失败！总仓位价值 {total_position_value:.2f} USDT 超过浮动余额的100倍限制 {max_allowed_value:.2f} USDT\n当前浮动余额: {floating_balance:.2f} USDT"
                    }

            # 计算强平价格
            liquidation_price = await self._calculate_liquidation_price(user_id, group_id, symbol, side, volume, entry_price)

            # 创建新仓位
            create_result = TradingRepository.create_position(
                user_id, group_id, symbol, side, volume, entry_price, liquidation_price
            )

            if not create_result["success"]:
                return {"success": False, "message": "创建仓位失败"}

            # 添加交易记录
            TradingRepository.add_trading_history(
                user_id, group_id, 'open', symbol, side, volume, entry_price, 0.0
            )

            direction_emoji = "📈" if side == 'long' else "📉"
            coin_symbol = symbol.replace('/USDT', '')

            return {
                "success": True,
                "message": f"开仓成功！\n{direction_emoji} {coin_symbol} {volume:.2f} USDT\n开仓价: {entry_price:.4f}\n强平价: {liquidation_price:.4f}",
                "position": {
                    "id": create_result.get("position_id"),
                    "symbol": symbol,
                    "side": side,
                    "size": volume,
                    "entry_price": entry_price,
                    "liquidation_price": liquidation_price
                }
            }

        except Exception as e:
            logger.error(f"开辟新仓位失败: {e}")
            return {
                "success": False,
                "message": f"开仓失败: {str(e)}"
            }

    async def _reduce_position(self, user_id: int, group_id: int, symbol: str,
                              direction: str, volume: float, exit_price: float) -> Dict:
        """
        减仓操作（平仓）
        """
        try:
            side = 'short' if direction == 'ask' else 'long'

            # 获取现有仓位
            position_result = TradingRepository.get_position(user_id, group_id, symbol, side)
            if not position_result["success"] or not position_result["position"]:
                return {"success": False, "message": f"没有找到 {symbol} {side.upper()} 仓位"}

            position = position_result["position"]
            current_size = position['size']

            if volume >= current_size:
                # 全平仓位
                close_size = current_size
                close_result = await self._close_position_fully(user_id, group_id, position, exit_price)
            else:
                # 部分平仓
                close_size = volume
                close_result = await self._close_position_partially(user_id, group_id, position, close_size, exit_price)

            if close_result["success"]:
                # 记录交易历史
                pnl = close_result.get("pnl", 0.0)
                fee = close_result.get("fee", 0.0)
                net_pnl = pnl - fee

                TradingRepository.add_trading_history(
                    user_id, group_id, 'close', symbol, side, close_size, exit_price, net_pnl
                )

            return close_result

        except Exception as e:
            logger.error(f"减仓操作失败: {e}")
            return {
                "success": False,
                "message": f"减仓失败: {str(e)}"
            }

    async def _close_position_fully(self, user_id: int, group_id: int,
                                  position: Dict, exit_price: float) -> Dict:
        """
        全平仓位
        """
        try:
            symbol = position['symbol']
            side = position['side']
            size = position['size']
            entry_price = position['entry_price']

            # 计算盈亏（包含手续费）
            fee = size * 0.00035  # 万分之3.5
            pnl_before_fee = self._calculate_pnl(entry_price, exit_price, size, side)
            net_pnl = pnl_before_fee - fee

            # 删除仓位
            delete_result = TradingRepository.delete_position(user_id, group_id, symbol, side)
            if not delete_result["success"]:
                return {"success": False, "message": "删除仓位失败"}

            # 更新账户余额和统计
            account = account_service.get_or_create_account(user_id, group_id)
            new_balance = account['balance'] + net_pnl

            # 根据盈亏更新统计数据
            is_WIN = pnl_before_fee > 0
            profit_change = pnl_before_fee if pnl_before_fee > 0 else 0
            loss_change = abs(pnl_before_fee) if pnl_before_fee < 0 else 0

            balance_result = TradingRepository.update_account_balance(
                user_id, group_id, new_balance, pnl_before_fee, fee, is_WIN if pnl_before_fee != 0 else None
            )

            # 自动取消相关的止盈止损订单
            await self._cancel_related_stop_orders(user_id, group_id, symbol, side)

            direction_emoji = "📈" if side == 'long' else "📉"
            coin_symbol = symbol.replace('/USDT', '')

            pnl_color = "🟢" if net_pnl >= 0 else "🔴"

            return {
                "success": True,
                "message": f"平仓成功！\n{direction_emoji} {coin_symbol} -{size:.2f} USDT\n" +
                         f"{pnl_color} 平仓价: {exit_price:.4f}\n" +
                         f"盈亏: {pnl_before_fee:+.2f} USDT\n手续费: -{fee:.2f} USDT\n净盈亏: {net_pnl:+.2f} USDT",
                "pnl": pnl_before_fee,
                "fee": fee,
                "net_pnl": net_pnl
            }

        except Exception as e:
            logger.error(f"全平仓位失败: {e}")
            return {
                "success": False,
                "message": f"全平失败: {str(e)}"
            }
    
    async def _cancel_related_stop_orders(self, user_id: int, group_id: int, symbol: str, side: str):
        """取消与已平仓位相关的止盈止损订单"""
        try:
            # 动态导入order_service以避免循环导入
            from .order_service import order_service
            
            # 获取所有止盈止损订单
            tp_orders_result = TradingRepository.get_orders_by_type('tp', 'pending')
            sl_orders_result = TradingRepository.get_orders_by_type('sl', 'pending')
            
            if not tp_orders_result.get('success', False) or not sl_orders_result.get('success', False):
                logger.warning("获取止盈止损订单失败")
                return
            
            stop_orders = tp_orders_result.get('orders', []) + sl_orders_result.get('orders', [])
            
            if not stop_orders:
                return
            
            cancelled_count = 0
            
            # 遍历所有止盈止损订单，找到与已平仓位相关的订单
            for order in stop_orders:
                # 检查订单是否属于该用户和群组
                if order.get('user_id') != user_id or order.get('group_id') != group_id:
                    continue
                
                # 检查订单是否与平仓的交易对匹配
                if order.get('symbol') != symbol:
                    continue
                
                # 检查订单方向是否与已平仓位匹配
                order_side = 'long' if order.get('side') == 'sell' else 'short'  # 止盈止损订单的side与持仓方向相反
                
                if order_side == side:
                    # 取消该订单
                    cancel_result = order_service.cancel_order(order['order_id'])
                    if cancel_result.get('success'):
                        cancelled_count += 1
                        order_type_name = "止盈" if order['order_type'] == 'tp' else "止损"
                        logger.info(f"已自动取消{order_type_name}订单 {order['order_id']} (关联仓位: {symbol} {side.upper()})")
                    else:
                        logger.warning(f"取消{order_type_name}订单 {order['order_id']} 失败: {cancel_result.get('message')}")
            
            if cancelled_count > 0:
                logger.info(f"平仓操作自动取消了 {cancelled_count} 个相关的止盈止损订单")
                
        except Exception as e:
            logger.error(f"取消相关止盈止损订单失败: {e}")

    async def _close_position_partially(self, user_id: int, group_id: int,
                                      position: Dict, close_size: float, exit_price: float) -> Dict:
        """
        部分平仓
        """
        try:
            symbol = position['symbol']
            side = position['side']
            current_size = position['size']
            entry_price = position['entry_price']

            # 计算剩余仓位大小和新平均价格
            remaining_size = current_size - close_size
            remaining_value = remaining_size * entry_price

            # 计算手续费和平仓盈亏
            fee = close_size * 0.00035  # 万分之3.5
            pnl_before_fee = self._calculate_pnl(entry_price, exit_price, close_size, side)
            net_pnl = pnl_before_fee - fee

            # 计算新平均开仓价（剩余仓位的加权平均）
            new_entry_price = entry_price  # 部分平仓后，剩余仓位保持原有开仓价

            # 更新仓位
            liquidation_price = await self._calculate_liquidation_price(
                user_id, group_id, symbol, side, remaining_size, new_entry_price
            )

            update_result = TradingRepository.update_position(
                user_id, group_id, symbol, side, remaining_size, new_entry_price, liquidation_price
            )

            if not update_result["success"]:
                return {"success": False, "message": "更新仓位失败"}

            # 更新账户余额和统计
            account = account_service.get_or_create_account(user_id, group_id)
            new_balance = account['balance'] + net_pnl

            # 根据盈亏更新统计数据
            is_WIN = pnl_before_fee > 0
            profit_change = pnl_before_fee if pnl_before_fee > 0 else 0
            loss_change = abs(pnl_before_fee) if pnl_before_fee < 0 else 0

            balance_result = TradingRepository.update_account_balance(
                user_id, group_id, new_balance, pnl_before_fee, fee, is_WIN if pnl_before_fee != 0 else None
            )

            direction_emoji = "📈" if side == 'long' else "📉"
            coin_symbol = symbol.replace('/USDT', '')

            pnl_color = "🟢" if net_pnl >= 0 else "🔴"

            return {
                "success": True,
                "message": f"部分平仓成功！\n{direction_emoji} {coin_symbol} -{close_size:.2f} USDT (剩余: {remaining_size:.2f} USDT)\n" +
                         f"{pnl_color} 平仓价: {exit_price:.4f}\n" +
                         f"盈亏: {pnl_before_fee:+.2f} USDT\n手续费: -{fee:.2f} USDT\n净盈亏: {net_pnl:+.2f} USDT",
                "pnl": pnl_before_fee,
                "fee": fee,
                "net_pnl": net_pnl,
                "remaining_size": remaining_size
            }

        except Exception as e:
            logger.error(f"部分平仓失败: {e}")
            return {
                "success": False,
                "message": f"部分平仓失败: {str(e)}"
            }

    def _calculate_pnl(self, entry_price: float, exit_price: float, size: float, side: str) -> float:
        """计算盈亏"""
        if side == 'long':
            return (exit_price - entry_price) * (size / entry_price)
        else:
            return (entry_price - exit_price) * (size / entry_price)

    async def _calculate_liquidation_price(self, user_id: int, group_id: int, symbol: str,
                                         side: str, size: float, entry_price: float) -> float:
        """
        计算强平价格
        """
        try:
            # 获取用户账户
            account = account_service.get_or_create_account(user_id, group_id)

            # 获取用户所有仓位计算总仓位价值
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return entry_price * 0.8 if side == 'long' else entry_price * 1.2

            all_positions = positions_result["positions"]

            # 将当前仓位添加/合并到列表中
            current_position_found = False
            for pos in all_positions:
                if pos['symbol'] == symbol and pos['side'] == side:
                    pos['size'] = size
                    pos['entry_price'] = entry_price
                    current_position_found = True
                    break

            if not current_position_found:
                all_positions.append({'symbol': symbol, 'side': side, 'size': size, 'entry_price': entry_price})

            # 计算总仓位价值
            total_position_value = sum(p['size'] for p in all_positions)

            # 计算杠杆倍数
            leverage_ratio = total_position_value / account['balance'] if account['balance'] > 0 else float('inf')

            # 根据杠杆倍数动态计算强平阈值比例
            if leverage_ratio <= 1.0:
                threshold_ratio = 0.05  # 1倍以内，5%
            elif leverage_ratio >= 100.0:
                threshold_ratio = 0.20  # 100倍以上，20%
            else:
                # 1-100倍之间线性插值
                threshold_ratio = 0.05 + (leverage_ratio - 1.0) * 0.15 / 99.0

            liquidation_threshold = account['balance'] * threshold_ratio

            # 获取其他仓位的浮动盈亏
            other_positions_pnl = 0.0
            for pos in all_positions:
                if pos['symbol'] != symbol or pos['side'] != side:
                    current_price = await price_service.get_current_price(pos['symbol'])
                    if current_price:
                        pnl = self._calculate_pnl(pos['entry_price'], current_price, pos['size'], pos['side'])
                        other_positions_pnl += pnl

            # 计算所需的盈亏来触发强平
            # 强平条件: 余额 + 其他仓位盈亏 + 当前仓位盈亏 = 强平阈值
            target_pnl = liquidation_threshold - account['balance'] - other_positions_pnl

            if size <= 0:
                return entry_price

            # 计算强平价格
            if side == 'long':
                # 做多: target_pnl = (强平价 - 开仓价) / 开仓价 * 仓位大小
                liquidation_price = entry_price * (1 + target_pnl / size)
            else:
                # 做空: target_pnl = (开仓价 - 强平价) / 开仓价 * 仓位大小
                liquidation_price = entry_price * (1 - target_pnl / size)

            return max(liquidation_price, 0.0001)  # 确保价格为正

        except Exception as e:
            logger.error(f"计算强平价格失败: {e}")
            return entry_price * 0.8 if side == 'long' else entry_price * 1.2

    async def get_positions(self, user_id: int, group_id: int) -> List[Dict]:
        """获取用户仓位列表"""
        try:
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return []
            return positions_result["positions"]
        except Exception as e:
            logger.error(f"获取仓位列表失败: {e}")
            return []

    async def get_positions_summary(self, user_id: int, group_id: int) -> Dict:
        """获取用户仓位摘要"""
        try:
            account = account_service.get_or_create_account(user_id, group_id)

            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return {"success": False, "message": "获取仓位信息失败"}

            positions = positions_result["positions"]

            if not positions:
                account_info = (
                    f"🏦 浮动余额: {account['balance']:.2f} USDT({account['balance']:.2f}+0.00)\n"
                    f"📊 杠杆率: 0.00x(仓位总价值:0u)\n"
                    f"⚠️ 强平阈值: {account['balance'] * 0.05:.2f} USDT (5.0%)"
                )
                return {
                    'success': True,
                    'message': f"<blockquote>💼 账户信息\n\n{account_info}</blockquote>\n\n📋 当前无持仓"
                }

            total_unrealized_pnl = 0.0
            position_text = []

            # 计算总仓位价值和杠杆倍数
            total_position_value = sum(pos['size'] for pos in positions)
            leverage_ratio = total_position_value / account['balance'] if account['balance'] > 0 else 0

            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                size = pos['size']
                entry_price = pos['entry_price']
                liquidation_price = pos['liquidation_price']

                # 获取当前价格
                current_price = await price_service.get_current_price(symbol)

                # 计算未实现盈亏
                unrealized_pnl = self._calculate_pnl(entry_price, current_price, size, side)
                total_unrealized_pnl += unrealized_pnl

                # 计算盈亏百分比
                margin_used = size / 100  # 1%
                pnl_percent = (unrealized_pnl / margin_used) * 100 if margin_used > 0 else 0

                # 格式化
                side_emoji = "📈" if side == 'long' else "📉"
                coin_symbol = symbol.replace('/USDT', '')
                formatted_entry_price = f"{entry_price:.4f}"
                formatted_current_price = f"{current_price:.4f}"
                quantity = size / entry_price if entry_price > 0 else 0

                position_text.append(
                    f"{side_emoji}  {coin_symbol} |数量{quantity:.2f}| {unrealized_pnl:+.2f} USDT ({pnl_percent:+.2f}%)\n"
                    f"   开仓:{formatted_entry_price} |现价:{formatted_current_price}"
                )

            # 计算浮动余额和强平阈值
            floating_balance = account['balance'] + total_unrealized_pnl
            dynamic_threshold_ratio = self._calculate_dynamic_liquidation_threshold(leverage_ratio)
            liquidation_threshold = account['balance'] * dynamic_threshold_ratio

            # 风险警告
            risk_warning = ""
            if floating_balance < liquidation_threshold:
                risk_warning = "\n🚨 警告: 已触发强平条件！"
            elif floating_balance < liquidation_threshold * 1.1:
                risk_warning = "\n⚠️ 警告: 接近强平，请注意风险！"

            detailed_positions = "\n\n".join(position_text) if position_text else ""

            account_info = (
                f"🏦 浮动余额: {floating_balance:.2f} USDT ({account['balance']:.2f}{total_unrealized_pnl:+.2f})\n"
                f"📊 杠杆率: {leverage_ratio:.2f}x (仓位总价值: {total_position_value:.0f}u)\n"
                f"⚠️ 强平阈值: {liquidation_threshold:.2f} USDT ({dynamic_threshold_ratio*100:.1f}%)"
            )

            message = f"<blockquote expandable>💼 账户信息\n\n{account_info}</blockquote>{risk_warning}"

            if detailed_positions:
                message += f"\n\n<blockquote>📋 详细仓位信息\n\n{detailed_positions}</blockquote>"

            return {'success': True, 'message': message}

        except Exception as e:
            logger.error(f"获取仓位摘要失败: {e}")
            return {
                "success": False,
                "message": f"获取仓位信息失败: {str(e)}"
            }

    def _calculate_dynamic_liquidation_threshold(self, leverage_ratio: float) -> float:
        """根据杠杆倍数动态计算强平保证金率阈值"""
        if leverage_ratio <= 1.0:
            return 0.05  # 1倍以内，5%
        elif leverage_ratio >= 100.0:
            return 0.20  # 100倍以上，20%
        else:
            # 1-100倍之间线性插值
            return 0.05 + (leverage_ratio - 1.0) * 0.15 / 99.0

    async def close_all_positions(self, user_id: int, group_id: int) -> Dict:
        """一键全平所有仓位"""
        try:
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return {"success": False, "message": "获取仓位信息失败"}

            positions = positions_result["positions"]
            if not positions:
                return {"success": False, "message": "当前没有持仓"}

            total_pnl = 0.0
            total_fee = 0.0
            closed_positions = []

            for position in positions:
                # 获取实时价格（一键全平使用实时价格确保准确性）
                current_price = await price_service.get_real_time_price(position['symbol'])
                if not current_price:
                    continue

                # 计算手续费和平仓盈亏
                fee = position['size'] * 0.00035  # 万分之3.5
                pnl_before_fee = self._calculate_pnl(position['entry_price'], current_price,
                                                   position['size'], position['side'])
                net_pnl = pnl_before_fee - fee

                total_pnl += net_pnl
                total_fee += fee

                # 删除仓位
                delete_result = TradingRepository.delete_position(
                    user_id, group_id, position['symbol'], position['side']
                )

                if delete_result["success"]:
                    closed_positions.append({
                        'symbol': position['symbol'],
                        'side': position['side'],
                        'size': position['size'],
                        'pnl_before_fee': pnl_before_fee,
                        'fee': fee,
                        'net_pnl': net_pnl
                    })

                    # 记录交易历史
                    TradingRepository.add_trading_history(
                        user_id, group_id, 'close', position['symbol'], position['side'],
                        position['size'], current_price, net_pnl
                    )

            if not closed_positions:
                return {"success": False, "message": "平仓失败，无法获取价格信息"}

            # 更新账户余额和统计
            account = account_service.get_or_create_account(user_id, group_id)
            new_balance = account['balance'] + total_pnl

            balance_result = TradingRepository.update_account_balance(
                user_id, group_id, new_balance, total_pnl, total_fee, False
            )

            # 构建返回消息
            message_lines = ["🔄 一键全平成功！"]
            for pos in closed_positions:
                direction_emoji = "📈" if pos['side'] == 'long' else "📉"
                coin_symbol = pos['symbol'].replace('/USDT', '')
                pnl_color = "🟢" if pos['net_pnl'] >= 0 else "🔴"
                message_lines.append(
                    f"{direction_emoji} {coin_symbol} -{pos['size']:.2f} USDT "
                    f"({pnl_color} 净盈亏: {pos['net_pnl']:+.2f} USDT)"
                )
            message_lines.append(f"\n💰 总手续费: -{total_fee:.2f} USDT")
            message_lines.append(f"💰 总净盈亏: {total_pnl:+.2f} USDT")

            return {'success': True, 'message': '\n'.join(message_lines)}

        except Exception as e:
            logger.error(f"一键全平失败: {e}")
            return {
                "success": False,
                "message": f"一键全平失败: {str(e)}"
            }


# 全局仓位服务实例
position_service = PositionService()