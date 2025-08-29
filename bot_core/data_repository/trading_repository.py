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
                        "trading_count": int(account[4]) if account[4] else 0,
                        "winning_trades": int(account[5]) if account[5] else 0,
                        "losing_trades": int(account[6]) if account[6] else 0,
                        "total_profit": float(account[7]) if account[7] else 0.0,
                        "total_loss": float(account[8]) if account[8] else 0.0,
                        "loan_count": int(account[9]) if account[9] else 0,
                        "total_loan_amount": float(account[10]) if account[10] else 0.0,
                        "total_repayment_amount": float(account[11]) if account[11] else 0.0,
                        "current_debt": float(account[12]) if account[12] else 0.0,
                        "total_fees": float(account[13]) if account[13] else 0.0,
                        "frozen_margin": float(account[14]) if account[14] else 0.0,
                        "created_at": account[15],
                        "updated_at": account[16]
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
    def get_order(order_id: str) -> dict:
        """获取单个订单信息"""
        try:
            command = "SELECT * FROM trading_orders WHERE order_id = ?"
            result = query_db(command, (order_id,))
            
            if result:
                row = result[0]
                order = {
                    "order_id": row[0],
                    "user_id": row[1],
                    "group_id": row[2],
                    "symbol": row[3],
                    "direction": row[4],
                    "role": row[5],
                    "order_type": row[6],
                    "operation": row[7],
                    "status": row[8],
                    "volume": float(row[9]),
                    "price": float(row[10]) if row[10] else None,
                    "tp_price": float(row[11]) if row[11] else None,
                    "sl_price": float(row[12]) if row[12] else None,
                    "margin_locked": float(row[13]) if row[13] else 0.0,
                    "fee_rate": float(row[14]) if row[14] else 0.0035,
                    "actual_fee": float(row[15]) if row[15] else 0.0,
                    "related_position_id": row[16],
                    "created_at": row[17],
                    "executed_at": row[18],
                    "cancelled_at": row[19]
                }
                return {
                    "success": True,
                    "order": order
                }
            else:
                return {
                    "success": True,
                    "order": None
                }
        except Exception as e:
            logger.error(f"获取订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_orders(user_id: int, group_id: int, status: str = None) -> dict:
        """获取用户订单列表"""
        try:
            if status:
                command = "SELECT * FROM trading_orders WHERE user_id = ? AND group_id = ? AND status = ? ORDER BY created_at DESC"
                result = query_db(command, (user_id, group_id, status))
            else:
                command = "SELECT * FROM trading_orders WHERE user_id = ? AND group_id = ? ORDER BY created_at DESC"
                result = query_db(command, (user_id, group_id))
            
            orders = []
            for row in result:
                orders.append({
                    "order_id": row[0],
                    "user_id": row[1],
                    "group_id": row[2],
                    "symbol": row[3],
                    "direction": row[4],
                    "role": row[5],
                    "order_type": row[6],
                    "operation": row[7],
                    "status": row[8],
                    "volume": float(row[9]),
                    "price": float(row[10]) if row[10] else None,
                    "tp_price": float(row[11]) if row[11] else None,
                    "sl_price": float(row[12]) if row[12] else None,
                    "margin_locked": float(row[13]) if row[13] else 0.0,
                    "fee_rate": float(row[14]) if row[14] else 0.0035,
                    "actual_fee": float(row[15]) if row[15] else 0.0,
                    "related_position_id": row[16],
                    "created_at": row[17],
                    "executed_at": row[18],
                    "cancelled_at": row[19]
                })
            
            return {
                "success": True,
                "orders": orders
            }
        except Exception as e:
            logger.error(f"获取订单列表失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_orders_by_type(order_type: str, status: str = "pending") -> dict:
        """根据订单类型获取订单列表"""
        try:
            command = "SELECT * FROM trading_orders WHERE order_type = ? AND status = ? ORDER BY created_at ASC"
            result = query_db(command, (order_type, status))
            
            orders = []
            for row in result:
                orders.append({
                    "order_id": row[0],
                    "user_id": row[1],
                    "group_id": row[2],
                    "symbol": row[3],
                    "direction": row[4],
                    "role": row[5],
                    "order_type": row[6],
                    "operation": row[7],
                    "status": row[8],
                    "volume": float(row[9]),
                    "price": float(row[10]) if row[10] else None,
                    "tp_price": float(row[11]) if row[11] else None,
                    "sl_price": float(row[12]) if row[12] else None,
                    "margin_locked": float(row[13]) if row[13] else 0.0,
                    "fee_rate": float(row[14]) if row[14] else 0.0035,
                    "actual_fee": float(row[15]) if row[15] else 0.0,
                    "related_position_id": row[16],
                    "created_at": row[17],
                    "executed_at": row[18],
                    "cancelled_at": row[19]
                })
            
            return {
                "success": True,
                "orders": orders
            }
        except Exception as e:
            logger.error(f"根据类型获取订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def execute_order(order_id: str, execution_price: float) -> dict:
        """执行订单"""
        try:
            now = datetime.datetime.now().isoformat()
            command = "UPDATE trading_orders SET status = 'executed', executed_at = ? WHERE order_id = ?"
            revise_db(command, (now, order_id))
            
            return {
                "success": True,
                "executed": True
            }
        except Exception as e:
            logger.error(f"执行订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def cancel_order(order_id: str) -> dict:
        """取消订单"""
        try:
            now = datetime.datetime.now().isoformat()
            command = "UPDATE trading_orders SET status = 'cancelled', cancelled_at = ? WHERE order_id = ?"
            revise_db(command, (now, order_id))
            
            return {
                "success": True,
                "cancelled": True
            }
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def create_loan(user_id: int, group_id: int, principal: float) -> dict:
        """创建新贷款记录"""
        try:
            current_time = datetime.datetime.now().isoformat()
            # 计算初始欠款(本金 + 10%手续费)
            initial_debt = principal * 1.1
            
            command = """
                INSERT INTO loans (user_id, group_id, principal, remaining_debt, 
                                 loan_time, last_interest_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            result = revise_db(command, (user_id, group_id, principal, initial_debt,
                                       current_time, current_time, current_time))
            
            if result:
                return {
                    "success": True,
                    "loan_id": result,
                    "principal": principal,
                    "initial_debt": initial_debt
                }
            else:
                return {
                    "success": False,
                    "error": "创建贷款记录失败"
                }
        except Exception as e:
            logger.error(f"创建贷款记录失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_active_loans(user_id: int, group_id: int) -> dict:
        """获取用户的活跃贷款记录"""
        try:
            command = """
                SELECT id, principal, remaining_debt, interest_rate, initial_fee,
                       loan_time, last_interest_time, status, created_at
                FROM loans 
                WHERE user_id = ? AND group_id = ? AND status = 'active'
                ORDER BY created_at DESC
            """
            
            result = query_db(command, (user_id, group_id))
            
            loans = []
            if result:
                for row in result:
                    loans.append({
                        "id": row[0],
                        "principal": float(row[1]),
                        "remaining_debt": float(row[2]),
                        "interest_rate": float(row[3]),
                        "initial_fee": float(row[4]),
                        "loan_time": row[5],
                        "last_interest_time": row[6],
                        "status": row[7],
                        "created_at": row[8]
                    })
            
            return {
                "success": True,
                "loans": loans
            }
        except Exception as e:
            logger.error(f"获取活跃贷款记录失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def update_loan_debt(loan_id: int, new_debt: float, last_interest_time: str = None) -> dict:
        """更新贷款欠款金额和计息时间"""
        try:
            if last_interest_time is None:
                last_interest_time = datetime.datetime.now().isoformat()
            
            command = """
                UPDATE loans 
                SET remaining_debt = ?, last_interest_time = ?, updated_at = ?
                WHERE id = ?
            """
            
            current_time = datetime.datetime.now().isoformat()
            result = revise_db(command, (new_debt, last_interest_time, current_time, loan_id))
            
            return {
                "success": bool(result),
                "updated": bool(result)
            }
        except Exception as e:
            logger.error(f"更新贷款欠款失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def repay_loan(loan_id: int, user_id: int, group_id: int, amount: float) -> dict:
        """还款操作"""
        try:
            current_time = datetime.datetime.now().isoformat()
            
            # 获取当前贷款信息
            loan_query = "SELECT remaining_debt FROM loans WHERE id = ? AND user_id = ? AND group_id = ?"
            loan_result = query_db(loan_query, (loan_id, user_id, group_id))
            
            if not loan_result:
                return {
                    "success": False,
                    "error": "贷款记录不存在"
                }
            
            current_debt = float(loan_result[0][0])
            remaining_after = max(0, current_debt - amount)
            
            # 记录还款
            repayment_command = """
                INSERT INTO loan_repayments (loan_id, user_id, group_id, amount, 
                                           repayment_time, remaining_after, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            repayment_result = revise_db(repayment_command, (loan_id, user_id, group_id, amount,
                                                           current_time, remaining_after, current_time))
            
            if not repayment_result:
                return {
                    "success": False,
                    "error": "记录还款失败"
                }
            
            # 更新贷款状态
            if remaining_after <= 0:
                # 完全还清
                loan_update_command = """
                    UPDATE loans 
                    SET remaining_debt = 0, status = 'paid_off', updated_at = ?
                    WHERE id = ?
                """
                revise_db(loan_update_command, (current_time, loan_id))
            else:
                # 部分还款
                loan_update_command = """
                    UPDATE loans 
                    SET remaining_debt = ?, updated_at = ?
                    WHERE id = ?
                """
                revise_db(loan_update_command, (remaining_after, current_time, loan_id))
            
            return {
                "success": True,
                "repayment_id": repayment_result,
                "amount": amount,
                "remaining_after": remaining_after,
                "paid_off": remaining_after <= 0
            }
        except Exception as e:
            logger.error(f"还款操作失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_loan_summary(user_id: int, group_id: int) -> dict:
        """获取用户贷款汇总信息"""
        try:
            # 获取活跃贷款统计
            active_loans_query = """
                SELECT COUNT(*) as loan_count, 
                       COALESCE(SUM(remaining_debt), 0) as total_debt,
                       COALESCE(SUM(principal), 0) as total_principal
                FROM loans 
                WHERE user_id = ? AND group_id = ? AND status = 'active'
            """
            
            active_result = query_db(active_loans_query, (user_id, group_id))
            
            # 获取历史贷款统计
            total_loans_query = """
                SELECT COUNT(*) as total_loans,
                       COALESCE(SUM(principal), 0) as total_borrowed
                FROM loans 
                WHERE user_id = ? AND group_id = ?
            """
            
            total_result = query_db(total_loans_query, (user_id, group_id))
            
            # 获取还款统计
            repayment_query = """
                SELECT COALESCE(SUM(amount), 0) as total_repaid
                FROM loan_repayments 
                WHERE user_id = ? AND group_id = ?
            """
            
            repayment_result = query_db(repayment_query, (user_id, group_id))
            
            summary = {
                "active_loan_count": 0,
                "total_debt": 0.0,
                "total_principal": 0.0,
                "total_loans": 0,
                "total_borrowed": 0.0,
                "total_repaid": 0.0
            }
            
            if active_result:
                summary["active_loan_count"] = active_result[0][0] or 0
                summary["total_debt"] = float(active_result[0][1] or 0)
                summary["total_principal"] = float(active_result[0][2] or 0)
            
            if total_result:
                summary["total_loans"] = total_result[0][0] or 0
                summary["total_borrowed"] = float(total_result[0][1] or 0)
            
            if repayment_result:
                summary["total_repaid"] = float(repayment_result[0][0] or 0)
            
            return {
                "success": True,
                "summary": summary
            }
        except Exception as e:
            logger.error(f"获取贷款汇总失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_group_profit_ranking(group_id: int, limit: int = 5) -> dict:
        """获取群组盈利排行榜"""
        try:
            command = """
                SELECT user_id, total_pnl 
                FROM trading_accounts 
                WHERE group_id = ? AND total_pnl > 0
                ORDER BY total_pnl DESC 
                LIMIT ?
            """
            result = query_db(command, (group_id, limit))
            
            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "total_pnl": float(row[1])
                })
            
            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取群组盈利排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_group_loss_ranking(group_id: int, limit: int = 5) -> dict:
        """获取群组亏损排行榜"""
        try:
            command = """
                SELECT user_id, total_pnl 
                FROM trading_accounts 
                WHERE group_id = ? AND total_pnl < 0
                ORDER BY total_pnl ASC 
                LIMIT ?
            """
            result = query_db(command, (group_id, limit))
            
            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "total_pnl": float(row[1])
                })
            
            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取群组亏损排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_group_balance_accounts(group_id: int) -> dict:
        """获取群组所有账户余额信息"""
        try:
            command = """
                SELECT ta.user_id, ta.balance
                FROM trading_accounts ta
                WHERE ta.group_id = ?
            """
            result = query_db(command, (group_id,))
            
            accounts = []
            for row in result:
                accounts.append({
                    "user_id": row[0],
                    "balance": float(row[1])
                })
            
            return {
                "success": True,
                "accounts": accounts
            }
        except Exception as e:
            logger.error(f"获取群组账户余额失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_group_liquidation_ranking(group_id: int, limit: int = 10) -> dict:
        """获取群组爆仓次数排行榜"""
        try:
            command = """
                SELECT user_id, COUNT(*) as liquidation_count
                FROM trading_history 
                WHERE group_id = ? AND action = 'liquidated'
                GROUP BY user_id 
                ORDER BY liquidation_count DESC 
                LIMIT ?
            """
            result = query_db(command, (group_id, limit))
            
            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "liquidation_count": int(row[1])
                })
            
            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取群组爆仓排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_global_profit_ranking(limit: int = 5) -> dict:
        """获取跨群盈利排行榜"""
        try:
            command = """
                SELECT ta.user_id, MAX(ta.total_pnl) as best_pnl, ta.group_id, g.group_name
                FROM trading_accounts ta
                LEFT JOIN groups g ON ta.group_id = g.group_id
                WHERE ta.total_pnl > 0
                GROUP BY ta.user_id 
                ORDER BY best_pnl DESC 
                LIMIT ?
            """
            result = query_db(command, (limit,))
            
            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "total_pnl": float(row[1]),
                    "group_id": row[2],
                    "group_name": row[3] or f"群组{row[2]}"
                })
            
            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取跨群盈利排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_global_loss_ranking(limit: int = 5) -> dict:
        """获取跨群亏损排行榜"""
        try:
            command = """
                SELECT ta.user_id, MIN(ta.total_pnl) as worst_pnl, ta.group_id, g.group_name
                FROM trading_accounts ta
                LEFT JOIN groups g ON ta.group_id = g.group_id
                WHERE ta.total_pnl < 0
                GROUP BY ta.user_id 
                ORDER BY worst_pnl ASC 
                LIMIT ?
            """
            result = query_db(command, (limit,))
            
            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "total_pnl": float(row[1]),
                    "group_id": row[2],
                    "group_name": row[3] or f"群组{row[2]}"
                })
            
            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取跨群亏损排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_global_balance_accounts() -> dict:
        """获取跨群所有账户余额信息"""
        try:
            command = """
                SELECT ta.user_id, ta.balance, ta.group_id, g.group_name
                FROM trading_accounts ta
                LEFT JOIN groups g ON ta.group_id = g.group_id
            """
            result = query_db(command)
            
            accounts = []
            for row in result:
                accounts.append({
                    "user_id": row[0],
                    "balance": float(row[1]),
                    "group_id": row[2],
                    "group_name": row[3] or f"群组{row[2]}"
                })
            
            return {
                "success": True,
                "accounts": accounts
            }
        except Exception as e:
            logger.error(f"获取跨群账户余额失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_global_liquidation_ranking() -> dict:
        """获取跨群爆仓次数排行榜"""
        try:
            command = """
                SELECT th.user_id, COUNT(*) as liquidation_count, th.group_id, g.group_name
                FROM trading_history th
                LEFT JOIN groups g ON th.group_id = g.group_id
                WHERE th.action = 'liquidated'
                GROUP BY th.user_id, th.group_id
            """
            result = query_db(command)

            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "liquidation_count": int(row[1]),
                    "group_id": row[2],
                    "group_name": row[3] or f"群组{row[2]}"
                })

            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取跨群爆仓排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_group_trading_volume_ranking(group_id: int, limit: int = 10) -> dict:
        """获取群组交易量排行榜"""
        try:
            command = """
                SELECT user_id, COALESCE(SUM(size), 0) as total_volume
                FROM trading_history
                WHERE group_id = ? AND action IN ('open', 'close', 'liquidated')
                GROUP BY user_id
                ORDER BY total_volume DESC
                LIMIT ?
            """
            result = query_db(command, (group_id, limit))

            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "total_volume": float(row[1])
                })

            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取群组交易量排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_global_trading_volume_ranking(limit: int = 10) -> dict:
        """获取跨群交易量排行榜"""
        try:
            command = """
                SELECT th.user_id, COALESCE(SUM(th.size), 0) as total_volume, th.group_id, g.group_name
                FROM trading_history th
                LEFT JOIN groups g ON th.group_id = g.group_id
                WHERE th.action IN ('open', 'close', 'liquidated')
                GROUP BY th.user_id, th.group_id
                ORDER BY total_volume DESC
                LIMIT ?
            """
            result = query_db(command, (limit,))

            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "total_volume": float(row[1]),
                    "group_id": row[2],
                    "group_name": row[3] or f"群组{row[2]}"
                })

            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取跨群交易量排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_group_deadbeat_ranking(group_id: int, limit: int = 5) -> dict:
        """获取群组老赖排行榜 - 按欠款金额/净余额比例排序"""
        try:
            command = """
                SELECT 
                    l.user_id,
                    SUM(l.remaining_debt) as total_debt,
                    ta.balance,
                    COALESCE(SUM(l.principal / 1.1), 0) as total_loan_received,
                    (ta.balance - COALESCE(SUM(l.principal / 1.1), 0)) as net_balance,
                    CASE 
                        WHEN (ta.balance - COALESCE(SUM(l.principal / 1.1), 0)) > 0 
                        THEN SUM(l.remaining_debt) / (ta.balance - COALESCE(SUM(l.principal / 1.1), 0))
                        ELSE 999999
                    END as debt_ratio,
                    MIN(l.loan_time) as earliest_loan_time,
                    MAX(l.last_interest_time) as latest_interest_time
                FROM loans l
                JOIN trading_accounts ta ON l.user_id = ta.user_id AND l.group_id = ta.group_id
                WHERE l.group_id = ? AND l.status = 'active' AND l.remaining_debt > 0
                GROUP BY l.user_id, ta.balance
                ORDER BY debt_ratio DESC
                LIMIT ?
            """
            result = query_db(command, (group_id, limit))
            
            ranking = []
            for row in result:
                ranking.append({
                "user_id": row[0],
                "total_debt": float(row[1]),
                "balance": float(row[2]),
                "total_loan_received": float(row[3]),
                "net_balance": float(row[4]),
                "debt_ratio": float(row[5]),
                "earliest_loan_time": row[6],
                "latest_interest_time": row[7]
            })
            
            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取群组老赖排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_global_deadbeat_ranking(limit: int = 5) -> dict:
        """获取跨群老赖排行榜 - 按欠款金额/净余额比例排序"""
        try:
            command = """
                SELECT 
                    l.user_id,
                    l.group_id,
                    g.group_name,
                    SUM(l.remaining_debt) as total_debt,
                    ta.balance,
                    COALESCE(SUM(l.principal / 1.1), 0) as total_loan_received,
                    (ta.balance - COALESCE(SUM(l.principal / 1.1), 0)) as net_balance,
                    CASE 
                        WHEN (ta.balance - COALESCE(SUM(l.principal / 1.1), 0)) > 0 
                        THEN SUM(l.remaining_debt) / (ta.balance - COALESCE(SUM(l.principal / 1.1), 0))
                        ELSE 999999
                    END as debt_ratio,
                    MIN(l.loan_time) as earliest_loan_time,
                    MAX(l.last_interest_time) as latest_interest_time
                FROM loans l
                JOIN trading_accounts ta ON l.user_id = ta.user_id AND l.group_id = ta.group_id
                LEFT JOIN groups g ON l.group_id = g.group_id
                WHERE l.status = 'active' AND l.remaining_debt > 0
                GROUP BY l.user_id, l.group_id, ta.balance
                ORDER BY debt_ratio DESC
                LIMIT ?
            """
            result = query_db(command, (limit,))
            
            ranking = []
            for row in result:
                ranking.append({
                    "user_id": row[0],
                    "group_id": row[1],
                    "group_name": row[2] or f"群组{row[1]}",
                    "total_debt": float(row[3]),
                    "balance": float(row[4]),
                    "total_loan_received": float(row[5]),
                    "net_balance": float(row[6]),
                    "debt_ratio": float(row[7]),
                    "earliest_loan_time": row[8],
                    "latest_interest_time": row[9]
                })
            
            return {
                "success": True,
                "ranking": ranking
            }
        except Exception as e:
            logger.error(f"获取跨群老赖排行榜失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def create_account(user_id: int, group_id: int, initial_balance: float = 1000.0) -> dict:
        """创建用户交易账户"""
        try:
            now = datetime.datetime.now().isoformat()
            command = """
                INSERT INTO trading_accounts (
                    user_id, group_id, balance, total_pnl, trading_count, winning_trades,
                    losing_trades, total_profit, total_loss, loan_count, total_loan_amount,
                    total_repayment_amount, current_debt, total_fees, frozen_margin,
                    created_at, updated_at
                ) VALUES (?, ?, ?, 0.0, 0, 0, 0, 0.0, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, ?, ?)
            """
            revise_db(command, (user_id, group_id, initial_balance, now, now))

            return {
                "success": True,
                "account": {
                    "user_id": user_id,
                    "group_id": group_id,
                    "balance": initial_balance,
                    "total_pnl": 0.0,
                    "trading_count": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_profit": 0.0,
                    "total_loss": 0.0,
                    "loan_count": 0,
                    "total_loan_amount": 0.0,
                    "total_repayment_amount": 0.0,
                    "current_debt": 0.0,
                    "total_fees": 0.0,
                    "frozen_margin": 0.0,
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
    def update_account_balance(user_id: int, group_id: int, new_balance: float, pnl_change: float = 0.0,
                              fee_change: float = 0.0, is_win: bool = None) -> dict:
        """更新用户账户余额和相关统计数据"""
        try:
            now = datetime.datetime.now().isoformat()

            # 构建动态更新语句
            update_parts = ["balance = ?", "updated_at = ?"]
            params = [new_balance, now]

            if pnl_change != 0:
                update_parts.append("total_pnl = total_pnl + ?")
                params.append(pnl_change)

                # 如果提供了交易胜负信息，更新相应统计
                if pnl_change > 0:
                    update_parts.extend([
                        "trading_count = trading_count + 1",
                        "winning_trades = winning_trades + 1",
                        "total_profit = total_profit + ?"
                    ])
                    params.append(pnl_change)
                elif pnl_change < 0:
                    update_parts.extend([
                        "trading_count = trading_count + 1",
                        "losing_trades = losing_trades + 1",
                        "total_loss = total_loss + ?"
                    ])
                    params.append(abs(pnl_change))

            if fee_change != 0:
                update_parts.append("total_fees = total_fees + ?")
                params.append(fee_change)

            # 如果pnl_change为0且is_win由调用者明确指定，则只更新统计
            if pnl_change == 0 and is_win is not None:
                if is_win:
                    update_parts.extend([
                        "trading_count = trading_count + 1",
                        "winning_trades = winning_trades + 1"
                    ])
                else:
                    update_parts.extend([
                        "trading_count = trading_count + 1",
                        "losing_trades = losing_trades + 1"
                    ])

            command = f"""
                UPDATE trading_accounts
                SET {", ".join(update_parts)}
                WHERE user_id = ? AND group_id = ?
            """
            params.extend([user_id, group_id])

            revise_db(command, params)

            return {"success": True}
        except Exception as e:
            logger.error(f"更新账户余额失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def update_account_margin(user_id: int, group_id: int, margin_change: float) -> dict:
        """更新账户冻结保证金"""
        try:
            now = datetime.datetime.now().isoformat()
            command = """
                UPDATE trading_accounts
                SET frozen_margin = frozen_margin + ?, updated_at = ?
                WHERE user_id = ? AND group_id = ?
            """
            revise_db(command, (margin_change, now, user_id, group_id))

            return {"success": True}
        except Exception as e:
            logger.error(f"更新保证金失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def update_loan_stats(user_id: int, group_id: int, loan_amount: float = 0.0,
                         repayment_amount: float = 0.0, debt_change: float = 0.0) -> dict:
        """更新账户贷款相关统计"""
        try:
            now = datetime.datetime.now().isoformat()

            update_parts = ["updated_at = ?"]
            params = [now]

            if loan_amount > 0:
                update_parts.extend([
                    "loan_count = loan_count + 1",
                    "total_loan_amount = total_loan_amount + ?"
                ])
                params.append(loan_amount)

            if repayment_amount > 0:
                update_parts.append("total_repayment_amount = total_repayment_amount + ?")
                params.append(repayment_amount)

            if debt_change != 0:
                update_parts.append("current_debt = current_debt + ?")
                params.append(debt_change)

            command = f"""
                UPDATE trading_accounts
                SET {", ".join(update_parts)}
                WHERE user_id = ? AND group_id = ?
            """
            params.extend([user_id, group_id])

            revise_db(command, params)

            return {"success": True}
        except Exception as e:
            logger.error(f"更新贷款统计失败: {e}")
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
    def get_trading_history(user_id: int, group_id: int, limit: int = 15) -> dict:
        """获取用户交易历史记录(不包含持仓中的仓位)"""
        try:
            command = """
                SELECT close_trade.action, close_trade.symbol, close_trade.side, 
                       close_trade.size, close_trade.price as exit_price, 
                       close_trade.pnl, close_trade.created_at,
                       open_trade.price as entry_price
                FROM trading_history close_trade
                LEFT JOIN (
                    SELECT symbol, side, price, 
                           ROW_NUMBER() OVER (PARTITION BY symbol, side ORDER BY created_at DESC) as rn
                    FROM trading_history 
                    WHERE user_id = ? AND group_id = ? AND action = 'open'
                ) open_trade ON close_trade.symbol = open_trade.symbol 
                                AND close_trade.side = open_trade.side 
                                AND open_trade.rn = 1
                WHERE close_trade.user_id = ? AND close_trade.group_id = ? 
                      AND close_trade.action IN ('close', 'liquidated')
                ORDER BY close_trade.created_at DESC
                LIMIT ?
            """
            result = query_db(command, (user_id, group_id, user_id, group_id, limit))
            
            history = []
            for row in result:
                history.append({
                    "action": row[0],
                    "symbol": row[1],
                    "side": row[2],
                    "size": float(row[3]),
                    "price": float(row[4]),  # exit_price
                    "pnl": float(row[5]),
                    "created_at": row[6],
                    "entry_price": float(row[7]) if row[7] is not None else float(row[4])  # 如果没有找到开仓记录，使用平仓价格
                })
            
            return {
                "success": True,
                "history": history
            }
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_win_rate(user_id: int, group_id: int) -> dict:
        """计算用户胜率和交易统计(被强平的仓位判定为亏损)"""
        try:
            # 获取所有已平仓和被强平的交易记录，匹配对应的开仓时间
            command = """
                SELECT close_trade.pnl, close_trade.created_at as close_time, 
                       close_trade.size, close_trade.action, close_trade.symbol,
                       (
                           SELECT open_sub.created_at 
                           FROM trading_history open_sub
                           WHERE open_sub.user_id = close_trade.user_id 
                             AND open_sub.group_id = close_trade.group_id
                             AND open_sub.symbol = close_trade.symbol
                             AND open_sub.side = close_trade.side
                             AND open_sub.action = 'open'
                             AND open_sub.created_at < close_trade.created_at
                           ORDER BY open_sub.created_at DESC
                           LIMIT 1
                       ) as open_time
                FROM trading_history close_trade
                WHERE close_trade.user_id = ? AND close_trade.group_id = ? 
                      AND close_trade.action IN ('close', 'liquidated')
                ORDER BY close_trade.created_at
            """
            result = query_db(command, (user_id, group_id))
            
            if not result:
                return {
                    "success": True,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "liquidated_trades": 0,
                    "win_rate": 0.0,
                    "avg_position_size": 0.0,
                    "total_position_size": 0.0,
                    "fee_contribution": 0.0,
                    "avg_holding_time": 0.0,
                    "avg_pnl": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "profit_loss_ratio": 0.0,
                    "most_profitable_symbol": "",
                    "most_profitable_pnl": 0.0,
                    "most_profitable_count": 0,
                    "most_profitable_avg_pnl": 0.0,
                    "most_loss_symbol": "",
                    "most_loss_pnl": 0.0,
                    "most_loss_count": 0,
                    "most_loss_avg_pnl": 0.0,
                    "most_traded_symbol": "",
                    "most_traded_count": 0,
                    "most_traded_avg_pnl": 0.0
                }
            
            total_trades = len(result)
            winning_trades = 0
            losing_trades = 0
            liquidated_trades = 0  # 强平次数
            total_pnl = 0.0
            total_position_size = 0.0
            total_fee_contribution = 0.0  # 手续费贡献
            total_holding_time = 0.0
            winning_pnl = 0.0
            losing_pnl = 0.0
            valid_holding_times = 0
            
            # 按币种统计
            symbol_stats = {}
            
            for row in result:
                pnl = float(row[0])
                close_time = row[1]
                size = float(row[2])
                action = row[3]
                symbol = row[4]
                open_time = row[5]
                
                # 初始化币种统计
                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {
                        'total_pnl': 0.0,
                        'trade_count': 0
                    }
                
                # 更新币种统计
                symbol_stats[symbol]['total_pnl'] += pnl
                symbol_stats[symbol]['trade_count'] += 1
                
                total_pnl += pnl
                total_position_size += size

                # 计算手续费贡献（开仓+平仓手续费）
                fee = size * 0.00035 * 2  # 万分之3.5的开仓和平仓手续费
                total_fee_contribution += fee
                
                # 计算持仓时间（如果有开仓时间）
                if open_time and close_time:
                    try:
                        from datetime import datetime
                        if isinstance(open_time, str):
                            open_dt = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
                        else:
                            open_dt = open_time
                        
                        if isinstance(close_time, str):
                            close_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
                        else:
                            close_dt = close_time
                        
                        holding_time_hours = (close_dt - open_dt).total_seconds() / 3600
                        total_holding_time += holding_time_hours
                        valid_holding_times += 1
                    except:
                        pass
                
                # 统计交易类型和盈亏
                if action == 'liquidated':
                    liquidated_trades += 1
                    losing_trades += 1
                    losing_pnl += abs(pnl)
                elif action == 'close':
                    if pnl > 0:
                        winning_trades += 1
                        winning_pnl += pnl
                    else:
                        losing_trades += 1
                        losing_pnl += abs(pnl)
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
            avg_position_size = total_position_size / total_trades if total_trades > 0 else 0.0
            total_position_size_doubled = total_position_size * 2  # 累计交易量乘以2（开仓+平仓）
            avg_holding_time = total_holding_time / valid_holding_times if valid_holding_times > 0 else 0.0
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
            
            # 盈亏比 = 平均盈利 / 平均亏损
            avg_win = winning_pnl / winning_trades if winning_trades > 0 else 0.0
            avg_loss = -losing_pnl / losing_trades if losing_trades > 0 else 0.0  # 显示为负数
            profit_loss_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else 0.0  # 计算时用绝对值
            
            # 计算币种排名
            most_profitable_symbol = ""
            most_loss_symbol = ""
            most_traded_symbol = ""
            
            if symbol_stats:
                # 赚得最多的币种
                most_profitable_symbol = max(symbol_stats.keys(), key=lambda x: symbol_stats[x]['total_pnl'])
                # 亏得最多的币种
                most_loss_symbol = min(symbol_stats.keys(), key=lambda x: symbol_stats[x]['total_pnl'])
                # 交易次数最多的币种
                most_traded_symbol = max(symbol_stats.keys(), key=lambda x: symbol_stats[x]['trade_count'])
            
            return {
                "success": True,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "liquidated_trades": liquidated_trades,
                "win_rate": round(win_rate, 2),
                "avg_position_size": round(avg_position_size, 2),
                "total_position_size": round(total_position_size_doubled, 2),
                "fee_contribution": round(total_fee_contribution, 2),
                "avg_holding_time": round(avg_holding_time, 2),
                "avg_pnl": round(avg_pnl, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_loss_ratio": round(profit_loss_ratio, 2),
                "most_profitable_symbol": most_profitable_symbol,
                "most_profitable_pnl": round(symbol_stats[most_profitable_symbol]['total_pnl'], 2) if most_profitable_symbol else 0.0,
                "most_profitable_count": symbol_stats[most_profitable_symbol]['trade_count'] if most_profitable_symbol else 0,
                "most_profitable_avg_pnl": round(symbol_stats[most_profitable_symbol]['total_pnl'] / symbol_stats[most_profitable_symbol]['trade_count'], 2) if most_profitable_symbol and symbol_stats[most_profitable_symbol]['trade_count'] > 0 else 0.0,
                "most_loss_symbol": most_loss_symbol,
                "most_loss_pnl": round(symbol_stats[most_loss_symbol]['total_pnl'], 2) if most_loss_symbol else 0.0,
                "most_loss_count": symbol_stats[most_loss_symbol]['trade_count'] if most_loss_symbol else 0,
                "most_loss_avg_pnl": round(symbol_stats[most_loss_symbol]['total_pnl'] / symbol_stats[most_loss_symbol]['trade_count'], 2) if most_loss_symbol and symbol_stats[most_loss_symbol]['trade_count'] > 0 else 0.0,
                "most_traded_symbol": most_traded_symbol,
                "most_traded_count": symbol_stats[most_traded_symbol]['trade_count'] if most_traded_symbol else 0,
                "most_traded_avg_pnl": round(symbol_stats[most_traded_symbol]['total_pnl'] / symbol_stats[most_traded_symbol]['trade_count'], 2) if most_traded_symbol and symbol_stats[most_traded_symbol]['trade_count'] > 0 else 0.0
            }
        except Exception as e:
            logger.error(f"计算胜率失败: {e}")
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

    @staticmethod
    def get_full_trading_history(user_id: int, group_id: int) -> dict:
        """获取用户完整的交易历史记录(用于绘图，不限制数量)"""
        try:
            command = """
                SELECT close_trade.action, close_trade.symbol, close_trade.side,
                       close_trade.size, close_trade.price as exit_price,
                       close_trade.pnl, close_trade.created_at,
                       open_trade.price as entry_price
                FROM trading_history close_trade
                LEFT JOIN (
                    SELECT symbol, side, price,
                           ROW_NUMBER() OVER (PARTITION BY symbol, side ORDER BY created_at DESC) as rn
                    FROM trading_history
                    WHERE user_id = ? AND group_id = ? AND action = 'open'
                ) open_trade ON close_trade.symbol = open_trade.symbol
                                AND close_trade.side = open_trade.side
                                AND open_trade.rn = 1
                WHERE close_trade.user_id = ? AND close_trade.group_id = ?
                      AND close_trade.action IN ('close', 'liquidated')
                ORDER BY close_trade.created_at ASC
            """
            result = query_db(command, (user_id, group_id, user_id, group_id))

            history = []
            for row in result:
                history.append({
                    "action": row[0],
                    "symbol": row[1],
                    "side": row[2],
                    "size": float(row[3]),
                    "price": float(row[4]),  # exit_price
                    "pnl": float(row[5]),
                    "created_at": row[6],
                    "entry_price": float(row[7]) if row[7] is not None else float(row[4])  # 如果没有找到开仓记录，使用平仓价格
                })

            return {
                "success": True,
                "history": history
            }
        except Exception as e:
            logger.error(f"获取完整交易历史失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def create_order(order_id: str, user_id: int, group_id: int, symbol: str, direction: str,
                     role: str, order_type: str, operation: str, volume: float,
                     price: float = None, tp_price: float = None, sl_price: float = None,
                     margin_locked: float = 0.0, fee_rate: float = 0.0035) -> dict:
        """创建新的交易订单"""
        try:
            now = datetime.datetime.now().isoformat()

            command = """
                INSERT INTO trading_orders (
                    order_id, user_id, group_id, symbol, direction, role,
                    order_type, operation, volume, price, tp_price, sl_price,
                    margin_locked, fee_rate, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            revise_db(command, (order_id, user_id, group_id, symbol, direction, role,
                              order_type, operation, volume, price, tp_price, sl_price,
                              margin_locked, fee_rate, now))

            return {
                "success": True,
                "order_id": order_id
            }
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }