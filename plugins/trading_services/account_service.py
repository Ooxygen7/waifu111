"""
账户服务
负责交易账户的管理和统计数据维护
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class AccountService:
    """
    账户管理服务
    处理账户创建、余额管理、统计数据维护等功能
    """

    def __init__(self):
        logger.info("账户服务已初始化")

    def get_or_create_account(self, user_id: int, group_id: int) -> Dict:
        """
        获取或创建用户交易账户

        Args:
            user_id: 用户ID
            group_id: 群组ID

        Returns:
            账户信息字典
        """
        try:
            # 尝试获取现有账户
            result = TradingRepository.get_account(user_id, group_id)
            if not result["success"]:
                logger.error(f"获取账户失败: {result['error']}")
                return {
                    'balance': 0.0,
                    'total_pnl': 0.0,
                    'trading_count': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0.0,
                    'total_loss': 0.0,
                    'loan_count': 0,
                    'total_loan_amount': 0.0,
                    'total_repayment_amount': 0.0,
                    'current_debt': 0.0,
                    'total_fees': 0.0,
                    'frozen_margin': 0.0
                }

            if result["account"]:
                account = result["account"]
                return {
                    'balance': account['balance'],
                    'total_pnl': account['total_pnl'],
                    'trading_count': account['trading_count'],
                    'winning_trades': account['winning_trades'],
                    'losing_trades': account['losing_trades'],
                    'total_profit': account['total_profit'],
                    'total_loss': account['total_loss'],
                    'loan_count': account['loan_count'],
                    'total_loan_amount': account['total_loan_amount'],
                    'total_repayment_amount': account['total_repayment_amount'],
                    'current_debt': account['current_debt'],
                    'total_fees': account['total_fees'],
                    'frozen_margin': account['frozen_margin']
                }

            # 创建新账户
            logger.info(f"创建新账户 - 用户{user_id} 群组{group_id}")
            create_result = TradingRepository.create_account(user_id, group_id)
            if not create_result["success"]:
                logger.error(f"创建账户失败: {create_result['error']}")
                return {
                    'balance': 0.0,
                    'total_pnl': 0.0,
                    'trading_count': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0.0,
                    'total_loss': 0.0,
                    'loan_count': 0,
                    'total_loan_amount': 0.0,
                    'total_repayment_amount': 0.0,
                    'current_debt': 0.0,
                    'total_fees': 0.0,
                    'frozen_margin': 0.0
                }

            return {
                'balance': 1000.0,  # 新账户初始余额
                'total_pnl': 0.0,
                'trading_count': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'loan_count': 0,
                'total_loan_amount': 0.0,
                'total_repayment_amount': 0.0,
                'current_debt': 0.0,
                'total_fees': 0.0,
                'frozen_margin': 0.0
            }

        except Exception as e:
            logger.error(f"获取/创建账户失败: {e}")
            return {
                'balance': 0.0,
                'total_pnl': 0.0,
                'trading_count': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'loan_count': 0,
                'total_loan_amount': 0.0,
                'total_repayment_amount': 0.0,
                'current_debt': 0.0,
                'total_fees': 0.0,
                'frozen_margin': 0.0
            }

    def update_balance(self, user_id: int, group_id: int, new_balance: float,
                      pnl_change: float = 0.0, fee_change: float = 0.0,
                      is_win: Optional[bool] = None) -> Dict:
        """
        更新账户余额和相关统计

        Args:
            user_id: 用户ID
            group_id: 群组ID
            new_balance: 新的余额
            pnl_change: 盈亏变化
            fee_change: 手续费变化
            is_win: 是否盈利交易 (用于统计胜率)

        Returns:
            操作结果
        """
        try:
            result = TradingRepository.update_account_balance(
                user_id, group_id, new_balance, pnl_change, fee_change, is_win
            )

            if result["success"]:
                logger.debug(f"账户余额更新成功 - 用户{user_id} 群组{group_id}: 余额={new_balance}, 盈亏={pnl_change}, 手续费={fee_change}")
            else:
                logger.error(f"账户余额更新失败 - 用户{user_id} 群组{group_id}: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"更新账户余额异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def update_margin(self, user_id: int, group_id: int, margin_change: float) -> Dict:
        """
        更新账户冻结保证金

        Args:
            user_id: 用户ID
            group_id: 群组ID
            margin_change: 保证金变化 (正数为增加，负数为减少)

        Returns:
            操作结果
        """
        try:
            result = TradingRepository.update_account_margin(user_id, group_id, margin_change)

            if result["success"]:
                direction = "增加" if margin_change > 0 else "减少"
                logger.debug(f"保证金更新成功 - 用户{user_id} 群组{group_id}: {direction} {abs(margin_change)} USDT")
            else:
                logger.error(f"保证金更新失败 - 用户{user_id} 群组{group_id}: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"更新保证金异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def update_loan_stats(self, user_id: int, group_id: int,
                         loan_amount: float = 0.0, repayment_amount: float = 0.0,
                         debt_change: float = 0.0) -> Dict:
        """
        更新账户贷款相关统计

        Args:
            user_id: 用户ID
            group_id: 群组ID
            loan_amount: 新借款金额
            repayment_amount: 还款金额
            debt_change: 债务变化

        Returns:
            操作结果
        """
        try:
            result = TradingRepository.update_loan_stats(
                user_id, group_id, loan_amount, repayment_amount, debt_change
            )

            if result["success"]:
                logger.info(f"贷款统计更新 - 用户{user_id} 群组{group_id}: 借款={loan_amount}, 还款={repayment_amount}")
            else:
                logger.error(f"贷款统计更新失败 - 用户{user_id} 群组{group_id}: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"更新贷款统计异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_account_summary(self, user_id: int, group_id: int) -> Dict:
        """获取账户完整摘要信息"""
        try:
            account = self.get_or_create_account(user_id, group_id)

            # 计算胜率
            win_rate = 0.0
            if account["trading_count"] > 0:
                win_rate = (account["winning_trades"] / account["trading_count"]) * 100

            # 计算净资产 (未实现部分需要从仓位服务获取)
            net_asset = account["balance"] - account["frozen_margin"]

            return {
                "success": True,
                "account": account,
                "win_rate": round(win_rate, 2),
                "net_asset": net_asset,
                "profit_factor": round(account["total_profit"] / max(account["total_loss"], 0.01), 2),
                "summary": f"余额: {account['balance']:.2f} USDT, 总盈亏: {account['total_pnl']:+.2f} USDT, 胜率: {win_rate:.1f}%, 净利润: {account['total_profit'] - account['total_loss']:.2f} USDT"
            }

        except Exception as e:
            logger.error(f"获取账户摘要异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 全局账户服务实例
account_service = AccountService()