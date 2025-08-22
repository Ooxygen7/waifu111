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

class TradingService:
    """
    模拟盘交易服务
    处理开仓、平仓、查询仓位、救济金等功能
    """
    
    def __init__(self):
        # 初始化交易所连接(使用币安作为价格源)
        self.exchange = ccxt.binance({
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
            price = float(ticker['last'])
            
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
                
                # 计算新的强平价格
                liquidation_price = self._calculate_liquidation_price(
                    user_id, group_id, symbol, side, new_size, new_entry
                )
                
                update_result = TradingRepository.update_position(
                    user_id, group_id, symbol, side, new_size, new_entry, liquidation_price
                )
                if not update_result["success"]:
                    return {'success': False, 'message': '更新仓位失败'}
                
                message = f"加仓成功！\n{symbol} {side.upper()} +{size:.2f} USDT\n平均开仓价: {new_entry:.4f}\n总仓位: {new_size:.2f} USDT"
            else:
                # 新开仓位
                liquidation_price = self._calculate_liquidation_price(
                    user_id, group_id, symbol, side, size, current_price
                )
                
                create_result = TradingRepository.create_position(
                    user_id, group_id, symbol, side, size, current_price, liquidation_price
                )
                if not create_result["success"]:
                    return {'success': False, 'message': '创建仓位失败'}
                
                message = f"开仓成功！\n{symbol} {side.upper()} {size:.2f} USDT\n开仓价: {current_price:.4f}\n强平价: {liquidation_price:.4f}"
            
            # 杠杆交易不扣除余额，余额就是保证金
            # 仓位占用保证金，但不从余额中扣除
            
            # 记录交易历史
            TradingRepository.add_trading_history(
                user_id, group_id, 'open', symbol, side, size, current_price
            )
            
            return {'success': True, 'message': message}
                
        except Exception as e:
            logger.error(f"开仓失败: {e}")
            return {'success': False, 'message': '开仓失败，请稍后重试'}
    
    async def close_position(self, user_id: int, group_id: int, symbol: str, side: str, size: float = None) -> Dict:
        """
        平仓操作
        size: 平仓大小，None表示全部平仓
        """
        try:
            # 获取当前价格
            current_price = await self.get_current_price(symbol)
            if current_price <= 0:
                return {'success': False, 'message': f'无法获取 {symbol} 价格'}
            
            # 获取仓位信息
            position_result = TradingRepository.get_position(user_id, group_id, symbol, side)
            if not position_result["success"] or not position_result["position"]:
                return {'success': False, 'message': f'没有找到 {symbol} {side.upper()} 仓位'}
            
            position = position_result["position"]
            
            # 确定平仓大小
            close_size = size if size and size <= position['size'] else position['size']
            
            # 计算盈亏
            pnl = self._calculate_pnl(position['entry_price'], current_price, close_size, side)
            
            if close_size >= position['size']:
                # 全部平仓
                delete_result = TradingRepository.delete_position(user_id, group_id, symbol, side)
                if not delete_result["success"]:
                    return {'success': False, 'message': '删除仓位失败'}
                message = f"平仓成功！\n{symbol} {side.upper()} -{close_size:.2f} USDT\n盈亏: {pnl:+.2f} USDT"
            else:
                # 部分平仓
                new_size = position['size'] - close_size
                update_result = TradingRepository.update_position(
                    user_id, group_id, symbol, side, new_size, position['entry_price'], position['liquidation_price']
                )
                if not update_result["success"]:
                    return {'success': False, 'message': '更新仓位失败'}
                message = f"部分平仓成功！\n{symbol} {side.upper()} -{close_size:.2f} USDT\n剩余仓位: {new_size:.2f} USDT\n盈亏: {pnl:+.2f} USDT"
            
            # 更新账户余额和总盈亏 - 杠杆交易只需要加上盈亏
            account = self.get_or_create_account(user_id, group_id)
            new_balance = account['balance'] + pnl
            new_total_pnl = account['total_pnl'] + pnl
            
            balance_result = TradingRepository.update_account_balance(user_id, group_id, new_balance, pnl)
            if not balance_result["success"]:
                return {'success': False, 'message': '更新账户余额失败'}
            
            # 记录交易历史
            TradingRepository.add_trading_history(
                user_id, group_id, 'close', symbol, side, close_size, current_price, pnl
            )
            
            return {'success': True, 'message': message}
                
        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return {'success': False, 'message': '平仓失败，请稍后重试'}
    
    async def get_positions(self, user_id: int, group_id: int) -> Dict:
        """获取用户所有仓位信息"""
        try:
            account = self.get_or_create_account(user_id, group_id)
            
            positions_result = TradingRepository.get_positions(user_id, group_id)
            if not positions_result["success"]:
                return {'success': False, 'message': '获取仓位信息失败'}
            
            positions = positions_result["positions"]
            
            if not positions:
                return {
                    'success': True,
                    'message': f"💰 余额: {account['balance']:.2f} USDT\n📊 总盈亏: {account['total_pnl']:+.2f} USDT\n📋 当前无持仓"
                }
            
            total_unrealized_pnl = 0
            position_text = []
            
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
                
                # 计算盈亏百分比
                pnl_percent = (unrealized_pnl / size) * 100
                
                position_text.append(
                    f"📈 {symbol} {side.upper()}\n"
                    f"   仓位: {size:.2f} USDT\n"
                    f"   开仓价: {entry_price:.4f}\n"
                    f"   当前价: {current_price:.4f}\n"
                    f"   盈亏: {unrealized_pnl:+.2f} USDT ({pnl_percent:+.2f}%)\n"
                    f"   强平价: {liquidation_price:.4f}"
                )
            
            # 计算浮动余额
            floating_balance = account['balance'] + total_unrealized_pnl
            
            message = (
                f"💰 余额: {account['balance']:.2f} USDT\n"
                f"📊 总盈亏: {account['total_pnl']:+.2f} USDT\n"
                f"💸 未实现盈亏: {total_unrealized_pnl:+.2f} USDT\n"
                f"🏦 浮动余额: {floating_balance:.2f} USDT\n\n"
                + "\n\n".join(position_text)
            )
            
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
            return (current_price - entry_price) / entry_price * size
        else:  # short
            return (entry_price - current_price) / entry_price * size
    
    def _calculate_liquidation_price(self, user_id: int, group_id: int, symbol: str, side: str, size: float, entry_price: float) -> float:
        """计算强平价格(维持保证金率1%)"""
        try:
            account = self.get_or_create_account(user_id, group_id)
            
            # 维持保证金率1%，当保证金率低于1%时强平
            maintenance_margin_rate = 0.01
            
            # 计算强平价格
            # 强平条件: (余额 + 浮盈) / 仓位价值 = 维持保证金率
            # 浮盈 = (当前价格 - 开仓价) * 仓位大小 / 开仓价 (做多)
            # 浮盈 = (开仓价 - 当前价格) * 仓位大小 / 开仓价 (做空)
            
            if side == 'long':
                # 做多: 余额 + (强平价 - 开仓价) * 仓位大小 / 开仓价 = 维持保证金率 * 仓位大小
                # 强平价 = 开仓价 * (1 - (余额 - 维持保证金率 * 仓位大小) / 仓位大小)
                liquidation_price = entry_price * (1 - (account['balance'] - maintenance_margin_rate * size) / size)
            else:
                # 做空: 余额 + (开仓价 - 强平价) * 仓位大小 / 开仓价 = 维持保证金率 * 仓位大小  
                # 强平价 = 开仓价 * (1 + (余额 - 维持保证金率 * 仓位大小) / 仓位大小)
                liquidation_price = entry_price * (1 + (account['balance'] - maintenance_margin_rate * size) / size)
            
            return max(liquidation_price, 0.0001)  # 确保价格为正
            
        except Exception as e:
            logger.error(f"计算强平价格失败: {e}")
            return entry_price * 0.8 if side == 'long' else entry_price * 1.2
    
    async def check_liquidations(self) -> List[Dict]:
        """检查所有仓位是否需要强平"""
        liquidated_positions = []
        
        try:
            all_positions_result = TradingRepository.get_all_positions()
            if not all_positions_result["success"]:
                return liquidated_positions
            
            positions = all_positions_result["positions"]
            
            for pos in positions:
                user_id = pos['user_id']
                group_id = pos['group_id']
                symbol = pos['symbol']
                side = pos['side']
                size = pos['size']
                entry_price = pos['entry_price']
                liquidation_price = pos['liquidation_price']
                
                # 获取当前价格
                current_price = await self.get_current_price(symbol)
                
                # 检查是否触发强平
                should_liquidate = False
                if side == 'long' and current_price <= liquidation_price:
                    should_liquidate = True
                elif side == 'short' and current_price >= liquidation_price:
                    should_liquidate = True
                
                if should_liquidate:
                    # 执行强平
                    liquidated_positions.append({
                        'user_id': user_id,
                        'group_id': group_id,
                        'symbol': symbol,
                        'side': side,
                        'size': size,
                        'liquidation_price': liquidation_price,
                        'current_price': current_price
                    })
                    
                    # 删除仓位并清零余额
                    TradingRepository.delete_position(user_id, group_id, symbol, side)
                    TradingRepository.update_account_balance(user_id, group_id, 0.0)
                    
                    # 记录强平历史
                    TradingRepository.add_trading_history(
                        user_id, group_id, 'liquidated', symbol, side, size, current_price, -size
                    )
        
        except Exception as e:
            logger.error(f"检查强平失败: {e}")
        
        return liquidated_positions

# 全局交易服务实例
trading_service = TradingService()