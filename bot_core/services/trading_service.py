import asyncio
import logging
import sqlite3
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# 屏蔽ccxt的日志输出
logging.getLogger('ccxt').setLevel(logging.WARNING)
logging.getLogger('ccxt.base').setLevel(logging.WARNING)
logging.getLogger('ccxt.bybit').setLevel(logging.WARNING)

class TradingService:
    """
    模拟盘交易服务
    处理开仓、平仓、查询仓位、救济金等功能
    """
    
    def __init__(self):
        # 初始化交易所连接(使用Bybit作为价格源)
        self.exchange = ccxt.bybit({
            'sandbox': False,  # 使用实盘数据但不实际交易
            'enableRateLimit': True,
        })
        self.price_cache = {}  # 价格缓存
        self.last_update = {}
        
    async def get_current_price(self, symbol: str) -> float:
        """
        获取当前价格，优先从缓存获取，缓存过期则从交易所获取
        """
        try:
            # 标准化交易对格式
            if '/' not in symbol:
                symbol = f"{symbol.upper()}/USDT"
            
            # 检查缓存是否有效(10秒内)
            now = datetime.now()
            if (symbol in self.price_cache and 
                symbol in self.last_update and 
                (now - self.last_update[symbol]).seconds < 10):
                return self.price_cache[symbol]
            
            # 从交易所获取最新价格
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ticker, symbol
            )
            price_val = ticker.get('last')
            if price_val is None:
                logger.warning(f"获取的ticker中'last'价格为空: {symbol}")
                return self._get_price_from_db(symbol)
            price = float(price_val)
            
            # 更新缓存
            self.price_cache[symbol] = price
            self.last_update[symbol] = now
            
            # 更新数据库价格缓存
            self._update_price_cache_db(symbol, price)
            
            return price
            
        except Exception as e:
            logger.error(f"获取价格失败 {symbol}: {e}")
            # 从数据库获取缓存价格
            return self._get_price_from_db(symbol)
    
    def _update_price_cache_db(self, symbol: str, price: float):
        """更新数据库中的价格缓存"""
        try:
            result = TradingRepository.update_price_cache(symbol, price)
            if not result["success"]:
                logger.error(f"更新价格缓存失败: {result.get('error')}")
        except Exception as e:
            logger.error(f"更新价格缓存失败: {e}")
    
    def _get_price_from_db(self, symbol: str) -> float:
        """从数据库获取缓存价格"""
        try:
            result = TradingRepository.get_price_cache(symbol)
            if result["success"] and result["cache"]:
                return result["cache"]["price"]
            return 0.0
        except Exception as e:
            logger.error(f"从数据库获取价格失败: {e}")
            return 0.0
    
    def get_or_create_account(self, user_id: int, group_id: int) -> Dict:
        """获取或创建用户交易账户"""
        try:
            # 尝试获取现有账户
            result = TradingRepository.get_account(user_id, group_id)
            if not result["success"]:
                logger.error(f"获取账户失败: {result['error']}")
                return {'balance': 0.0, 'total_pnl': 0.0}
            
            if result["account"]:
                account = result["account"]
                return {
                    'balance': account['balance'],
                    'total_pnl': account['total_pnl']
                }
            
            # 创建新账户
            create_result = TradingRepository.create_account(user_id, group_id)
            if not create_result["success"]:
                logger.error(f"创建账户失败: {create_result['error']}")
                return {'balance': 0.0, 'total_pnl': 0.0}
            
            return {'balance': 1000.0, 'total_pnl': 0.0}
                
        except Exception as e:
            logger.error(f"获取/创建账户失败: {e}")
            return {'balance': 0.0, 'total_pnl': 0.0}
    
    async def open_position(self, user_id: int, group_id: int, symbol: str, side: str, size: float) -> Dict:
        """
        开仓操作
        side: 'long' 或 'short'
        size: 仓位大小(USDT价值)
        """
        try:
            # 获取当前价格
            current_price = await self.get_current_price(symbol)
            if current_price <= 0:
                return {'success': False, 'message': f'无法获取 {symbol} 价格'}
            
            # 获取账户信息
            account = self.get_or_create_account(user_id, group_id)
            
            # 计算所需保证金 (100倍杠杆，即1%保证金)
            required_margin = size / 100
            if account['balance'] < required_margin:
                return {'success': False, 'message': f'保证金不足，需要: {required_margin:.2f} USDT，当前余额: {account["balance"]:.2f} USDT'}
            
            # 检查是否已有相同方向的仓位
            position_result = TradingRepository.get_position(user_id, group_id, symbol, side)
            if not position_result["success"]:
                return {'success': False, 'message': '获取仓位信息失败'}
            
            existing_position = position_result["position"]
            
            if existing_position:
                # 加仓操作 - 检查额外保证金
                additional_margin = size / 100
                if account['balance'] < additional_margin:
                    return {'success': False, 'message': f'加仓保证金不足，需要: {additional_margin:.2f} USDT，当前余额: {account["balance"]:.2f} USDT'}
                
                old_size = existing_position['size']
                old_entry = existing_position['entry_price']
                new_size = old_size + size
                new_entry = (old_size * old_entry + size * current_price) / new_size
                
                # 验证加仓后的总仓位价值不超过浮动余额的100倍
                # 获取用户所有仓位计算总价值
                positions_result = TradingRepository.get_positions(user_id, group_id)
                total_position_value = new_size  # 当前仓位的新价值
                total_unrealized_pnl = 0.0
                
                if positions_result["success"] and positions_result["positions"]:
                    for pos in positions_result["positions"]:
                        # 跳过当前正在加仓的仓位（因为还没更新到数据库）
                        if pos['symbol'] == symbol and pos['side'] == side:
                            continue
                        
                        total_position_value += pos['size']
                        
                        # 计算其他仓位的未实现盈亏
                        pos_current_price = await self.get_current_price(pos['symbol'])
                        if pos_current_price > 0:
                            pnl = self._calculate_pnl(pos['entry_price'], pos_current_price, pos['size'], pos['side'])
                            total_unrealized_pnl += pnl
                
                # 计算当前仓位的未实现盈亏
                current_pnl = self._calculate_pnl(new_entry, current_price, new_size, side)
                total_unrealized_pnl += current_pnl
                
                # 计算浮动余额
                floating_balance = account['balance'] + total_unrealized_pnl
                
                # 检查总仓位价值是否超过浮动余额的100倍
                max_allowed_value = floating_balance * 100
                if total_position_value > max_allowed_value:
                    return {
                        'success': False, 
                        'message': f'加仓失败！总仓位价值 {total_position_value:.2f} USDT 超过浮动余额的100倍限制 {max_allowed_value:.2f} USDT\n当前浮动余额: {floating_balance:.2f} USDT'
                    }
                
                # 计算新的强平价格
                liquidation_price = await self._calculate_liquidation_price(
                    user_id, group_id, symbol, side, new_size, new_entry
                )
                
                update_result = TradingRepository.update_position(
                    user_id, group_id, symbol, side, new_size, new_entry, liquidation_price
                )
                if not update_result["success"]:
                    return {'success': False, 'message': '更新仓位失败'}
                
                # 使用新的显示格式
                side_emoji = "📈" if side == 'long' else "📉"
                coin_symbol = symbol.replace('/USDT', '')
                formatted_entry_price = self._format_price(new_entry)

                message = f"加仓成功！\n{side_emoji} {coin_symbol} +{size:.2f} USDT\n平均开仓价: {formatted_entry_price}\n总仓位: {new_size:.2f} USDT"
            else:
                # 新开仓位 - 验证仓位价值不超过浮动余额的100倍
                # 获取用户所有现有仓位计算总价值
                positions_result = TradingRepository.get_positions(user_id, group_id)
                total_position_value = size  # 新仓位的价值
                total_unrealized_pnl = 0.0
                
                if positions_result["success"] and positions_result["positions"]:
                    for pos in positions_result["positions"]:
                        total_position_value += pos['size']
                        
                        # 计算现有仓位的未实现盈亏
                        pos_current_price = await self.get_current_price(pos['symbol'])
                        if pos_current_price > 0:
                            pnl = self._calculate_pnl(pos['entry_price'], pos_current_price, pos['size'], pos['side'])
                            total_unrealized_pnl += pnl
                
                # 计算浮动余额（新仓位还没有盈亏）
                floating_balance = account['balance'] + total_unrealized_pnl
                
                # 检查总仓位价值是否超过浮动余额的100倍
                max_allowed_value = floating_balance * 100
                if total_position_value > max_allowed_value:
                    return {
                        'success': False, 
                        'message': f'开仓失败！总仓位价值 {total_position_value:.2f} USDT 超过浮动余额的100倍限制 {max_allowed_value:.2f} USDT\n当前浮动余额: {floating_balance:.2f} USDT'
                    }
                
                liquidation_price = await self._calculate_liquidation_price(
                    user_id, group_id, symbol, side, size, current_price
                )
                
                create_result = TradingRepository.create_position(
                    user_id, group_id, symbol, side, size, current_price, liquidation_price
                )
                if not create_result["success"]:
                    return {'success': False, 'message': '创建仓位失败'}
                
                # 使用新的显示格式
                side_emoji = "📈" if side == 'long' else "📉"
                coin_symbol = symbol.replace('/USDT', '')
                formatted_entry_price = self._format_price(current_price)
                formatted_liquidation_price = self._format_price(liquidation_price)

                message = f"开仓成功！\n{side_emoji} {coin_symbol} {size:.2f} USDT\n开仓价: {formatted_entry_price}\n强平价: {formatted_liquidation_price}"
            
            # 计算开仓手续费 (万分之3.5)
            open_fee = size * 0.00035
            
            # 从账户余额中扣除手续费
            account = self.get_or_create_account(user_id, group_id)
            new_balance = account['balance'] - open_fee
            
            # 更新账户余额（扣除手续费，但不计入总盈亏统计）
            balance_result = TradingRepository.update_account_balance(user_id, group_id, new_balance, 0.0)
            if not balance_result["success"]:
                return {'success': False, 'message': '更新账户余额失败'}
            
            # 记录交易历史（手续费作为负盈亏记录，但不影响胜率）
            TradingRepository.add_trading_history(
                user_id, group_id, 'open', symbol, side, size, current_price, -open_fee
            )
            
            # 在消息中显示手续费信息
            message += f"\n手续费: -{open_fee:.2f} USDT"
            
            return {'success': True, 'message': message}
                
        except Exception as e:
            logger.error(f"开仓失败: {e}")
            return {'success': False, 'message': '开仓失败，请稍后重试'}
    
    async def close_position(self, user_id: int, group_id: int, symbol: str, side: Optional[str] = None, size: Optional[float] = None) -> Dict:
        """
        智能平仓操作
        side: 仓位方向，None表示智能平仓（根据持仓情况自动决定）
        size: 平仓大小，None表示全部平仓
        """
        try:
            # 获取当前价格
            current_price = await self.get_current_price(symbol)
            if current_price <= 0:
                return {'success': False, 'message': f'无法获取 {symbol} 价格'}
            
            # 获取该币种的所有仓位
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return {'success': False, 'message': '获取仓位信息失败'}
            
            # 筛选出指定币种的仓位
            symbol_positions = [pos for pos in positions_result["positions"] if pos['symbol'] == symbol]
            
            if not symbol_positions:
                return {'success': False, 'message': f'没有找到 {symbol} 仓位'}
            
            # 如果指定了方向，只平指定方向的仓位
            if side:
                target_positions = [pos for pos in symbol_positions if pos['side'] == side]
                if not target_positions:
                    return {'success': False, 'message': f'没有找到 {symbol} {side.upper()} 仓位'}
            else:
                # 智能平仓：平所有该币种的仓位
                target_positions = symbol_positions
            
            total_pnl = 0.0
            total_close_fee = 0.0
            close_messages = []
            
            # 逐个平仓
            for position in target_positions:
                pos_side = position['side']
                pos_size = position['size']
                
                # 确定平仓大小
                if size and len(target_positions) == 1:
                    # 只有一个仓位且指定了平仓大小
                    close_size = min(size, pos_size)
                else:
                    # 多个仓位或未指定大小，全部平仓
                    close_size = pos_size
                
                # 计算平仓手续费 (万分之3.5)
                close_fee = close_size * 0.00035
                total_close_fee += close_fee
                
                # 计算盈亏（不包含手续费）
                pnl_before_fee = self._calculate_pnl(position['entry_price'], current_price, close_size, pos_side)
                # 计算扣除手续费后的净盈亏
                net_pnl = pnl_before_fee - close_fee
                total_pnl += net_pnl
                
                if close_size >= pos_size:
                    # 全部平仓
                    delete_result = TradingRepository.delete_position(user_id, group_id, symbol, pos_side)
                    if not delete_result["success"]:
                        return {'success': False, 'message': f'删除 {pos_side.upper()} 仓位失败'}
                    close_messages.append(f"{symbol} {pos_side.upper()} -{close_size:.2f} USDT (盈亏: {pnl_before_fee:+.2f} USDT, 手续费: -{close_fee:.2f} USDT, 净盈亏: {net_pnl:+.2f} USDT)")
                else:
                    # 部分平仓
                    new_size = pos_size - close_size
                    update_result = TradingRepository.update_position(
                        user_id, group_id, symbol, pos_side, new_size, position['entry_price'], position['liquidation_price']
                    )
                    if not update_result["success"]:
                        return {'success': False, 'message': f'更新 {pos_side.upper()} 仓位失败'}
                    close_messages.append(f"{symbol} {pos_side.upper()} -{close_size:.2f} USDT (剩余: {new_size:.2f} USDT, 盈亏: {pnl_before_fee:+.2f} USDT, 手续费: -{close_fee:.2f} USDT, 净盈亏: {net_pnl:+.2f} USDT)")
                
                # 记录交易历史（记录净盈亏，包含手续费）
                TradingRepository.add_trading_history(
                    user_id, group_id, 'close', symbol, pos_side, close_size, current_price, net_pnl
                )
            
            # 更新账户余额和总盈亏
            account = self.get_or_create_account(user_id, group_id)
            new_balance = account['balance'] + total_pnl
            
            balance_result = TradingRepository.update_account_balance(user_id, group_id, new_balance, total_pnl)
            if not balance_result["success"]:
                return {'success': False, 'message': '更新账户余额失败'}
            
            # 构建返回消息
            if len(close_messages) == 1:
                message = f"平仓成功！\n{close_messages[0]}"
            else:
                message = f"批量平仓成功！\n" + "\n".join(close_messages) + f"\n总手续费: -{total_close_fee:.2f} USDT\n总净盈亏: {total_pnl:+.2f} USDT"
            
            return {'success': True, 'message': message}
                
        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return {'success': False, 'message': '平仓失败，请稍后重试'}

    async def close_all_positions(self, user_id: int, group_id: int) -> Dict:
        """
        一键全平所有仓位
        """
        try:
            # 获取用户所有仓位
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return {'success': False, 'message': '获取仓位信息失败'}
            
            positions = positions_result["positions"]
            if not positions:
                return {'success': False, 'message': '当前没有持仓'}
            
            total_pnl = 0.0
            total_close_fee = 0.0
            closed_positions = []
            
            # 逐个平仓所有仓位
            for position in positions:
                symbol = position['symbol']
                side = position['side']
                size = position['size']
                
                # 获取当前价格
                current_price = await self.get_current_price(symbol)
                if current_price <= 0:
                    continue
                
                # 计算平仓手续费 (万分之3.5)
                close_fee = size * 0.00035
                total_close_fee += close_fee
                
                # 计算盈亏（不包含手续费）
                pnl_before_fee = self._calculate_pnl(position['entry_price'], current_price, size, side)
                # 计算扣除手续费后的净盈亏
                net_pnl = pnl_before_fee - close_fee
                total_pnl += net_pnl
                
                # 删除仓位
                delete_result = TradingRepository.delete_position(user_id, group_id, symbol, side)
                if delete_result["success"]:
                    closed_positions.append({
                        'symbol': symbol,
                        'side': side,
                        'size': size,
                        'pnl_before_fee': pnl_before_fee,
                        'close_fee': close_fee,
                        'net_pnl': net_pnl
                    })
                    
                    # 记录交易历史（记录净盈亏，包含手续费）
                    TradingRepository.add_trading_history(
                        user_id, group_id, 'close', symbol, side, size, current_price, net_pnl
                    )
            
            if not closed_positions:
                return {'success': False, 'message': '平仓失败，无法获取价格信息'}
            
            # 更新账户余额
            account = self.get_or_create_account(user_id, group_id)
            new_balance = account['balance'] + total_pnl
            
            balance_result = TradingRepository.update_account_balance(user_id, group_id, new_balance, total_pnl)
            if not balance_result["success"]:
                return {'success': False, 'message': '更新账户余额失败'}
            
            # 构建返回消息
            message_lines = ["🔄 一键全平成功！"]
            for pos in closed_positions:
                message_lines.append(f"{pos['symbol']} {pos['side'].upper()} -{pos['size']:.2f} USDT (盈亏: {pos['pnl_before_fee']:+.2f} USDT, 手续费: -{pos['close_fee']:.2f} USDT, 净盈亏: {pos['net_pnl']:+.2f} USDT)")
            message_lines.append(f"\n💰 总手续费: -{total_close_fee:.2f} USDT")
            message_lines.append(f"💰 总净盈亏: {total_pnl:+.2f} USDT")
            
            return {'success': True, 'message': '\n'.join(message_lines)}
            
        except Exception as e:
            logger.error(f"一键全平失败: {e}")
            return {'success': False, 'message': '一键全平失败，请稍后重试'}

    async def get_positions(self, user_id: int, group_id: int) -> dict:
        """获取用户所有仓位信息"""
        try:
            account = self.get_or_create_account(user_id, group_id)
            
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return {'success': False, 'message': '获取仓位信息失败'}
            
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
            
            total_unrealized_pnl = 0
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
                current_price = await self.get_current_price(symbol)

                # 计算未实现盈亏
                unrealized_pnl = self._calculate_pnl(entry_price, current_price, size, side)
                total_unrealized_pnl += unrealized_pnl

                # 计算盈亏百分比 - 按总杠杆率计算
                # 使用总杠杆倍数而不是固定100倍
                if leverage_ratio > 0:
                    margin = size / leverage_ratio
                    pnl_percent = (unrealized_pnl / margin) * 100 if margin > 0 else 0
                else:
                    pnl_percent = 0

                # 使用不同emoji表示多空方向
                side_emoji = "📈" if side == 'long' else "📉"

                # 移除/USDT后缀，只显示币种
                coin_symbol = symbol.replace('/USDT', '')

                # 计算数量（仓位价值/开仓价格）
                quantity = size / entry_price if entry_price > 0 else 0

                # 格式化数量显示
                def format_quantity(q: float) -> str:
                    if q >= 1000000:
                        return f"{q/1000000:.2f}m"
                    elif q >= 1000:
                        return f"{q/1000:.2f}k"
                    else:
                        return f"{q:.2f}"

                formatted_quantity = format_quantity(quantity)

                # 使用动态价格精度
                formatted_entry_price = self._format_price(entry_price)
                formatted_current_price = self._format_price(current_price)

                position_text.append(
                    f"{side_emoji}  {coin_symbol} |数量{formatted_quantity}| {unrealized_pnl:+.2f} USDT ({pnl_percent:+.2f}%)\n"
                    f"   开仓:{formatted_entry_price} |现价:{formatted_current_price}"
                )
            
            # 计算浮动余额
            floating_balance = account['balance'] + total_unrealized_pnl
            
            # 计算动态强平阈值
            dynamic_threshold_ratio = self._calculate_dynamic_liquidation_threshold(leverage_ratio)
            liquidation_threshold = account['balance'] * dynamic_threshold_ratio  # 基于当前余额计算

            # 构建强平阈值信息
            threshold_info = f"⚠️ 强平阈值: {liquidation_threshold:.2f} USDT ({dynamic_threshold_ratio*100:.1f}%)"
            
            risk_warning = ""
            if floating_balance < liquidation_threshold:
                risk_warning = "\n🚨 警告: 已触发强平条件！"
            elif floating_balance < liquidation_threshold * 1.1:
                risk_warning = "\n⚠️ 警告: 接近强平，请注意风险！"
            
            # 使用可折叠的引用块显示详细仓位信息
            detailed_positions = "\n\n".join(position_text)
            
            # 构建简化的账户信息
            account_info = (
                f"🏦 浮动余额: {floating_balance:.2f} USDT({account['balance']:.2f}{total_unrealized_pnl:+.2f})\n"
                f"📊 杠杆率: {leverage_ratio:.2f}(仓位总价值:{total_position_value:.0f}u)\n"
                f"{threshold_info}"
            )
            
            message = f"<blockquote expandable>💼 账户信息\n\n{account_info}</blockquote>{risk_warning}"

            # 添加详细仓位信息（实时更新，不使用expandable）
            if detailed_positions:
                message += f"\n\n<blockquote>📋 详细仓位信息\n\n{detailed_positions}</blockquote>"
            
            return {'success': True, 'message': message}
            
        except Exception as e:
            logger.error(f"获取仓位失败: {e}")
            return {'success': False, 'message': '获取仓位信息失败'}
    
    def begging(self, user_id: int, group_id: int) -> Dict:
        """救济金功能"""
        try:
            account = self.get_or_create_account(user_id, group_id)
            
            # 检查余额是否小于100
            if account['balance'] >= 100:
                return {'success': False, 'message': f'余额充足({account["balance"]:.2f} USDT)，无需救济金'}
            
            # 检查今日是否已领取
            begging_result = TradingRepository.get_begging_record(user_id, group_id)
            if not begging_result["success"]:
                return {'success': False, 'message': '检查救济金记录失败'}
            
            today = datetime.now().date()
            
            if begging_result["record"]:
                return {'success': False, 'message': '今日已领取救济金，明天再来吧！'}
            
            # 发放救济金
            balance_result = TradingRepository.update_account_balance(user_id, group_id, 1000.0)
            if not balance_result["success"]:
                return {'success': False, 'message': '更新账户余额失败'}
            
            # 创建救济金记录
            begging_create_result = TradingRepository.create_begging_record(user_id, group_id, 1000.0)
            if not begging_create_result["success"]:
                return {'success': False, 'message': '创建救济金记录失败'}
            
            return {'success': True, 'message': '🎁 救济金发放成功！余额已补充至 1000 USDT'}
                
        except Exception as e:
            logger.error(f"救济金发放失败: {e}")
            return {'success': False, 'message': '救济金发放失败'}
    
    def _get_position(self, user_id: int, group_id: int, symbol: str, side: str) -> Optional[Dict]:
        """获取指定仓位"""
        try:
            result = TradingRepository.get_position(user_id, group_id, symbol, side)
            if result["success"] and result["position"]:
                return result["position"]
            return None
        except Exception as e:
            logger.error(f"获取仓位失败: {e}")
            return None
    
    def _calculate_pnl(self, entry_price: float, current_price: float, size: float, side: str) -> float:
        """计算盈亏"""
        if side == 'long':
            return (current_price - entry_price) * size / entry_price
        else:
            return (entry_price - current_price) * size / entry_price
    
    def _calculate_dynamic_liquidation_threshold(self, leverage_ratio: float) -> float:
        """根据杠杆倍数动态计算强平保证金率阈值
        
        Args:
            leverage_ratio: 杠杆倍数 (仓位价值/浮动余额)
            
        Returns:
            强平保证金率阈值 (0-1之间的小数)
        """
        if leverage_ratio <= 1.0:
            # 1倍以内，强平阈值为5%
            return 0.05
        elif leverage_ratio >= 100.0:
            # 100倍以上，强平阈值为20%
            return 0.20
        else:
            # 1-100倍之间，平滑计算
            # 使用线性插值：y = 0.05 + (leverage_ratio - 1) * (0.20 - 0.05) / (100 - 1)
            return 0.05 + (leverage_ratio - 1.0) * 0.15 / 99.0
    
    async def _calculate_liquidation_price(self, user_id: int, group_id: int, symbol: str, side: str, size: float, entry_price: float) -> float:
        """计算强平价格 - 基于动态保证金率阈值"""
        try:
            account = self.get_or_create_account(user_id, group_id)
            
            # 获取用户所有仓位（包括当前仓位）来计算总价值
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                # 如果获取失败，使用一个保守的默认值
                return entry_price * 0.8 if side == 'long' else entry_price * 1.2

            all_positions = positions_result["positions"]
            
            # 检查当前仓位是否已在列表中，如果不在（例如新开仓），则手动加入计算
            current_position_found = False
            for pos in all_positions:
                if pos['symbol'] == symbol and pos['side'] == side:
                    # 更新仓位大小和价格为最新值
                    pos['size'] = size
                    pos['entry_price'] = entry_price
                    current_position_found = True
                    break
            
            if not current_position_found:
                all_positions.append({'symbol': symbol, 'side': side, 'size': size, 'entry_price': entry_price})

            # 计算总仓位价值
            total_position_value = sum(p['size'] for p in all_positions)
            
            # 计算杠杆倍数 (仓位价值 / 账户余额)
            leverage_ratio = total_position_value / account['balance'] if account['balance'] > 0 else float('inf')
            
            # 根据杠杆倍数动态计算强平阈值比例
            dynamic_threshold_ratio = self._calculate_dynamic_liquidation_threshold(leverage_ratio)
            liquidation_threshold = account['balance'] * dynamic_threshold_ratio
            
            # 获取用户所有其他仓位的当前浮动盈亏
            other_positions_pnl = 0.0
            for pos in all_positions:
                # 跳过当前正在计算的仓位
                if pos['symbol'] == symbol and pos['side'] == side:
                    continue
                
                current_price = await self.get_current_price(pos['symbol'])
                if current_price > 0:
                    pnl = self._calculate_pnl(pos['entry_price'], current_price, pos['size'], pos['side'])
                    other_positions_pnl += pnl
            
            # 计算强平价格
            # 强平条件: 余额 + 其他仓位盈亏 + 当前仓位盈亏 = 强平阈值
            target_pnl = liquidation_threshold - account['balance'] - other_positions_pnl
            
            if size <= 0: # 避免除以零
                return entry_price

            if side == 'long':
                # 做多: target_pnl = (强平价 - 开仓价) / 开仓价 * 仓位大小
                # 强平价 = 开仓价 * (1 + target_pnl / 仓位大小)
                liquidation_price = entry_price * (1 + target_pnl / size)
            else:
                # 做空: target_pnl = (开仓价 - 强平价) / 开仓价 * 仓位大小
                # 强平价 = 开仓价 * (1 - target_pnl / 仓位大小)
                liquidation_price = entry_price * (1 - target_pnl / size)
            
            return max(liquidation_price, 0.0001)  # 确保价格为正
            
        except Exception as e:
            logger.error(f"计算强平价格失败: {e}")
            return entry_price * 0.8 if side == 'long' else entry_price * 1.2
    
    async def check_liquidations(self) -> List[Dict]:
        """检查所有仓位是否需要强平 - 基于浮动余额计算"""
        liquidated_positions = []

        try:
            # 首先检查并清理小额债务
            await self._cleanup_small_debts()
            all_positions_result = TradingRepository.get_all_positions()
            if not all_positions_result["success"]:
                return liquidated_positions
            
            positions = all_positions_result["positions"]
            
            # 按用户分组检查强平
            user_positions = {}
            for pos in positions:
                user_key = (pos['user_id'], pos['group_id'])
                if user_key not in user_positions:
                    user_positions[user_key] = []
                user_positions[user_key].append(pos)
            
            # 检查每个用户的浮动余额
            for (user_id, group_id), user_pos_list in user_positions.items():
                account = self.get_or_create_account(user_id, group_id)
                initial_balance = 1000.0  # 本金固定为1000 USDT
                
                # 计算总浮动盈亏
                total_unrealized_pnl = 0.0
                position_details = []
                
                for pos in user_pos_list:
                    symbol = pos['symbol']
                    side = pos['side']
                    size = pos['size']
                    entry_price = pos['entry_price']
                    
                    # 获取当前价格
                    current_price = await self.get_current_price(symbol)
                    if current_price <= 0:
                        continue
                    
                    # 计算该仓位的浮动盈亏
                    unrealized_pnl = self._calculate_pnl(entry_price, current_price, size, side)
                    total_unrealized_pnl += unrealized_pnl
                    
                    position_details.append({
                        'symbol': symbol,
                        'side': side,
                        'size': size,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'unrealized_pnl': unrealized_pnl
                    })
                
                # 计算浮动余额
                floating_balance = account['balance'] + total_unrealized_pnl
                
                # 计算总仓位价值
                total_position_value = sum(pos['size'] for pos in user_pos_list)
                
                # 计算杠杆倍数 (仓位价值/余额)
                leverage_ratio = total_position_value / account['balance'] if account['balance'] > 0 else float('inf')
                
                # 根据杠杆倍数动态计算强平阈值
                dynamic_threshold_ratio = self._calculate_dynamic_liquidation_threshold(leverage_ratio)
                liquidation_threshold = account['balance'] * dynamic_threshold_ratio
                
                if floating_balance < liquidation_threshold:
                    # 触发强平 - 清空所有仓位，只记录一次爆仓事件
                    liquidated_positions.append({
                        'user_id': user_id,
                        'group_id': group_id,
                        'floating_balance': floating_balance,
                        'threshold': liquidation_threshold,
                        'leverage_ratio': leverage_ratio,
                        'threshold_ratio': dynamic_threshold_ratio,
                        'total_positions': len(user_pos_list),
                        'total_position_value': total_position_value
                    })

                    # 清空所有仓位
                    for pos in user_pos_list:
                        # 删除仓位
                        TradingRepository.delete_position(user_id, group_id, pos['symbol'], pos['side'])

                        # 记录强平历史
                        current_price = await self.get_current_price(pos['symbol'])
                        TradingRepository.add_trading_history(
                            user_id, group_id, 'liquidated', pos['symbol'], pos['side'],
                            pos['size'], current_price, -account['balance']
                        )

                    # 清零余额
                    # 清零余额，并记录亏损到总盈亏
                    liquidation_loss = -account['balance']
                    TradingRepository.update_account_balance(user_id, group_id, 0.0, liquidation_loss)

                    logger.info(f"用户 {user_id} 在群组 {group_id} 触发强平，浮动余额: {floating_balance:.2f}, 阈值: {liquidation_threshold:.2f}")
        
        except Exception as e:
            logger.error(f"检查强平失败: {e}")
        
        return liquidated_positions
    
    async def update_all_liquidation_prices(self) -> dict:
        """更新所有仓位的强平价格 - 根据实时价格数据动态调整"""
        try:
            all_positions_result = TradingRepository.get_all_positions()
            if not all_positions_result["success"]:
                return {"success": False, "error": "获取仓位失败"}
            
            positions = all_positions_result["positions"]
            updated_count = 0
            
            # 按用户分组更新强平价格
            user_positions = {}
            for pos in positions:
                user_key = (pos['user_id'], pos['group_id'])
                if user_key not in user_positions:
                    user_positions[user_key] = []
                user_positions[user_key].append(pos)
            
            for (user_id, group_id), user_pos_list in user_positions.items():
                for pos in user_pos_list:
                    try:
                        # 重新计算强平价格
                        new_liquidation_price = await self._calculate_liquidation_price(
                            user_id, group_id, pos['symbol'], pos['side'], 
                            pos['size'], pos['entry_price']
                        )
                        
                        # 更新数据库中的强平价格
                        update_result = TradingRepository.update_position(
                            user_id, group_id, pos['symbol'], pos['side'],
                            pos['size'], pos['entry_price'], new_liquidation_price
                        )
                        
                        if update_result["success"]:
                            updated_count += 1
                        
                    except Exception as e:
                        logger.error(f"更新仓位 {pos['symbol']} {pos['side']} 强平价格失败: {e}")
                        continue
            
            logger.debug(f"已更新 {updated_count} 个仓位的强平价格")
            return {
                "success": True, 
                "updated_count": updated_count,
                "total_positions": len(positions)
            }
            
        except Exception as e:
            logger.error(f"批量更新强平价格失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_ranking_data(self, group_id: int) -> Dict:
        """获取群组排行榜数据"""
        try:
            # 使用 repository 方法获取盈利排行榜
            profit_result = TradingRepository.get_group_profit_ranking(group_id)
            profit_ranking = profit_result.get("ranking", []) if profit_result.get("success") else []
            
            # 使用 repository 方法获取亏损排行榜
            loss_result = TradingRepository.get_group_loss_ranking(group_id)
            loss_ranking = loss_result.get("ranking", []) if loss_result.get("success") else []
            
            # 使用 repository 方法获取账户余额信息
            balance_result = TradingRepository.get_group_balance_accounts(group_id)
            balance_accounts = balance_result.get("accounts", []) if balance_result.get("success") else []
            
            # 使用 repository 方法获取爆仓次数排行榜
            liquidation_result = TradingRepository.get_group_liquidation_ranking(group_id)
            liquidation_ranking = liquidation_result.get("ranking", []) if liquidation_result.get("success") else []
            
            # 计算每个用户的浮动余额
            balance_ranking = []
            for account in balance_accounts:
                user_id = account["user_id"]
                balance = account["balance"]
                
                # 获取用户所有仓位计算未实现盈亏
                positions_result = TradingRepository.get_positions(user_id, group_id)
                total_unrealized_pnl = 0.0
                
                if positions_result["success"] and positions_result["positions"]:
                    for pos in positions_result["positions"]:
                        current_price = await self.get_current_price(pos['symbol'])
                        if current_price > 0:
                            pnl = self._calculate_pnl(pos['entry_price'], current_price, pos['size'], pos['side'])
                            total_unrealized_pnl += pnl
                
                floating_balance = balance + total_unrealized_pnl
                balance_ranking.append({
                    "user_id": user_id,
                    "balance": balance,
                    "floating_balance": floating_balance
                })
            
            # 按浮动余额排序并取前10名
            balance_ranking.sort(key=lambda x: x["floating_balance"], reverse=True)
            balance_ranking = balance_ranking[:10]
            
            # 获取交易量排行榜
            volume_result = TradingRepository.get_group_trading_volume_ranking(group_id)
            volume_ranking = volume_result.get("ranking", []) if volume_result.get("success") else []

            return {
                "success": True,
                "profit_ranking": profit_ranking,
                "loss_ranking": loss_ranking,
                "balance_ranking": balance_ranking,
                "liquidation_ranking": liquidation_ranking,
                "volume_ranking": volume_ranking
            }
            
        except Exception as e:
            logger.error(f"获取排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_overdue_days(self, loan_time: str) -> int:
        """计算贷款逾期天数"""
        try:
            loan_datetime = datetime.fromisoformat(loan_time.replace('Z', '+00:00'))
            current_datetime = datetime.now()
            
            # 计算从贷款开始到现在的天数
            days_since_loan = (current_datetime - loan_datetime).days
            
            # 假设贷款期限为30天，超过30天算逾期
            overdue_days = max(0, days_since_loan - 30)
            
            return overdue_days
        except Exception as e:
            logger.error(f"计算逾期天数失败: {e}")
            return 0
    
    async def get_deadbeat_ranking_data(self, group_id: int) -> Dict:
        """获取群组老赖排行榜数据"""
        try:
            # 获取老赖排行榜数据
            result = TradingRepository.get_group_deadbeat_ranking(group_id)
            
            if not result['success']:
                return result
            
            # 为每个老赖计算逾期天数
            deadbeat_ranking = []
            for deadbeat in result['ranking']:
                overdue_days = self._calculate_overdue_days(deadbeat['earliest_loan_time'])
                deadbeat_ranking.append({
                    **deadbeat,
                    'overdue_days': overdue_days
                })
            
            return {
                "success": True,
                "deadbeat_ranking": deadbeat_ranking
            }
            
        except Exception as e:
            logger.error(f"获取老赖排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_global_deadbeat_ranking_data(self) -> Dict:
        """获取跨群老赖排行榜数据"""
        try:
            # 获取跨群老赖排行榜数据
            result = TradingRepository.get_global_deadbeat_ranking()
            
            if not result['success']:
                return result
            
            # 为每个老赖计算逾期天数
            deadbeat_ranking = []
            for deadbeat in result['ranking']:
                overdue_days = self._calculate_overdue_days(deadbeat['earliest_loan_time'])
                deadbeat_ranking.append({
                    **deadbeat,
                    'overdue_days': overdue_days
                })
            
            return {
                "success": True,
                "deadbeat_ranking": deadbeat_ranking
            }
            
        except Exception as e:
            logger.error(f"获取跨群老赖排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_global_ranking_data(self) -> Dict:
        """获取跨群排行榜数据"""
        try:
            # 使用 repository 方法获取跨群盈利排行榜
            profit_result = TradingRepository.get_global_profit_ranking()
            profit_ranking = profit_result.get("ranking", []) if profit_result.get("success") else []
            
            # 使用 repository 方法获取跨群亏损排行榜
            loss_result = TradingRepository.get_global_loss_ranking()
            loss_ranking = loss_result.get("ranking", []) if loss_result.get("success") else []
            
            # 使用 repository 方法获取跨群账户余额信息
            balance_result = TradingRepository.get_global_balance_accounts()
            balance_accounts = balance_result.get("accounts", []) if balance_result.get("success") else []
            
            # 使用 repository 方法获取跨群爆仓次数排行榜
            liquidation_result = TradingRepository.get_global_liquidation_ranking()
            liquidation_data_list = liquidation_result.get("ranking", []) if liquidation_result.get("success") else []
            
            # 计算每个用户在各群的浮动余额，取最好的
            user_best_balance = {}
            for account in balance_accounts:
                user_id = account["user_id"]
                balance = account["balance"]
                group_id = account["group_id"]
                group_name = account["group_name"]
                
                # 获取用户在该群的所有仓位计算未实现盈亏
                positions_result = TradingRepository.get_positions(user_id, group_id)
                total_unrealized_pnl = 0.0
                
                if positions_result["success"] and positions_result["positions"]:
                    for pos in positions_result["positions"]:
                        current_price = await self.get_current_price(pos['symbol'])
                        if current_price > 0:
                            pnl = self._calculate_pnl(pos['entry_price'], current_price, pos['size'], pos['side'])
                            total_unrealized_pnl += pnl
                
                floating_balance = balance + total_unrealized_pnl
                
                # 保存该用户的最好成绩
                if user_id not in user_best_balance or floating_balance > user_best_balance[user_id]["floating_balance"]:
                    user_best_balance[user_id] = {
                        "user_id": user_id,
                        "balance": balance,
                        "floating_balance": floating_balance,
                        "group_id": group_id,
                        "group_name": group_name
                    }
            
            # 转换为列表并排序
            balance_ranking = list(user_best_balance.values())
            balance_ranking.sort(key=lambda x: x["floating_balance"], reverse=True)
            balance_ranking = balance_ranking[:10]
            
            # 计算每个用户的最多爆仓次数
            user_max_liquidation = {}
            for liquidation_data in liquidation_data_list:
                user_id = liquidation_data["user_id"]
                liquidation_count = liquidation_data["liquidation_count"]
                group_id = liquidation_data["group_id"]
                group_name = liquidation_data["group_name"]
                
                # 保存该用户的最多爆仓次数
                if user_id not in user_max_liquidation or liquidation_count > user_max_liquidation[user_id]["liquidation_count"]:
                    user_max_liquidation[user_id] = {
                        "user_id": user_id,
                        "liquidation_count": liquidation_count,
                        "group_id": group_id,
                        "group_name": group_name
                    }
            
            # 转换为列表并排序（爆仓次数从多到少）
            liquidation_ranking = list(user_max_liquidation.values())
            liquidation_ranking.sort(key=lambda x: x["liquidation_count"], reverse=True)
            liquidation_ranking = liquidation_ranking[:10]
            
            # 获取跨群交易量排行榜
            global_volume_result = TradingRepository.get_global_trading_volume_ranking()
            global_volume_ranking = global_volume_result.get("ranking", []) if global_volume_result.get("success") else []

            return {
                "success": True,
                "profit_ranking": profit_ranking,
                "loss_ranking": loss_ranking,
                "balance_ranking": balance_ranking,
                "liquidation_ranking": liquidation_ranking,
                "volume_ranking": global_volume_ranking
            }
            
        except Exception as e:
            logger.error(f"获取跨群排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pnl_report(self, user_id: int, group_id: int) -> Dict:
        """获取用户盈亏报告，包含最近15笔交易记录和总胜率"""
        try:
            # 获取用户账户信息（包含累计盈亏）
            account = self.get_or_create_account(user_id, group_id)
            total_pnl = account['total_pnl']

            # 获取交易历史记录
            history_result = TradingRepository.get_trading_history(user_id, group_id, 15)
            if not history_result["success"]:
                return {
                    "success": False,
                    "message": f"获取交易历史失败: {history_result['error']}"
                }

            # 获取胜率数据
            win_rate_result = TradingRepository.get_win_rate(user_id, group_id)
            if not win_rate_result["success"]:
                return {
                    "success": False,
                    "message": f"计算胜率失败: {win_rate_result['error']}"
                }

            history = history_result["history"]
            win_rate_data = win_rate_result

            # 构建消息
            if not history:
                pnl_status = "📈 累计盈利" if total_pnl >= 0 else "📉 累计亏损"
                pnl_color = "🟢" if total_pnl >= 0 else "🔴"
                message = f"📊 盈亏报告\n\n{pnl_color} {pnl_status}: {total_pnl:+.2f} USDT\n\n❌ 暂无交易记录"
            else:
                # 构建交易记录列表
                trade_records = []
                for i, trade in enumerate(history, 1):
                    # 多空单用上涨下跌emoji
                    side_emoji = '📈' if trade['side'] == 'long' else '📉'
                    
                    # 盈亏用勾叉
                    pnl_emoji = '✅' if trade['pnl'] > 0 else '❌'
                    
                    # 提取币种（去掉/USDT后缀）
                    coin = trade['symbol'].replace('/USDT', '')
                    
                    # 格式化时间
                    try:
                        from datetime import datetime
                        if isinstance(trade['created_at'], str):
                            dt = datetime.fromisoformat(trade['created_at'].replace('Z', '+00:00'))
                        else:
                            dt = trade['created_at']
                        time_str = dt.strftime('%m-%d %H:%M')
                    except:
                        time_str = str(trade['created_at'])[:16]
                    
                    # 使用数据库查询到的开仓价格和平仓价格
                    entry_price = trade['entry_price']  # 开仓价格
                    exit_price = trade['price']         # 平仓价格
                    
                    trade_records.append(
                        f"{side_emoji}{pnl_emoji} | {coin} | Entry:{entry_price:.4f} | Exit:{exit_price:.4f} | ${trade['size']:.0f} | PnL:{trade['pnl']:+.0f} | {time_str}"
                    )
                
                recent_trades = "\n".join(trade_records)
                
                # 胜率信息
                win_rate_info = (
                    f"📈 总交易次数: {win_rate_data['total_trades']}\n"
                    f"🎯 盈利次数: {win_rate_data['winning_trades']}\n"
                    f"📉 亏损次数: {win_rate_data['losing_trades']}\n"
                    f"⚡ 强平次数: {win_rate_data['liquidated_trades']}\n"
                    f"📊 胜率: {win_rate_data['win_rate']:.1f}%\n"
                    f"💰 累计交易量: ${win_rate_data['total_position_size']:.0f}\n"
                    f"💸 手续费贡献: ${win_rate_data['fee_contribution']:.2f}\n"
                    f" 平均仓位: ${win_rate_data['avg_position_size']:.0f}\n"
                    f"⏱️ 平均持仓: {win_rate_data['avg_holding_time']:.1f}小时\n"
                    f"📈 平均盈利: {win_rate_data['avg_win']:+.2f} USDT\n"
                    f"📉 平均亏损: {win_rate_data['avg_loss']:+.2f} USDT\n"
                    f"⚖️ 盈亏比: {win_rate_data['profit_loss_ratio']:.2f}"
                )
                
                # 币种统计信息
                symbol_stats = ""
                if win_rate_data['most_profitable_symbol']:
                    most_profitable_coin = win_rate_data['most_profitable_symbol'].replace('/USDT', '')
                    symbol_stats += f"🏆 最赚钱币种: {most_profitable_coin} (+{win_rate_data['most_profitable_pnl']:.0f} USDT, {win_rate_data['most_profitable_count']}次, 平均{win_rate_data['most_profitable_avg_pnl']:+.1f})\n"
                
                if win_rate_data['most_loss_symbol']:
                    most_loss_coin = win_rate_data['most_loss_symbol'].replace('/USDT', '')
                    symbol_stats += f"💸 最亏钱币种: {most_loss_coin} ({win_rate_data['most_loss_pnl']:+.0f} USDT, {win_rate_data['most_loss_count']}次, 平均{win_rate_data['most_loss_avg_pnl']:+.1f})\n"
                
                if win_rate_data['most_traded_symbol']:
                    most_traded_coin = win_rate_data['most_traded_symbol'].replace('/USDT', '')
                    symbol_stats += f"🔥 最常交易币种: {most_traded_coin} ({win_rate_data['most_traded_count']}次, 平均{win_rate_data['most_traded_avg_pnl']:+.1f} USDT)"
                
                # 构建完整消息
                # 累计盈亏信息
                pnl_status = "📈 累计盈利" if total_pnl >= 0 else "📉 累计亏损"
                pnl_color = "🟢" if total_pnl >= 0 else "🔴"

                message_parts = [
                    "📊 盈亏报告\n",
                    f"<blockquote expandable>💰 累计盈亏\n{pnl_color} {pnl_status}: {total_pnl:+.2f} USDT</blockquote>\n",
                    f"<blockquote expandable>📋 最近15笔交易\n\n{recent_trades}</blockquote>\n",
                    f"<blockquote expandable>📈 胜率统计\n\n{win_rate_info}</blockquote>"
                ]

                # 如果有币种统计信息，添加到消息中
                if symbol_stats.strip():
                    message_parts.append(f"\n<blockquote expandable>🎯 币种统计\n\n{symbol_stats}</blockquote>")

                message = "".join(message_parts)
            
            return {
                "success": True,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"获取盈亏报告失败: {e}")
            return {
                "success": False,
                "message": f"获取盈亏报告失败: {str(e)}"
            }

    def apply_loan(self, user_id: int, group_id: int, amount: float) -> Dict:
        """申请贷款"""
        try:
            # 获取用户账户信息
            account_result = TradingRepository.get_account(user_id, group_id)
            if not account_result["success"]:
                return {
                    "success": False,
                    "message": "获取账户信息失败"
                }
            
            account = account_result.get("account")
            if not account:
                # 创建新账户
                create_result = TradingRepository.create_account(user_id, group_id)
                if not create_result["success"]:
                    return {
                        "success": False,
                        "message": "创建账户失败"
                    }
                account = {"balance": 1000.0}
            
            current_balance = account["balance"]
            
            # 获取当前活跃贷款
            loans_result = TradingRepository.get_active_loans(user_id, group_id)
            if not loans_result["success"]:
                return {
                    "success": False,
                    "message": "获取贷款信息失败"
                }
            
            # 计算当前总欠款和总贷款本金
            current_total_debt = 0.0
            total_loan_principal = 0.0
            for loan in loans_result["loans"]:
                # 更新利息
                updated_debt = self._calculate_compound_interest(
                    loan["remaining_debt"], 
                    loan["last_interest_time"], 
                    loan["interest_rate"]
                )
                current_total_debt += updated_debt
                total_loan_principal += loan["principal"]
            
            # 计算净余额：当前余额减去所有贷款本金（排除贷款获得的资金）
            net_balance = current_balance - total_loan_principal
            
            # 检查贷款额度：总欠款不能超过净余额的20倍
            max_allowed_debt = net_balance * 20
            new_total_debt = current_total_debt + amount * 1.1  # 包含10%手续费
            
            if new_total_debt > max_allowed_debt:
                # 计算实际最大可贷金额（考虑10%手续费）
                max_loan_amount = (max_allowed_debt - current_total_debt) / 1.1
                return {
                    "success": False,
                    "message": f"贷款额度不足！\n💰 当前余额: {current_balance:.2f} USDT\n💸 净余额: {net_balance:.2f} USDT (扣除贷款本金: {total_loan_principal:.2f} USDT)\n💳 当前欠款: {current_total_debt:.2f} USDT\n📊 最大可贷: {max_loan_amount:.2f} USDT\n🏦 申请金额: {amount:.2f} USDT (含手续费: {amount * 1.1:.2f} USDT)\n\n💡 最大可贷金额已考虑10%手续费"
                }
            
            # 创建贷款记录
            loan_result = TradingRepository.create_loan(user_id, group_id, amount)
            if not loan_result["success"]:
                return {
                    "success": False,
                    "message": "创建贷款记录失败"
                }
            
            # 更新用户余额
            new_balance = current_balance + amount
            balance_result = TradingRepository.update_account_balance(user_id, group_id, new_balance)
            if not balance_result["success"]:
                return {
                    "success": False,
                    "message": "更新余额失败"
                }
            
            return {
                "success": True,
                "message": f"🏦 贷款成功！\n\n💰 贷款金额: {amount:.2f} USDT\n💸 手续费(10%): {amount * 0.1:.2f} USDT\n📊 实际欠款: {amount * 1.1:.2f} USDT\n💳 当前余额: {new_balance:.2f} USDT\n\n⚠️ 每6小时产生0.2%复利，请及时还款！",
                "loan_id": loan_result["loan_id"],
                "amount": amount,
                "new_balance": new_balance
            }
            
        except Exception as e:
            logger.error(f"申请贷款失败: {e}")
            return {
                "success": False,
                "message": f"申请贷款失败: {str(e)}"
            }
    
    def repay_loan(self, user_id: int, group_id: int, amount: Optional[float] = None) -> Dict:
        """还款操作"""
        try:
            # 获取用户账户信息
            account_result = TradingRepository.get_account(user_id, group_id)
            if not account_result["success"] or not account_result.get("account"):
                return {
                    "success": False,
                    "message": "账户不存在"
                }
            
            current_balance = account_result["account"]["balance"]
            
            # 获取活跃贷款
            loans_result = TradingRepository.get_active_loans(user_id, group_id)
            if not loans_result["success"]:
                return {
                    "success": False,
                    "message": "获取贷款信息失败"
                }
            
            if not loans_result["loans"]:
                return {
                    "success": False,
                    "message": "没有待还贷款"
                }
            
            # 更新所有贷款的利息
            total_debt = 0.0
            updated_loans = []
            for loan in loans_result["loans"]:
                updated_debt = self._calculate_compound_interest(
                    loan["remaining_debt"], 
                    loan["last_interest_time"], 
                    loan["interest_rate"]
                )
                # 更新数据库中的欠款
                TradingRepository.update_loan_debt(loan["id"], updated_debt)
                loan["remaining_debt"] = updated_debt
                updated_loans.append(loan)
                total_debt += updated_debt
            
            # 如果没有指定金额，则全额还款
            if amount is None:
                amount = total_debt
            else:
                # 如果指定了金额，检查是否超过实际欠款
                if amount > total_debt:
                    return {
                        "success": False,
                        "message": f"还款金额超过实际欠款！\n💸 实际欠款: {total_debt:.2f} USDT\n💰 指定还款: {amount:.2f} USDT\n\n💡 请输入不超过实际欠款的金额，或使用 /repay 进行全额还款"
                    }
            
            # 检查余额是否足够（保留1000 USDT）
            available_balance = max(0, current_balance - 1000)
            if amount > available_balance:
                return {
                    "success": False,
                    "message": f"余额不足！\n当前余额: {current_balance:.2f} USDT\n可用于还款: {available_balance:.2f} USDT\n需要还款: {amount:.2f} USDT\n\n💡 系统会保留1000 USDT作为救济金基础"
                }
            
            # 按贷款时间顺序还款（先还旧贷款）
            remaining_amount = amount
            repaid_loans = []
            
            for loan in sorted(updated_loans, key=lambda x: x["created_at"]):
                if remaining_amount <= 0:
                    break

                loan_debt = loan["remaining_debt"]
                repay_amount = min(remaining_amount, loan_debt)

                # 添加调试日志 - 跟踪还款计算
                logger.debug(f"处理贷款 #{loan['id']}: 原始债务={loan_debt:.10f}, 还款金额={repay_amount:.10f}")

                # 执行还款
                repay_result = TradingRepository.repay_loan(
                    loan["id"], user_id, group_id, repay_amount
                )

                if repay_result["success"]:
                    remaining_after = repay_result["remaining_after"]
                    # 检查是否出现精度损失导致的小额剩余债务
                    if 0 < remaining_after < 0.05:
                        logger.warning(f"检测到精度损失: 贷款 #{loan['id']} 剩余债务 {remaining_after:.10f} USDT，低于0.05 USDT阈值")
                        # 将小额剩余债务设为0并标记为已还款
                        TradingRepository.update_loan_debt(loan["id"], 0.0)
                        # 更新贷款状态为已还清
                        current_time = datetime.now().isoformat()
                        loan_update_command = """
                            UPDATE loans
                            SET remaining_debt = 0, status = 'paid_off', updated_at = ?
                            WHERE id = ?
                        """
                        from utils.db_utils import revise_db
                        revise_db(loan_update_command, (current_time, loan["id"]))
                        remaining_after = 0.0
                        logger.info(f"已清理小额债务: 贷款 #{loan['id']} 剩余债务已设为0")

                    repaid_loans.append({
                        "loan_id": loan["id"],
                        "amount": repay_amount,
                        "remaining": remaining_after,
                        "paid_off": repay_result["paid_off"] or remaining_after == 0.0
                    })
                    remaining_amount -= repay_amount
            
            # 更新用户余额
            new_balance = current_balance - amount
            TradingRepository.update_account_balance(user_id, group_id, new_balance)
            
            # 生成还款报告
            message_parts = [f"💳 还款成功！\n\n💰 还款金额: {amount:.2f} USDT\n💳 剩余余额: {new_balance:.2f} USDT\n\n"]
            
            for repaid in repaid_loans:
                status = "✅ 已结清" if repaid["paid_off"] else f"剩余: {repaid['remaining']:.2f} USDT"
                message_parts.append(f"📋 贷款#{repaid['loan_id']}: {repaid['amount']:.2f} USDT ({status})\n")
            
            # 检查是否还有剩余欠款
            remaining_loans = TradingRepository.get_active_loans(user_id, group_id)
            if remaining_loans["success"] and remaining_loans["loans"]:
                remaining_total = sum(loan["remaining_debt"] for loan in remaining_loans["loans"])
                message_parts.append(f"\n⚠️ 剩余总欠款: {remaining_total:.2f} USDT")
            else:
                message_parts.append("\n🎉 所有贷款已结清！")
            
            return {
                "success": True,
                "message": "".join(message_parts),
                "repaid_amount": amount,
                "new_balance": new_balance,
                "repaid_loans": repaid_loans
            }
            
        except Exception as e:
            logger.error(f"还款失败: {e}")
            return {
                "success": False,
                "message": f"还款失败: {str(e)}"
            }
    
    def get_loan_bill(self, user_id: int, group_id: int) -> Dict:
        """获取贷款账单"""
        try:
            # 获取贷款汇总
            summary_result = TradingRepository.get_loan_summary(user_id, group_id)
            if not summary_result["success"]:
                return {
                    "success": False,
                    "message": "获取贷款信息失败"
                }
            
            summary = summary_result["summary"]
            
            # 获取活跃贷款详情
            loans_result = TradingRepository.get_active_loans(user_id, group_id)
            if not loans_result["success"]:
                return {
                    "success": False,
                    "message": "获取贷款详情失败"
                }
            
            # 更新利息并计算总欠款
            current_total_debt = 0.0
            loan_details = []
            
            for loan in loans_result["loans"]:
                # 计算最新利息
                updated_debt = self._calculate_compound_interest(
                    loan["remaining_debt"], 
                    loan["last_interest_time"], 
                    loan["interest_rate"]
                )
                
                # 更新数据库
                TradingRepository.update_loan_debt(loan["id"], updated_debt)
                
                current_total_debt += updated_debt
                
                # 计算贷款天数
                loan_time = datetime.fromisoformat(loan["loan_time"])
                days_since_loan = (datetime.now() - loan_time).days
                
                loan_details.append({
                    "id": loan["id"],
                    "principal": loan["principal"],
                    "current_debt": updated_debt,
                    "days": days_since_loan,
                    "loan_time": loan["loan_time"]
                })
            
            # 生成账单消息
            if not loan_details:
                return {
                    "success": True,
                    "message": "🎉 恭喜！您当前没有任何贷款\n\n📊 历史统计:\n" +
                             f"📈 总贷款次数: {summary['total_loans']}\n" +
                             f"💰 累计借款: {summary['total_borrowed']:.2f} USDT\n" +
                             f"💳 累计还款: {summary['total_repaid']:.2f} USDT"
                }
            
            message_parts = [
                "🏦 贷款账单\n\n",
                f"📊 当前状态:\n",
                f"💰 活跃贷款: {summary['active_loan_count']} 笔\n",
                f"💸 总欠款: {current_total_debt:.2f} USDT\n\n",
                "📋 贷款详情:\n"
            ]
            
            for i, loan in enumerate(loan_details, 1):
                interest_generated = loan["current_debt"] - loan["principal"] * 1.1
                message_parts.append(
                    f"{i}. 贷款#{loan['id']}\n" +
                    f"   💰 本金: {loan['principal']:.2f} USDT\n" +
                    f"   💸 当前欠款: {loan['current_debt']:.2f} USDT\n" +
                    f"   📈 产生利息: {interest_generated:.2f} USDT\n" +
                    f"   📅 贷款天数: {loan['days']} 天\n\n"
                )
            
            message_parts.extend([
                "📊 历史统计:\n",
                f"📈 总贷款次数: {summary['total_loans']}\n",
                f"💰 累计借款: {summary['total_borrowed']:.2f} USDT\n",
                f"💳 累计还款: {summary['total_repaid']:.2f} USDT\n\n",
                "⚠️ 利息每6小时复利0.2%，请及时还款！"
            ])
            
            return {
                "success": True,
                "message": "".join(message_parts),
                "total_debt": current_total_debt,
                "active_loans": len(loan_details)
            }
            
        except Exception as e:
            logger.error(f"获取贷款账单失败: {e}")
            return {
                "success": False,
                "message": f"获取贷款账单失败: {str(e)}"
            }
    
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

    def _calculate_compound_interest(self, principal: float, last_interest_time: str, rate: float = 0.002) -> float:
        """计算复利"""
        try:
            last_time = datetime.fromisoformat(last_interest_time)
            current_time = datetime.now()

            # 计算经过的6小时周期数
            time_diff = current_time - last_time
            periods = time_diff.total_seconds() / (6 * 3600)  # 6小时为一个周期

            if periods < 1:
                return principal  # 不足一个周期，不计息

            # 复利计算: A = P(1 + r)^n
            compound_amount = principal * ((1 + rate) ** int(periods))

            # 添加调试日志 - 跟踪利息计算精度
            if abs(compound_amount - principal) > 0.0001:  # 如果利息变化超过0.0001
                logger.debug(f"利息计算: 本金={principal:.10f}, 周期数={int(periods)}, 利率={rate}, 计算结果={compound_amount:.10f}, 利息={compound_amount-principal:.10f}")

            return compound_amount

        except Exception as e:
            logger.error(f"计算复利失败: {e}")
            return principal

    async def _cleanup_small_debts(self) -> None:
        """清理所有用户的小额债务（低于0.05 USDT）"""
        try:
            logger.debug("开始清理小额债务...")

            # 获取所有活跃贷款 - 使用数据库查询
            command = """
                SELECT id, user_id, group_id, remaining_debt, interest_rate, loan_time, last_interest_time
                FROM loans
                WHERE status = 'active' AND remaining_debt > 0
            """
            from utils.db_utils import query_db
            result = query_db(command)

            if not result:
                logger.debug("没有找到活跃贷款")
                return

            cleaned_count = 0
            for row in result:
                loan_id = row[0]
                user_id = row[1]
                group_id = row[2]
                remaining_debt = float(row[3])

                # 检查是否是小额债务
                if 0 < remaining_debt < 0.05:
                    logger.info(f"发现小额债务: 用户 {user_id} 在群组 {group_id} 的贷款 #{loan_id} 剩余债务 {remaining_debt:.10f} USDT")

                    # 将小额债务设为0并标记为已还款
                    current_time = datetime.now().isoformat()
                    TradingRepository.update_loan_debt(loan_id, 0.0)

                    # 更新贷款状态为已还清
                    loan_update_command = """
                        UPDATE loans
                        SET remaining_debt = 0, status = 'paid_off', updated_at = ?
                        WHERE id = ?
                    """
                    from utils.db_utils import revise_db
                    revise_db(loan_update_command, (current_time, loan_id))

                    logger.info(f"已清理小额债务: 贷款 #{loan_id} 剩余债务已设为0")
                    cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"小额债务清理完成，共清理 {cleaned_count} 笔债务")
            else:
                logger.debug("没有发现需要清理的小额债务")

        except Exception as e:
            logger.error(f"清理小额债务失败: {e}")

    def generate_pnl_chart(self, user_id: int, group_id: int) -> Optional[bytes]:
        """生成盈亏折线图，包含统计信息"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # 使用非GUI后端
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            from scipy.ndimage import uniform_filter1d
            import io
            import os
            from datetime import datetime

            # 设置字体 - 处理中文字体问题
            import matplotlib.font_manager as fm

            # 查找系统中可用的字体
            font_path = None
            for font in fm.findSystemFonts():
                if 'arial' in font.lower() or 'helvetica' in font.lower() or 'dejavu' in font.lower():
                    font_path = font
                    break

            if font_path:
                plt.rcParams['font.sans-serif'] = [fm.FontProperties(fname=font_path).get_name()]
            else:
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.family'] = 'sans-serif'

            # 获取完整交易历史
            history_result = TradingRepository.get_full_trading_history(user_id, group_id)
            if not history_result["success"] or not history_result["history"]:
                return None

            history = history_result["history"]

            if len(history) < 2:
                return None  # 至少需要2个数据点才能绘制有意义的图表

            # 计算累计盈亏
            cumulative_pnl = 0.0
            pnl_values = [0.0]  # 起始点
            dates = [None]  # 对应的日期
            min_pnl = 0.0
            max_pnl = 0.0
            min_date = None
            max_date = None

            for trade in history:
                cumulative_pnl += trade['pnl']
                pnl_values.append(cumulative_pnl)
                dates.append(trade['created_at'])

                # 记录最低点和最高点
                if cumulative_pnl < min_pnl:
                    min_pnl = cumulative_pnl
                    min_date = trade['created_at']
                if cumulative_pnl > max_pnl:
                    max_pnl = cumulative_pnl
                    max_date = trade['created_at']

            # 获取胜率统计数据
            win_rate_result = TradingRepository.get_win_rate(user_id, group_id)
            win_rate_data = win_rate_result if win_rate_result["success"] else None

            # 获取账户信息
            account = self.get_or_create_account(user_id, group_id)

            # 创建类似网页grid的布局：图表占9，统计信息占3
            fig = plt.figure(figsize=(16, 12))

            # 使用GridSpec创建不规则布局
            # 图表区域占主要空间（9/12），统计信息占右侧小块（3/12）
            gs = fig.add_gridspec(12, 12, hspace=0.4, wspace=0.4)

            # 主图表 - 盈亏曲线（占据9/12的空间）
            ax1 = fig.add_subplot(gs[:, :9])  # 所有行，前9列
            ax1.set_facecolor('#f8f9fa')

            # 绘制平滑曲线
            if len(pnl_values) > 3:
                # 使用均匀滤波器平滑曲线
                window_size = max(3, len(pnl_values) // 10)  # 动态窗口大小
                smoothed_pnl = uniform_filter1d(pnl_values, size=window_size)
                ax1.plot(smoothed_pnl, color='#00ff88', linewidth=3, alpha=0.8, label='PnL Curve')
            else:
                ax1.plot(pnl_values, color='#00ff88', linewidth=3, alpha=0.8, label='PnL Curve')

            # 绘制原始折线
            ax1.plot(pnl_values, color='#0088ff', linewidth=1, alpha=0.6, linestyle='--', label='Raw Data')

            # 标记最低点和最高点
            if min_date:
                min_idx = dates.index(min_date) + 1
                ax1.scatter(min_idx, min_pnl, color='red', s=100, zorder=5, marker='v', label=f'Lowest: {min_pnl:.2f}')
                ax1.annotate(f'Low: {min_pnl:.2f}', xy=(min_idx, min_pnl),
                            xytext=(10, -20), textcoords='offset points',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                            fontsize=12, color='white')

            if max_date:
                max_idx = dates.index(max_date) + 1
                ax1.scatter(max_idx, max_pnl, color='green', s=100, zorder=5, marker='^', label=f'Highest: {max_pnl:.2f}')
                ax1.annotate(f'High: {max_pnl:.2f}', xy=(max_idx, max_pnl),
                            xytext=(10, 20), textcoords='offset points',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='green', alpha=0.7),
                            fontsize=12, color='white')

            # 添加零线
            ax1.axhline(y=0, color='gray', linestyle='-', alpha=0.5, linewidth=1)
            ax1.set_title('Trading PnL Chart', fontsize=16, fontweight='bold', pad=20)
            ax1.set_xlabel('Trade Count', fontsize=12)
            ax1.set_ylabel('Cumulative PnL (USDT)', fontsize=12)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.legend(loc='upper left', fontsize=10)

            # 统计信息子图（右侧3/12空间的上半部分）
            ax2 = fig.add_subplot(gs[:6, 9:])  # 前6行，9-11列
            ax2.set_facecolor('#f8f9fa')
            ax2.axis('off')

            # 添加统计信息
            win_rate_percent = f"{win_rate_data['win_rate']:.1f}%" if win_rate_data and 'win_rate' in win_rate_data else '0.0%'
            avg_holding_time = win_rate_data['avg_holding_time'] if win_rate_data and 'avg_holding_time' in win_rate_data else 0.0
            avg_win = win_rate_data['avg_win'] if win_rate_data and 'avg_win' in win_rate_data else 0.0
            avg_loss = win_rate_data['avg_loss'] if win_rate_data and 'avg_loss' in win_rate_data else 0.0
            profit_loss_ratio = win_rate_data['profit_loss_ratio'] if win_rate_data and 'profit_loss_ratio' in win_rate_data else 0.0
            avg_position_size = win_rate_data['avg_position_size'] if win_rate_data and 'avg_position_size' in win_rate_data else 0.0
            total_position_size = win_rate_data['total_position_size'] if win_rate_data and 'total_position_size' in win_rate_data else 0.0
            fee_contribution = win_rate_data['fee_contribution'] if win_rate_data and 'fee_contribution' in win_rate_data else 0.0

            stats_text = f"""PnL Statistics

Total PnL: {account['total_pnl']:+.2f} USDT
Current Balance: {account['balance']:.2f} USDT

Trading Stats:
Total Trades: {win_rate_data['total_trades'] if win_rate_data else 0}
Winning Trades: {win_rate_data['winning_trades'] if win_rate_data else 0}
Losing Trades: {win_rate_data['losing_trades'] if win_rate_data else 0}
Liquidations: {win_rate_data['liquidated_trades'] if win_rate_data else 0}
Win Rate: {win_rate_percent}

Performance:
Avg Holding Time: {avg_holding_time:.1f}h
Avg Profit: {avg_win:+.2f} USDT
Avg Loss: {avg_loss:+.2f} USDT
Profit/Loss Ratio: {profit_loss_ratio:.2f}
Avg Position Size: ${avg_position_size:.0f}
Total Volume: ${total_position_size:.0f}
Fee Contribution: ${fee_contribution:.2f}
            """

            ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes,
                    fontsize=12, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

            # 币种统计子图（右侧3/12空间的下半部分）
            ax3 = fig.add_subplot(gs[6:, 9:])  # 后6行，9-11列
            ax3.set_facecolor('#f8f9fa')
            ax3.axis('off')

            # 获取币种统计
            symbol_stats_text = "Symbol Statistics\n\n" if win_rate_data and win_rate_data.get('most_profitable_symbol') else "No Symbol Stats"

            if win_rate_data and win_rate_data.get('most_profitable_symbol'):
                symbol_stats_text += f"""Best Symbol: {win_rate_data['most_profitable_symbol'].replace('/USDT', '')}
PnL: {win_rate_data['most_profitable_pnl']:+.0f} USDT
Avg: {win_rate_data['most_profitable_avg_pnl']:+.1f}

Worst Symbol: {win_rate_data['most_loss_symbol'].replace('/USDT', '')}
PnL: {win_rate_data['most_loss_pnl']:+.0f} USDT
Avg: {win_rate_data['most_loss_avg_pnl']:+.1f}

Most Traded: {win_rate_data['most_traded_symbol'].replace('/USDT', '')}
Trades: {win_rate_data['most_traded_count']}
Avg: {win_rate_data['most_traded_avg_pnl']:+.1f}
                """

            ax3.text(0.05, 0.95, symbol_stats_text, transform=ax3.transAxes,
                    fontsize=11, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

            # 设置主标题
            fig.suptitle('Trading PnL Analysis Report', fontsize=18, fontweight='bold', y=0.98)

            # 美化图表
            plt.tight_layout()

            # 将图表保存为bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor='#f0f0f0', edgecolor='none')
            buf.seek(0)
            image_bytes = buf.read()
            plt.close()

            return image_bytes

        except Exception as e:
            logger.error(f"生成盈亏图表失败: {e}")
            return None


# 全局交易服务实例
trading_service = TradingService()