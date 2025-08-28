"""
监控服务
负责价格轮询、订单触发、强平监控和利息计算
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable

from .account_service import account_service
from .order_service import order_service
from .position_service import position_service
from .price_service import price_service
from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class MonitorService:
    """
    监控服务类
    负责定时监控价格、触发订单、检查强平条件和利息计算
    """

    def __init__(self):
        self.is_running = False
        self.monitor_task = None
        self.price_check_interval = 10  # 价格检查间隔(秒)
        self.liquidation_check_interval = 30  # 强平检查间隔(秒)
        self.interest_update_interval = 21600  # 利息更新间隔(6小时)

        # 回调函数
        self.on_liquidation_callback: Optional[Callable] = None

        # 定时器计数器
        self.price_counter = 0
        self.liquidation_counter = 0
        self.interest_counter = 0

        logger.info("监控服务已初始化")

    async def start_monitoring(self):
        """启动监控服务"""
        if self.is_running:
            logger.warning("监控服务已在运行中")
            return

        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("监控服务已启动")

    async def stop_monitoring(self):
        """停止监控服务"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("监控服务已停止")

    async def _monitor_loop(self):
        """主监控循环"""
        logger.info("监控循环已启动")

        try:
            while self.is_running:
                try:
                    # 更新计数器
                    self.price_counter += 1
                    self.liquidation_counter += 1
                    self.interest_counter += 1

                    # 每10秒检查订单触发条件
                    if self.price_counter >= 1:
                        self.price_counter = 0
                        await self._check_pending_orders()

                    # 每30秒检查一次强平条件
                    if self.liquidation_counter >= 3:
                        self.liquidation_counter = 0
                        await self._check_liquidations()

                    # 每6小时更新一次利息
                    if self.interest_counter >= 2160:  # 6小时 * 3600秒 / 10秒
                        self.interest_counter = 0
                        await self._update_loan_interests()

                    # 等待10秒
                    await asyncio.sleep(10)

                except Exception as e:
                    logger.error(f"监控循环出错: {e}")
                    await asyncio.sleep(10)  # 出错后等待10秒再继续

        except asyncio.CancelledError:
            logger.info("监控循环被取消")
            raise

    async def _check_pending_orders(self):
        """检查待成交订单是否可以触发"""
        try:
            # 获取所有待成交订单
            pending_orders_result = TradingRepository.get_orders_by_type('open', 'pending')
            if not pending_orders_result["success"]:
                return

            orders = pending_orders_result["orders"]
            logger.debug(f"检查 {len(orders)} 个待成交订单")

            triggered_orders = []
            
            for order in orders:
                try:
                    # 检查订单是否可以触发
                    can_trigger = await self._check_order_trigger_condition(order)
                    
                    if can_trigger:
                        # 执行订单
                        result = await order_service.execute_order(order["order_id"])
                        
                        if result["success"]:
                            logger.info(f"订单 {order['order_id']} 已成功执行")
                            triggered_orders.append(order)
                            
                            # 检查是否需要触发止盈止损订单
                            await self._check_and_create_stop_orders(order)
                        else:
                            logger.debug(f"订单 {order['order_id']} 执行失败: {result.get('message', '未知错误')}")

                except Exception as e:
                    logger.error(f"检查订单 {order['order_id']} 失败: {e}")
                    continue
            
            # 检查现有仓位的止盈止损条件
            await self._check_stop_loss_take_profit_orders()
            
            if triggered_orders:
                logger.info(f"本轮触发了 {len(triggered_orders)} 个订单")

        except Exception as e:
            logger.error(f"检查待成交订单失败: {e}")

    async def _check_liquidations(self):
        """检查所有仓位是否需要强平"""
        try:
            # 获取所有仓位
            positions_result = TradingRepository.get_all_positions()
            if not positions_result["success"]:
                return

            positions = positions_result["positions"]
            logger.debug(f"检查 {len(positions)} 个仓位强平条件")

            # 按用户分组检查强平
            user_positions = {}
            for pos in positions:
                user_key = (pos['user_id'], pos['group_id'])
                if user_key not in user_positions:
                    user_positions[user_key] = []
                user_positions[user_key].append(pos)

            liquidated_positions = []

            for (user_id, group_id), user_pos_list in user_positions.items():
                user_liquidated = await self._check_user_liquidations(user_id, group_id, user_pos_list)
                liquidated_positions.extend(user_liquidated)

            # 处理强平结果
            if liquidated_positions:
                logger.info(f"共处理 {len(liquidated_positions)} 个强平")
                for position_info in liquidated_positions:
                    if self.on_liquidation_callback:
                        try:
                            await self.on_liquidation_callback(position_info)
                        except Exception as e:
                            logger.error(f"执行强平回调失败: {e}")

        except Exception as e:
            logger.error(f"检查强平失败: {e}")

    async def _check_user_liquidations(self, user_id: int, group_id: int, positions: List[Dict]) -> List[Dict]:
        """检查单个用户的强平条件"""
        try:
            liquidated_positions = []

            # 获取用户账户信息
            account = account_service.get_or_create_account(user_id, group_id)
            initial_balance = 1000.0  # 初始本金

            # 计算总未实现盈亏
            total_unrealized_pnl = 0.0
            position_details = []

            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                size = pos['size']
                entry_price = pos['entry_price']
                liquidation_price = pos['liquidation_price']

                # 获取当前价格
                current_price = await price_service.get_current_price(symbol)
                if current_price <= 0:
                    continue

                # 计算该仓位的未实现盈亏
                if side == 'long':
                    unrealized_pnl = (current_price - entry_price) * (size / entry_price)
                else:
                    unrealized_pnl = (entry_price - current_price) * (size / entry_price)

                total_unrealized_pnl += unrealized_pnl

                position_details.append({
                    'symbol': symbol,
                    'side': side,
                    'size': size,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'liquidation_price': liquidation_price,
                    'unrealized_pnl': unrealized_pnl
                })

            # 计算浮动余额
            floating_balance = account['balance'] + total_unrealized_pnl

            # 计算动态强平阈值（基于杠杆率）
            total_position_value = sum(pos['size'] for pos in positions)
            leverage_ratio = total_position_value / account['balance'] if account['balance'] > 0 else float('inf')

            dynamic_threshold_ratio = self._calculate_dynamic_liquidation_threshold(leverage_ratio)
            liquidation_threshold = account['balance'] * dynamic_threshold_ratio

            # 检查是否触发强平
            if floating_balance < liquidation_threshold:
                logger.info(f"用户 {user_id} 在群组 {group_id} 触发强平，浮动余额: {floating_balance:.2f}, 阈值: {liquidation_threshold:.2f}")

                # 统计强平信息
                total_position_value = sum(pos['size'] for pos in positions)

                liquidated_positions.append({
                    'user_id': user_id,
                    'group_id': group_id,
                    'floating_balance': floating_balance,
                    'threshold': liquidation_threshold,
                    'leverage_ratio': leverage_ratio,
                    'threshold_ratio': dynamic_threshold_ratio,
                    'total_positions': len(positions),
                    'total_position_value': total_position_value
                })

                # 执行强平清算
                await self._execute_liquidation(user_id, group_id, positions, floating_balance)

            return liquidated_positions

        except Exception as e:
            logger.error(f"检查用户强平失败 {user_id}: {e}")
            return []

    async def _execute_liquidation(self, user_id: int, group_id: int, positions: List[Dict], final_balance: float):
        """执行强平清算"""
        try:
            # 删除所有仓位并记录损失
            total_loss = -abs(final_balance)  # 将正余额清零的损失

            for pos in positions:
                try:
                    # 删除仓位
                    TradingRepository.delete_position(user_id, group_id, pos['symbol'], pos['side'])

                    # 获取当前价格用于历史记录
                    current_price = await price_service.get_current_price(pos['symbol'])
                    if current_price <= 0:
                        current_price = pos['entry_price']

                    # 记录强平历史
                    TradingRepository.add_trading_history(
                        user_id, group_id, 'liquidated', pos['symbol'], pos['side'],
                        pos['size'], current_price, total_loss / len(positions)  # 平均分配损失
                    )
                    logger.debug(f"强平仓位删除: {pos['symbol']} {pos['side']} - {pos['size']}")

                except Exception as e:
                    logger.error(f"删除强平仓位失败 {pos['symbol']} {pos['side']}: {e}")
                    continue

            # 清零余额并记录强平损失
            TradingRepository.update_account_balance(
                user_id, group_id, 0.0, total_loss, 0.0, False
            )

            logger.info(f"强平清算完成 - 用户{user_id} 群组{group_id}: 损失{total_loss:.2f}")

        except Exception as e:
            logger.error(f"执行强平清算失败 {user_id}: {e}")

    async def _update_loan_interests(self):
        """批量更新所有用户的贷款利息"""
        try:
            logger.info("开始批量更新贷款利息")

            # 获取所有活跃贷款
            command = """
                SELECT DISTINCT user_id, group_id
                FROM loans
                WHERE status = 'active'
            """
            from utils.db_utils import query_db
            result = query_db(command)

            updated_count = 0
            for row in result:
                user_id = row[0]
                group_id = row[1]

                try:
                    # 导入loan_service并更新利息
                    from .loan_service import loan_service
                    loan_result = loan_service.update_loan_interests(user_id, group_id)
                    
                    if loan_result.get("success", False):
                        updated_count += 1
                        logger.debug(f"用户 {user_id} 贷款利息更新成功")
                    else:
                        logger.warning(f"用户 {user_id} 贷款利息更新失败: {loan_result.get('message', '未知错误')}")

                except Exception as e:
                    logger.error(f"更新用户 {user_id} 贷款利息失败: {e}")
                    continue

            if updated_count > 0:
                logger.info(f"完成贷款利息更新: {updated_count} 个用户")

        except Exception as e:
            logger.error(f"批量更新贷款利息失败: {e}")

    def set_liquidation_callback(self, callback: Callable):
        """设置强平回调函数"""
        self.on_liquidation_callback = callback
        logger.info("强平回调函数已设置")

    def _calculate_dynamic_liquidation_threshold(self, leverage_ratio: float) -> float:
        """根据杠杆倍数动态计算强平保证金率阈值"""
        if leverage_ratio <= 1.0:
            return 0.05  # 1倍以内，5%
        elif leverage_ratio >= 100.0:
            return 0.20  # 100倍以上，20%
        else:
            # 1-100倍之间线性插值
            return 0.05 + (leverage_ratio - 1.0) * 0.15 / 99.0

    async def get_monitoring_status(self) -> Dict:
        """获取监控服务状态"""
        try:
            # 获取待成交订单数量
            pending_orders_result = TradingRepository.get_orders_by_type('open', 'pending')
            pending_orders_count = len(pending_orders_result["orders"]) if pending_orders_result["success"] else 0

            # 获取活跃仓位数量
            positions_result = TradingRepository.get_all_positions()
            positions_count = len(positions_result["positions"]) if positions_result["success"] else 0

            return {
                "success": True,
                "is_running": self.is_running,
                "check_intervals": {
                    "price_check": f"{self.price_check_interval}s",
                    "liquidation_check": f"{self.liquidation_check_interval}s",
                    "interest_update": f"{self.interest_update_interval}s"
                },
                "pending_orders_count": pending_orders_count,
                "active_positions_count": positions_count,
                "performance_counters": {
                    "price_checks": self.price_counter,
                    "liquidation_checks": self.liquidation_counter,
                    "interest_updates": self.interest_counter
                }
            }

        except Exception as e:
            logger.error(f"获取监控状态失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "is_running": self.is_running
            }


    async def _check_order_trigger_condition(self, order: Dict) -> bool:
        """检查订单是否满足触发条件"""
        try:
            symbol = order['symbol']
            order_type = order['order_type']
            direction = order['direction']  # 使用正确的字段名
            role = order['role']
            order_price = order.get('price')  # 使用正确的字段名
            tp_price = order.get('tp_price')
            sl_price = order.get('sl_price')
            
            # 获取当前市场价格
            current_price = await price_service.get_current_price(symbol)
            if current_price <= 0:
                logger.debug(f"无法获取 {symbol} 的当前价格")
                return False
            
            logger.debug(f"检查订单触发条件: {order['order_id']}, 类型: {order_type}, 方向: {direction}, 角色: {role}, 委托价: {order_price}, 当前价: {current_price}")
            
            # 根据订单类型和方向判断触发条件
            if order_type == 'open' and role == 'maker':  # 开仓限价单
                if direction == 'bid':  # 买入(做多)
                    # 买入限价单：当前价格 <= 委托价格时触发
                    triggered = current_price <= order_price
                    logger.debug(f"买入限价单触发检查: 当前价 {current_price} <= 委托价 {order_price} = {triggered}")
                    return triggered
                elif direction == 'ask':  # 卖出(做空)
                    # 卖出限价单：当前价格 >= 委托价格时触发
                    triggered = current_price >= order_price
                    logger.debug(f"卖出限价单触发检查: 当前价 {current_price} >= 委托价 {order_price} = {triggered}")
                    return triggered
            
            elif order_type == 'open' and role == 'taker':  # 开仓市价单
                # 市价单立即触发
                logger.debug(f"市价单立即触发")
                return True
            
            elif order_type == 'sl':  # 止损单
                if direction == 'bid':  # 多头止损
                    # 多头止损：当前价格 <= 止损价格时触发
                    triggered = current_price <= sl_price if sl_price else False
                    logger.debug(f"多头止损触发检查: 当前价 {current_price} <= 止损价 {sl_price} = {triggered}")
                    return triggered
                elif direction == 'ask':  # 空头止损
                    # 空头止损：当前价格 >= 止损价格时触发
                    triggered = current_price >= sl_price if sl_price else False
                    logger.debug(f"空头止损触发检查: 当前价 {current_price} >= 止损价 {sl_price} = {triggered}")
                    return triggered
            
            elif order_type == 'tp':  # 止盈单
                if direction == 'bid':  # 多头止盈
                    # 多头止盈：当前价格 >= 止盈价格时触发
                    triggered = current_price >= tp_price if tp_price else False
                    logger.debug(f"多头止盈触发检查: 当前价 {current_price} >= 止盈价 {tp_price} = {triggered}")
                    return triggered
                elif direction == 'ask':  # 空头止盈
                    # 空头止盈：当前价格 <= 止盈价格时触发
                    triggered = current_price <= tp_price if tp_price else False
                    logger.debug(f"空头止盈触发检查: 当前价 {current_price} <= 止盈价 {tp_price} = {triggered}")
                    return triggered
            
            logger.debug(f"订单不满足任何触发条件")
            return False
            
        except Exception as e:
            logger.error(f"检查订单触发条件失败: {e}")
            return False
    
    async def _check_and_create_stop_orders(self, executed_order: Dict):
        """检查并创建止盈止损订单"""
        try:
            # 如果执行的订单有止盈止损设置，创建相应的止盈止损订单
            stop_loss_price = executed_order.get('stop_loss_price')
            take_profit_price = executed_order.get('take_profit_price')
            
            if stop_loss_price or take_profit_price:
                user_id = executed_order['user_id']
                group_id = executed_order['group_id']
                symbol = executed_order['symbol']
                side = executed_order['side']
                size = executed_order['size']
                
                # 创建止损订单
                if stop_loss_price:
                    stop_loss_result = await order_service.create_order(
                        user_id=user_id,
                        group_id=group_id,
                        symbol=symbol,
                        side='short' if side == 'long' else 'long',  # 反向平仓
                        order_type='stop_loss',
                        size=size,
                        trigger_price=stop_loss_price,
                        order_attribute='close_position'
                    )
                    
                    if stop_loss_result['success']:
                        logger.info(f"为订单 {executed_order['order_id']} 创建止损订单成功")
                
                # 创建止盈订单
                if take_profit_price:
                    take_profit_result = await order_service.create_order(
                        user_id=user_id,
                        group_id=group_id,
                        symbol=symbol,
                        side='short' if side == 'long' else 'long',  # 反向平仓
                        order_type='take_profit',
                        size=size,
                        trigger_price=take_profit_price,
                        order_attribute='close_position'
                    )
                    
                    if take_profit_result['success']:
                        logger.info(f"为订单 {executed_order['order_id']} 创建止盈订单成功")
                        
        except Exception as e:
            logger.error(f"创建止盈止损订单失败: {e}")
    
    async def _check_stop_loss_take_profit_orders(self):
        """检查现有仓位的止盈止损订单"""
        try:
            # 获取所有止盈止损订单
            tp_orders_result = TradingRepository.get_orders_by_type('tp', 'pending')
            sl_orders_result = TradingRepository.get_orders_by_type('sl', 'pending')
            
            if not tp_orders_result.get('success', False) or not sl_orders_result.get('success', False):
                return
            
            stop_orders = tp_orders_result.get('orders', []) + sl_orders_result.get('orders', [])
            
            for order in stop_orders:
                try:
                    # 检查止盈止损订单是否可以触发
                    can_trigger = await self._check_order_trigger_condition(order)
                    
                    if can_trigger:
                        # 执行止盈止损订单
                        result = await order_service.execute_order(order['order_id'])
                        
                        if result['success']:
                            logger.info(f"止盈止损订单 {order['order_id']} 已成功执行")
                        else:
                            logger.debug(f"止盈止损订单 {order['order_id']} 执行失败: {result.get('message', '未知错误')}")
                            
                except Exception as e:
                    logger.error(f"检查止盈止损订单 {order['order_id']} 失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"检查止盈止损订单失败: {e}")


# 全局监控服务实例
monitor_service = MonitorService()