"""trading_repository.py - 交易相关的数据库操作"""

import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

from utils.db_utils import query_db, revise_db
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class TradingRepository:
    """交易相关的数据库操作"""

    @staticmethod
    def get_account(user_id: int, group_id: int) -> dict:
        """获取用户交易账户信息"""
        try:
            command = "SELECT * FROM trading_accounts WHERE user_id = ? AND group_id = ?"
            result = query_db(command, (user_id, group_id))
            
            if result:
                account = result[0]
                return {
                    "success": True,
                    "account": {
                        "user_id": account[0],
                        "group_id": account[1],
                        "balance": float(account[2]),
                        "total_pnl": float(account[3]),
                        "created_at": account[4],
                        "updated_at": account[5]
                    }
                }
            else:
                return {
                    "success": True,
                    "account": None
                }
        except Exception as e:
            logger.error(f"获取交易账户失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def create_account(user_id: int, group_id: int, initial_balance: float = 1000.0) -> dict:
        """创建用户交易账户"""
        try:
            now = datetime.datetime.now()
            command = """
                INSERT INTO trading_accounts (user_id, group_id, balance, total_pnl, created_at, updated_at)
                VALUES (?, ?, ?, 0.0, ?, ?)
            """
            revise_db(command, (user_id, group_id, initial_balance, now, now))
            
            return {
                "success": True,
                "account": {
                    "user_id": user_id,
                    "group_id": group_id,
                    "balance": initial_balance,
                    "total_pnl": 0.0,
                    "created_at": now,
                    "updated_at": now
                }
            }
        except Exception as e:
            logger.error(f"创建交易账户失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def update_account_balance(user_id: int, group_id: int, new_balance: float, pnl_change: float = 0.0) -> dict:
        """更新用户账户余额和总盈亏"""
        try:
            now = datetime.datetime.now()
            command = """
                UPDATE trading_accounts 
                SET balance = ?, total_pnl = total_pnl + ?, updated_at = ?
                WHERE user_id = ? AND group_id = ?
            """
            revise_db(command, (new_balance, pnl_change, now, user_id, group_id))
            
            return {"success": True}
        except Exception as e:
            logger.error(f"更新账户余额失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_positions(user_id: int, group_id: int) -> dict:
        """获取用户所有持仓"""
        try:
            command = "SELECT * FROM trading_positions WHERE user_id = ? AND group_id = ?"
            result = query_db(command, (user_id, group_id))
            
            positions = []
            for row in result:
                positions.append({
                    "id": row[0],
                    "user_id": row[1],
                    "group_id": row[2],
                    "symbol": row[3],
                    "side": row[4],
                    "size": float(row[5]),
                    "entry_price": float(row[6]),
                    "current_price": float(row[7]) if row[7] else 0.0,
                    "pnl": float(row[8]) if row[8] else 0.0,
                    "liquidation_price": float(row[9]) if row[9] else 0.0,
                    "created_at": row[10],
                    "updated_at": row[11]
                })
            
            return {
                "success": True,
                "positions": positions
            }
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_position(user_id: int, group_id: int, symbol: str, side: str) -> dict:
        """获取特定持仓"""
        try:
            command = "SELECT * FROM trading_positions WHERE user_id = ? AND group_id = ? AND symbol = ? AND side = ?"
            result = query_db(command, (user_id, group_id, symbol, side))
            
            if result:
                row = result[0]
                position = {
                    "id": row[0],
                    "user_id": row[1],
                    "group_id": row[2],
                    "symbol": row[3],
                    "side": row[4],
                    "size": float(row[5]),
                    "entry_price": float(row[6]),
                    "current_price": float(row[7]) if row[7] else 0.0,
                    "pnl": float(row[8]) if row[8] else 0.0,
                    "liquidation_price": float(row[9]) if row[9] else 0.0,
                    "created_at": row[10],
                    "updated_at": row[11]
                }
                return {
                    "success": True,
                    "position": position
                }
            else:
                return {
                    "success": True,
                    "position": None
                }
        except Exception as e:
            logger.error(f"获取特定持仓失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def create_position(user_id: int, group_id: int, symbol: str, side: str, size: float, 
                       entry_price: float, liquidation_price: float) -> dict:
        """创建新持仓"""
        try:
            now = datetime.datetime.now()
            command = """
                INSERT INTO trading_positions 
                (user_id, group_id, symbol, side, size, entry_price, liquidation_price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            revise_db(command, (user_id, group_id, symbol, side, size, entry_price, liquidation_price, now, now))
            
            return {"success": True}
        except Exception as e:
            logger.error(f"创建持仓失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def update_position(user_id: int, group_id: int, symbol: str, side: str, new_size: float, 
                       new_entry_price: float, new_liquidation_price: float) -> dict:
        """更新持仓"""
        try:
            now = datetime.datetime.now()
            command = """
                UPDATE trading_positions 
                SET size = ?, entry_price = ?, liquidation_price = ?, updated_at = ?
                WHERE user_id = ? AND group_id = ? AND symbol = ? AND side = ?
            """
            revise_db(command, (new_size, new_entry_price, new_liquidation_price, now, user_id, group_id, symbol, side))
            
            return {"success": True}
        except Exception as e:
            logger.error(f"更新持仓失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def delete_position(user_id: int, group_id: int, symbol: str, side: str) -> dict:
        """删除持仓"""
        try:
            command = "DELETE FROM trading_positions WHERE user_id = ? AND group_id = ? AND symbol = ? AND side = ?"
            revise_db(command, (user_id, group_id, symbol, side))
            
            return {"success": True}
        except Exception as e:
            logger.error(f"删除持仓失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_all_positions() -> dict:
        """获取所有持仓用于强平检查"""
        try:
            command = "SELECT * FROM trading_positions"
            result = query_db(command)
            
            positions = []
            for row in result:
                positions.append({
                    "id": row[0],
                    "user_id": row[1],
                    "group_id": row[2],
                    "symbol": row[3],
                    "side": row[4],
                    "size": float(row[5]),
                    "entry_price": float(row[6]),
                    "current_price": float(row[7]) if row[7] else 0.0,
                    "pnl": float(row[8]) if row[8] else 0.0,
                    "liquidation_price": float(row[9]) if row[9] else 0.0,
                    "created_at": row[10],
                    "updated_at": row[11]
                })
            
            return {
                "success": True,
                "positions": positions
            }
        except Exception as e:
            logger.error(f"获取所有持仓失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def add_trading_history(user_id: int, group_id: int, action: str, symbol: str, side: str, 
                           size: float, price: float, pnl: float = 0.0) -> dict:
        """添加交易历史记录"""
        try:
            now = datetime.datetime.now()
            command = """
                INSERT INTO trading_history 
                (user_id, group_id, action, symbol, side, size, price, pnl, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            revise_db(command, (user_id, group_id, action, symbol, side, size, price, pnl, now))
            
            return {"success": True}
        except Exception as e:
            logger.error(f"添加交易历史失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_begging_record(user_id: int, group_id: int) -> dict:
        """获取用户今日救济金记录"""
        try:
            today = datetime.date.today()
            command = "SELECT * FROM begging_records WHERE user_id = ? AND group_id = ? AND DATE(created_at) = ?"
            result = query_db(command, (user_id, group_id, today))
            
            if result:
                row = result[0]
                record = {
                    "id": row[0],
                    "user_id": row[1],
                    "group_id": row[2],
                    "amount": float(row[3]),
                    "created_at": row[4]
                }
                return {
                    "success": True,
                    "record": record
                }
            else:
                return {
                    "success": True,
                    "record": None
                }
        except Exception as e:
            logger.error(f"获取救济金记录失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def create_begging_record(user_id: int, group_id: int, amount: float) -> dict:
        """创建救济金记录"""
        try:
            now = datetime.datetime.now()
            command = """
                INSERT INTO begging_records (user_id, group_id, amount, created_at)
                VALUES (?, ?, ?, ?)
            """
            revise_db(command, (user_id, group_id, amount, now))
            
            return {"success": True}
        except Exception as e:
            logger.error(f"创建救济金记录失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_price_cache(symbol: str) -> dict:
        """获取价格缓存"""
        try:
            command = "SELECT * FROM price_cache WHERE symbol = ?"
            result = query_db(command, (symbol,))
            
            if result:
                row = result[0]
                cache = {
                    "symbol": row[0],
                    "price": float(row[1]),
                    "updated_at": row[2]
                }
                return {
                    "success": True,
                    "cache": cache
                }
            else:
                return {
                    "success": True,
                    "cache": None
                }
        except Exception as e:
            logger.error(f"获取价格缓存失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def update_price_cache(symbol: str, price: float) -> dict:
        """更新价格缓存"""
        try:
            now = datetime.datetime.now()
            # 使用 INSERT OR REPLACE 来处理插入或更新
            command = """
                INSERT OR REPLACE INTO price_cache (symbol, price, updated_at)
                VALUES (?, ?, ?)
            """
            revise_db(command, (symbol, price, now))
            
            return {"success": True}
        except Exception as e:
            logger.error(f"更新价格缓存失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }