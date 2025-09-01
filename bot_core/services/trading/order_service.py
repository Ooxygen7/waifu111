"""
订单服务
负责交易订单的创建、管理、执行和取消
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .account_service import account_service
from .price_service import price_service
from .position_service import position_service
from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class OrderService:
    """
    订单管理服务
    处理订单的完整生命周期：创建、匹配、执行、取消
    """

    def __init__(self):
        logger.info("订单服务已初始化")

    async def create_order(self, user_id: int, group_id: int, symbol: str, direction: str,
                    role: str, order_type: str, operation: str, volume: float,
                    price: Optional[float] = None, tp_price: Optional[float] = None,
                    sl_price: Optional[float] = None) -> Dict:
        """
        创建新的交易订单

        Args:
            user_id: 用户ID
            group_id: 群组ID
            symbol: 交易对，如'BTC/USDT'
            direction: 方向，'bid'(买入) 或 'ask'(卖出)
            role: 角色，'maker'(限价单) 或 'taker'(市价单)
            order_type: 订单类型，'open'(开仓), 'tp'(止盈), 'sl'(止损)
            operation: 操作，'reduction'(减仓), 'addition'(加仓)
            volume: 订单体积(USDT价值)
            price: 委托价格，None表示市价单
            tp_price: 止盈价格
            sl_price: 止损价格

        Returns:
            订单创建结果
        """
        try:
            # 标准化交易对格式
            if '/' not in symbol:
                symbol = f"{symbol.upper()}/USDT"

            # 验证订单参数
            if direction not in ['bid', 'ask']:
                return {"success": False, "message": "无效的方向，必须为'bid'或'ask'"}

            if role not in ['maker', 'taker']:
                return {"success": False, "message": "无效的角色，必须为'maker'或'taker'"}

            if order_type not in ['open', 'tp', 'sl']:
                return {"success": False, "message": "无效的订单类型，必须为'open', 'tp'或'sl'"}

            if operation not in ['reduction', 'addition']:
                return {"success": False, "message": "无效的操作，必须为'reduction'或'addition'"}

            # 获取用户账户信息
            account = account_service.get_or_create_account(user_id, group_id)

            # 计算保证金和手续费
            # 止盈止损订单不需要冻结保证金
            if order_type in ['tp', 'sl']:
                margin_required = 0.0
            else:
                margin_required = self._calculate_margin_required(volume, symbol)
            
            fee_rate = 0.00035 if role == 'taker' else 0.00015  # 市价单万分之3.5，限价单万分之1.5
            estimated_fee = volume * fee_rate

            # 检查保证金充足性（止盈止损订单跳过检查）
            if order_type not in ['tp', 'sl'] and account['balance'] - account['frozen_margin'] < margin_required:
                return {
                    "success": False,
                    "message": f"保证金不足，需要: {margin_required:.2f} USDT，可用余额: {account['balance'] - account['frozen_margin']:.2f} USDT"
                }

            # 为限价单检查价格合理性和币种有效性
            if role == 'maker':
                # 检查币种是否存在（通过尝试获取价格验证）
                current_price = await price_service.get_current_price(symbol)
                if not current_price:
                    return {
                        "success": False,
                        "message": f"无法获取 {symbol} 价格，该币种可能不存在或暂时无法交易"
                    }
                
                # 如果指定了价格，检查价格合理性
                if price is not None:
                    price_valid = await self._validate_price(price, symbol, direction)
                    if not price_valid:
                        return {
                            "success": False,
                            "message": f"限价单价格不合理，请检查价格设置"
                        }

            # 生成订单ID
            order_id = str(uuid.uuid4())

            # 创建订单
            result = TradingRepository.create_order(
                order_id, user_id, group_id, symbol, direction, role,
                order_type, operation, volume, price, tp_price, sl_price,
                margin_required, fee_rate
            )

            if not result["success"]:
                return result

            # 冻结保证金（止盈止损订单不需要冻结）
            if margin_required > 0:
                margin_result = account_service.update_margin(user_id, group_id, margin_required)
                if not margin_result["success"]:
                    logger.error(f"冻结保证金失败: {margin_result.get('error')}")
                    # 这里应该考虑回滚订单创建，但暂时先记录错误

            # 市价单立即执行
            if role == 'taker' and order_type == 'open':
                logger.info(f"检测到市价单，准备立即执行 - ID:{order_id}, role:{role}, order_type:{order_type}")
                # 获取实时市场价格（市价单必须使用最新价格，不依赖缓存）
                current_price = await price_service.get_real_time_price(symbol)
                if current_price:
                    logger.info(f"获取到实时价格 {current_price}，开始立即执行市价单 - ID:{order_id}")
                    # 立即执行市价单
                    execution_result = await self.execute_order(order_id)
                    if execution_result["success"]:
                        logger.info(f"市价单立即执行成功 - ID:{order_id}, 成交价:{current_price}")
                        return {
                            "success": True,
                            "order_id": order_id,
                            "executed": True,
                            "execution_price": current_price,
                            "message": f"市价单执行成功！\n订单ID: {order_id}\n成交价格: {current_price:.4f}\n数量: {volume:.2f} USDT\n手续费: {estimated_fee:.2f} USDT"
                        }
                    else:
                        logger.error(f"市价单立即执行失败: {execution_result.get('message')} - ID:{order_id}")
                        # 执行失败，取消订单并解冻保证金
                        self.cancel_order(order_id)
                        return {
                            "success": False,
                            "message": f"市价单执行失败: {execution_result.get('message')}"
                        }
                else:
                    logger.warning(f"无法获取{symbol}当前价格，市价单创建失败 - ID:{order_id}")
                    # 无法获取价格，取消订单并解冻保证金
                    self.cancel_order(order_id)
                    return {
                        "success": False,
                        "message": f"无法获取 {symbol} 价格，该币种可能不存在或暂时无法交易"
                    }
            else:
                logger.debug(f"非市价开仓单，跳过立即执行 - ID:{order_id}, role:{role}, order_type:{order_type}")

            logger.info(f"订单创建成功 - ID:{order_id}, 用户{user_id}, {direction.upper()} {symbol}, 数量:{volume:.2f}, 类型:{order_type}")

            return {
                "success": True,
                "order_id": order_id,
                "message": f"订单创建成功！\n订单ID: {order_id}\n类型: {order_type.upper()}\n方向: {direction.upper()}\n数量: {volume:.2f} USDT\n保证金: {margin_required:.2f} USDT\n预计手续费: {estimated_fee:.2f} USDT"
            }

        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return {
                "success": False,
                "message": f"创建订单失败: {str(e)}"
            }

    async def execute_order(self, order_id: str) -> Dict:
        """
        执行订单（由监控服务调用）

        Args:
            order_id: 订单ID

        Returns:
            执行结果
        """
        try:
            # 获取订单信息
            order_result = TradingRepository.get_order(order_id)
            if not order_result["success"] or not order_result["order"]:
                return {"success": False, "message": "订单不存在"}

            order = order_result["order"]

            # 检查订单状态
            if order["status"] != "pending":
                return {"success": False, "message": f"订单状态为{order['status']}，无法执行"}

            # 根据订单类型获取价格（市价单使用实时价格，限价单使用缓存价格）
            if order["role"] == "taker":  # 市价单
                current_price = await price_service.get_real_time_price(order["symbol"])
                if not current_price:
                    return {"success": False, "message": "无法获取实时价格"}
            else:  # 限价单
                current_price = await price_service.get_current_price(order["symbol"])
                if not current_price:
                    return {"success": False, "message": "无法获取当前价格"}

            # 检查价格匹配条件
            if not self._check_price_condition(order, current_price):
                return {"success": False, "message": "价格条件不满足"}

            # 执行订单
            execution_result = await self._execute_order_transaction(order, current_price)

            return execution_result

        except Exception as e:
            logger.error(f"执行订单失败 {order_id}: {e}")
            return {
                "success": False,
                "message": f"执行订单失败: {str(e)}"
            }

    async def _execute_order_transaction(self, order: Dict, execution_price: float) -> Dict:
        """执行订单事务"""
        try:
            # 计算实际手续费
            actual_fee = order["volume"] * order["fee_rate"]

            # 对于优于市价的限价单，按市价计算手续费
            if order["role"] == "maker":
                # 这里需要检查是否优于市价，如果是则按市价费率收费
                # 暂时简化处理
                pass

            # 解冻保证金
            margin_result = account_service.update_margin(
                order["user_id"], order["group_id"], -order["margin_locked"]
            )

            if not margin_result["success"]:
                return {"success": False, "message": "解冻保证金失败"}

            # 更新订单状态
            status_result = TradingRepository.execute_order(
                order["order_id"], execution_price
            )

            if not status_result["success"]:
                return {"success": False, "message": "更新订单状态失败"}

            # 记录交易历史
            pnl = 0.0  # 平仓时的盈亏，暂时设为0，开仓时没有盈亏
            history_result = TradingRepository.add_trading_history(
                order["user_id"], order["group_id"], order["order_type"].upper(),
                order["symbol"], "long" if order["direction"] == "ask" else "short",
                order["volume"], execution_price, pnl
            )

            # 执行仓位操作
            if order["order_type"] == "open":
                position_result = await position_service.execute_order_position(order)
                if not position_result["success"]:
                    logger.error(f"仓位操作失败: {position_result.get('message')}")
                    # 注意：这里不返回失败，因为订单已经执行成功，仓位操作失败不应该影响订单状态
                else:
                    logger.info(f"仓位操作成功 - 订单ID:{order['order_id']}")
            elif order["order_type"] in ["tp", "sl"]:
                # 止盈止损订单需要执行平仓操作
                user_id = order["user_id"]
                group_id = order["group_id"]
                symbol = order["symbol"]
                
                # 确定平仓方向：止盈止损订单的direction是平仓方向
                close_direction = order["direction"]  # ask或bid
                
                # 执行平仓操作 - 平掉该交易对的所有仓位
                close_result = await position_service._reduce_position(
                    user_id, group_id, symbol, close_direction, order["volume"], execution_price
                )
                
                if not close_result["success"]:
                    logger.error(f"止盈止损平仓失败: {close_result.get('message')} - 订单ID:{order['order_id']}")
                else:
                    logger.info(f"止盈止损平仓成功 - 订单ID:{order['order_id']}, 平仓方向:{close_direction}")

            # 从账户余额中扣除手续费
            account = account_service.get_or_create_account(order["user_id"], order["group_id"])
            new_balance = account['balance'] - actual_fee
            
            # 更新账户余额（扣除手续费）
            balance_result = TradingRepository.update_account_balance(
                order["user_id"], order["group_id"], new_balance, 0.0
            )
            if not balance_result["success"]:
                logger.error(f"扣除手续费失败: {balance_result.get('message')}")
                # 注意：这里不返回失败，因为订单已经执行成功
            else:
                logger.info(f"手续费扣除成功 - 用户ID:{order['user_id']}, 手续费:{actual_fee:.2f} USDT")

            # 记录手续费到交易历史（作为负盈亏记录）
            fee_history_result = TradingRepository.add_trading_history(
                order["user_id"], order["group_id"], "FEE",
                order["symbol"], "long" if order["direction"] == "ask" else "short",
                order["volume"], execution_price, -actual_fee
            )

            logger.info(f"订单执行成功 - ID:{order['order_id']}, 成交价:{execution_price}, 手续费:{actual_fee}")

            return {
                "success": True,
                "message": f"订单执行成功！\n成交价格: {execution_price}\n手续费: {actual_fee:.2f} USDT"
            }

        except Exception as e:
            logger.error(f"执行订单事务失败: {e}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}"
            }

    def cancel_order(self, order_id: str) -> Dict:
        """
        取消订单

        Args:
            order_id: 订单ID

        Returns:
            取消结果
        """
        try:
            # 获取订单信息
            order_result = TradingRepository.get_order(order_id)
            if not order_result["success"] or not order_result["order"]:
                return {"success": False, "message": "订单不存在"}

            order = order_result["order"]

            # 检查订单状态
            if order["status"] != "pending":
                return {"success": False, "message": f"订单状态为{order['status']}，无法取消"}

            # 取消订单
            cancel_result = TradingRepository.cancel_order(order_id)
            if not cancel_result["success"] or not cancel_result["cancelled"]:
                return {"success": False, "message": "取消订单失败"}

            # 解冻保证金（止盈止损订单不需要解冻）
            if order.get('order_type') not in ['tp', 'sl'] and order.get('margin_locked', 0) > 0:
                margin_result = account_service.update_margin(
                    order["user_id"], order["group_id"], -order["margin_locked"]
                )
                message = f"订单取消成功！\n解冻保证金: {order['margin_locked']:.2f} USDT"
            else:
                message = "订单取消成功！"

            logger.info(f"订单取消成功 - ID:{order_id}")

            return {
                "success": True,
                "message": message
            }

        except Exception as e:
            logger.error(f"取消订单失败 {order_id}: {e}")
            return {
                "success": False,
                "message": f"取消失败: {str(e)}"
            }

    def get_orders(self, user_id: int, group_id: int, status: Optional[str] = None) -> Dict:
        """获取用户订单列表"""
        try:
            result = TradingRepository.get_orders(user_id, group_id, status)
            return result
        except Exception as e:
            logger.error(f"获取订单列表失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_orders_by_type(self, user_id: int, group_id: int, order_type: str, status: Optional[str] = None) -> List[Dict]:
        """获取指定类型的用户订单列表"""
        try:
            result = self.get_orders(user_id, group_id, status)
            if result["success"]:
                # 过滤出指定类型的订单
                filtered_orders = [order for order in result["orders"] if order["order_type"] == order_type]
                return filtered_orders
            else:
                logger.error(f"获取订单失败: {result.get('error')}")
                return []
        except Exception as e:
            logger.error(f"获取{order_type}订单失败: {e}")
            return []

    def _calculate_margin_required(self, volume: float, symbol: str) -> float:
        """计算所需保证金 (100倍杠杆 = 1%)"""
        return volume / 100

    async def _validate_price(self, price: float, symbol: str, direction: str) -> bool:
        """验证限价单价格合理性"""
        try:
            current_price = await price_service.get_current_price(symbol)
            if not current_price:
                return False

            # 对于买入单，委托价不应远高于市价；卖出单不应远低于市价
            # 这里设置10%的合理范围
            min_price = current_price * 0.9
            max_price = current_price * 1.1

            if direction == 'bid' and price > max_price:
                logger.warning(f"限价买入价格过高: {price} > {max_price}")
                return False
            elif direction == 'ask' and price < min_price:
                logger.warning(f"限价卖出价格过低: {price} < {min_price}")
                return False

            return True

        except Exception as e:
            logger.error(f"验证价格失败: {e}")
            return False

    def _check_price_condition(self, order: Dict, current_price: float) -> bool:
        """检查价格触发条件"""
        try:
            if order["role"] == "taker":  # 市价单
                return True  # 随时可以执行

            elif order["role"] == "maker":  # 限价单
                if order["price"] is None:
                    return True  # 没有指定价格，按市价执行

                # 检查是否达到委托价格
                if order["direction"] == "bid":  # 买入单
                    return current_price <= order["price"]  # 价格下降到委托价或以下
                else:  # 卖出单
                    return current_price >= order["price"]  # 价格上升到委托价或以上

            return False

        except Exception as e:
            logger.error(f"检查价格条件失败: {e}")
            return False


# 全局订单服务实例
    async def create_limit_order(self, user_id: int, group_id: int, symbol: str, 
                                direction: str, order_type: str, volume: float, 
                                price: float, parent_order_id: Optional[str] = None) -> Dict:
        """
        创建限价订单
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            symbol: 交易对
            direction: 方向，'long'(做多) 或 'short'(做空)
            order_type: 订单类型，'open'(开仓), 'tp'(止盈), 'sl'(止损)
            volume: 订单体积
            price: 限价价格
            parent_order_id: 父订单ID（用于止盈止损）
            
        Returns:
            订单创建结果
        """
        # 转换方向参数
        bid_ask_direction = "bid" if direction == "long" else "ask"
        
        return await self.create_order(
            user_id=user_id,
            group_id=group_id,
            symbol=symbol,
            direction=bid_ask_direction,
            role="maker",  # 限价单为maker
            order_type=order_type,
            operation="addition",  # 默认为加仓
            volume=volume,
            price=price
        )
    
    async def create_market_order(self, user_id: int, group_id: int, symbol: str,
                                direction: str, order_type: str, volume: float,
                                trigger_price: Optional[float] = None,
                                parent_order_id: Optional[str] = None) -> Dict:
        """
        创建市价订单
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            symbol: 交易对
            direction: 方向，'long'(做多) 或 'short'(做空)
            order_type: 订单类型，'open'(开仓), 'tp'(止盈), 'sl'(止损)
            volume: 订单体积
            trigger_price: 触发价格（用于止损）
            parent_order_id: 父订单ID（用于止盈止损）
            
        Returns:
            订单创建结果
        """
        # 转换方向参数
        bid_ask_direction = "bid" if direction == "long" else "ask"
        
        return await self.create_order(
            user_id=user_id,
            group_id=group_id,
            symbol=symbol,
            direction=bid_ask_direction,
            role="taker",  # 市价单为taker
            order_type=order_type,
            operation="addition",  # 默认为加仓
            volume=volume,
            price=trigger_price  # 市价单价格为None，除非是止损触发价
        )


order_service = OrderService()