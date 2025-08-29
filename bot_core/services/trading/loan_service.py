"""
贷款服务
负责贷款申请、还款、利息计算等贷款相关业务
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from .account_service import account_service
from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class LoanService:
    """
    贷款管理服务
    处理贷款的完整生命周期：申请、利息计算、还款
    """

    def __init__(self):
        # 复利计算参数
        self.interest_rate_per_period = 0.002  # 每6小时利率0.2%
        self.period_hours = 6  # 计算周期：6小时
        self.initial_fee_rate = 0.1  # 初始手续费率10%

        logger.info("贷款服务已初始化")

    def apply_loan(self, user_id: int, group_id: int, principal: float) -> Dict:
        """
        申请贷款

        Args:
            user_id: 用户ID
            group_id: 群组ID
            principal: 贷款本金

        Returns:
            贷款申请结果
        """
        try:
            # 获取用户账户信息
            account = account_service.get_or_create_account(user_id, group_id)

            # 计算当前活跃贷款总额和总欠款
            loans_result = TradingRepository.get_active_loans(user_id, group_id)
            if not loans_result["success"]:
                return {"success": False, "message": "获取贷款信息失败"}

            current_total_debt = 0.0
            total_loan_principal = 0.0

            # 更新并计算所有活跃贷款的利息
            for loan in loans_result["loans"]:
                try:
                    updated_debt = self._calculate_compound_interest(
                        loan["remaining_debt"],
                        loan["last_interest_time"],
                        self.interest_rate_per_period
                    )

                    # 更新数据库中的欠款
                    TradingRepository.update_loan_debt(loan["id"], updated_debt)
                    current_total_debt += updated_debt
                    total_loan_principal += loan["principal"]

                except Exception as e:
                    logger.error(f"计算贷款利息失败 #{loan['id']}: {e}")
                    current_total_debt += loan["remaining_debt"]
                    total_loan_principal += loan["principal"]

            # 计算净余额（扣除已借贷本金）
            net_balance = account["balance"] - total_loan_principal

            # 计算最大可借额度（净余额的20倍）
            max_allowed_debt = net_balance * 20
            new_total_debt = current_total_debt + principal * (1 + self.initial_fee_rate)

            # 检查贷款额度
            if new_total_debt > max_allowed_debt:
                max_loan_amount = (max_allowed_debt - current_total_debt) / (1 + self.initial_fee_rate)

                return {
                    "success": False,
                    "message": f"贷款额度不足！\n💰 当前余额: {account['balance']:.2f} USDT\n" +
                             f"💸 净余额: {net_balance:.2f} USDT (扣除贷款本金: {total_loan_principal:.2f} USDT)\n" +
                             f"💳 当前欠款: {current_total_debt:.2f} USDT\n" +
                             f"📊 最大可贷: {max_loan_amount:.2f} USDT\n" +
                             f"🏦 申请金额: {principal:.2f} USDT (含手续费: {principal * (1 + self.initial_fee_rate):.2f} USDT)\n" +
                             f"\n💡 最大可贷金额已考虑10%手续费"
                }

            # 创建贷款记录
            loan_result = TradingRepository.create_loan(user_id, group_id, principal)
            if not loan_result["success"]:
                return {"success": False, "message": "创建贷款记录失败"}

            # 发放贷款到用户账户
            new_balance = account["balance"] + principal
            balance_result = TradingRepository.update_account_balance(
                user_id, group_id, new_balance, 0.0, 0.0
            )

            if not balance_result["success"]:
                return {"success": False, "message": "更新账户余额失败"}

            # 更新账户贷款统计
            debt_change = principal * (1 + self.initial_fee_rate)
            stats_result = account_service.update_loan_stats(
                user_id, group_id, principal, 0.0, debt_change
            )

            logger.info(f"贷款申请成功 - 用户{user_id} 群组{group_id}: 本金{principal}, 初始欠款{principal * (1 + self.initial_fee_rate)}")

            return {
                "success": True,
                "message": f"🏦 贷款成功！\n\n💰 贷款金额: {principal:.2f} USDT\n" +
                         f"💸 手续费(10%): {principal * self.initial_fee_rate:.2f} USDT\n" +
                         f"📊 实际欠款: {principal * (1 + self.initial_fee_rate):.2f} USDT\n" +
                         f"💳 当前余额: {new_balance:.2f} USDT\n\n⚠️ 每6小时产生0.2%复利，请及时还款！",
                "loan_id": loan_result["loan_id"],
                "principal": principal,
                "initial_debt": principal * (1 + self.initial_fee_rate),
                "new_balance": new_balance
            }

        except Exception as e:
            logger.error(f"申请贷款失败: {e}")
            return {
                "success": False,
                "message": f"申请贷款失败: {str(e)}"
            }

    def repay_loan(self, user_id: int, group_id: int, amount: Optional[float] = None) -> Dict:
        """
        还款操作

        Args:
            user_id: 用户ID
            group_id: 群组ID
            amount: 还款金额，None表示全额还款

        Returns:
            还款结果
        """
        try:
            # 获取用户账户信息
            account_result = TradingRepository.get_account(user_id, group_id)
            if not account_result["success"] or not account_result.get("account"):
                return {"success": False, "message": "账户不存在"}

            current_balance = account_result["account"]["balance"]

            # 获取活跃贷款
            loans_result = TradingRepository.get_active_loans(user_id, group_id)
            if not loans_result["success"]:
                return {"success": False, "message": "获取贷款信息失败"}

            if not loans_result["loans"]:
                return {"success": False, "message": "没有待还贷款"}

            # 更新所有贷款的利息并计算总欠款
            total_debt = 0.0
            updated_loans = []

            for loan in loans_result["loans"]:
                updated_debt = self._calculate_compound_interest(
                    loan["remaining_debt"],
                    loan["last_interest_time"],
                    loan["interest_rate"]
                )

                # 更新数据库
                TradingRepository.update_loan_debt(loan["id"], updated_debt)
                loan["remaining_debt"] = updated_debt
                updated_loans.append(loan)
                total_debt += updated_debt

            # 确定还款金额
            repayment_amount = total_debt if amount is None else amount

            # 检查还款金额是否合理
            if amount is not None and amount > total_debt:
                return {
                    "success": False,
                    "message": f"还款金额超过实际欠款！\n💸 实际欠款: {total_debt:.2f} USDT\n💰 指定还款: {amount:.2f} USDT\n\n💡 请输入不超过实际欠款的金额，或使用 /repay 进行全额还款"
                }

            # 检查余额是否足够（保留1000 USDT基础余额）
            available_balance = max(0, current_balance - 1000)
            if repayment_amount > available_balance:
                return {
                    "success": False,
                    "message": f"余额不足！\n当前余额: {current_balance:.2f} USDT\n可用于还款: {available_balance:.2f} USDT\n需要还款: {repayment_amount:.2f} USDT\n\n💡 系统会保留1000 USDT作为救济金基础"
                }

            # 按贷款时间顺序还款（先还旧贷款）
            remaining_amount = repayment_amount
            repaid_loans = []

            for loan in sorted(updated_loans, key=lambda x: x["created_at"]):
                if remaining_amount <= 0:
                    break

                loan_debt = loan["remaining_debt"]
                actual_repayment = min(remaining_amount, loan_debt)

                # 记录还款
                repay_result = TradingRepository.repay_loan(
                    loan["id"], user_id, group_id, actual_repayment
                )

                if repay_result["success"]:
                    remaining_after = repay_result["remaining_after"]
                    repaid_loans.append({
                        "loan_id": loan["id"],
                        "original_debt": loan_debt,
                        "paid_amount": actual_repayment,
                        "remaining_after": remaining_after,
                        "fully_paid": remaining_after <= 0.01  # 精度误差处理
                    })
                    remaining_amount -= actual_repayment
                else:
                    return {"success": False, "message": f"还款失败: 贷款#{loan['id']}"}

            # 更新用户余额
            new_balance = current_balance - repayment_amount
            balance_result = TradingRepository.update_account_balance(
                user_id, group_id, new_balance, 0.0, 0.0
            )

            if not balance_result["success"]:
                return {"success": False, "message": "更新余额失败"}

            # 更新账户贷款统计
            stats_result = account_service.update_loan_stats(
                user_id, group_id, 0.0, repayment_amount, -repayment_amount
            )

            # 构建还款报告
            message_parts = [f"💳 还款成功！\n\n💰 还款金额: {repayment_amount:.2f} USDT\n💳 剩余余额: {new_balance:.2f} USDT\n\n"]

            # 逐笔贷款还款详情
            for repaid in repaid_loans:
                status = "✅ 已结清" if repaid["fully_paid"] else f"剩余: {repaid['remaining_after']:.2f} USDT"
                message_parts.append(f"📋 贷款#{repaid['loan_id']}: {repaid['paid_amount']:.2f} USDT ({status})\n")

            # 检查是否还有剩余欠款
            remaining_loans = TradingRepository.get_active_loans(user_id, group_id)
            if remaining_loans["success"] and remaining_loans["loans"]:
                remaining_total = sum(self._calculate_compound_interest(
                    loan["remaining_debt"], loan["last_interest_time"], loan["interest_rate"]
                ) for loan in remaining_loans["loans"])
                message_parts.append(f"\n⚠️ 剩余总欠款: {remaining_total:.2f} USDT")
            else:
                message_parts.append("\n🎉 所有贷款已结清！")

            logger.info(f"还款成功 - 用户{user_id} 群组{group_id}: 还款{repayment_amount}, 新余额{new_balance}")

            return {
                "success": True,
                "message": "".join(message_parts),
                "repaid_amount": repayment_amount,
                "new_balance": new_balance,
                "repaid_loans": repaid_loans
            }

        except Exception as e:
            logger.error(f"还款失败: {e}")
            return {
                "success": False,
                "message": f"还款失败: {str(e)}"
            }

    def begging(self, user_id: int, group_id: int) -> Dict:
        """
        救济金功能
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            
        Returns:
            救济金发放结果
        """
        try:
            account = account_service.get_or_create_account(user_id, group_id)
            
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

    def get_loan_bill(self, user_id: int, group_id: int) -> Dict:
        """
        获取用户贷款账单

        Args:
            user_id: 用户ID
            group_id: 群组ID

        Returns:
            贷款账单信息
        """
        try:
            # 获取贷款汇总
            summary_result = TradingRepository.get_loan_summary(user_id, group_id)
            if not summary_result["success"]:
                return {"success": False, "message": "获取贷款信息失败"}

            summary = summary_result["summary"]

            # 获取活跃贷款详情并更新利息
            loans_result = TradingRepository.get_active_loans(user_id, group_id)
            if not loans_result["success"]:
                return {"success": False, "message": "获取贷款详情失败"}

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
                try:
                    from datetime import datetime
                    loan_time = datetime.fromisoformat(loan["loan_time"].replace('Z', '+00:00'))
                    days_since_loan = (datetime.now() - loan_time).days
                except:
                    days_since_loan = 0

                loan_details.append({
                    "loan_id": loan["id"],
                    "principal": loan["principal"],
                    "current_debt": updated_debt,
                    "interest_generated": updated_debt - loan["principal"] * (1 + self.initial_fee_rate),
                    "days_since_loan": days_since_loan,
                    "loan_time": loan["loan_time"]
                })

            if not loan_details:
                message = (
                    "🎉 恭喜！您当前没有任何贷款\n\n📊 历史统计:\n" +
                    f"📈 总贷款次数: {summary['total_loans']}\n" +
                    f"💰 累计借款: {summary['total_borrowed']:.2f} USDT\n" +
                    f"💳 累计还款: {summary['total_repaid']:.2f} USDT"
                )
            else:
                message_parts = [
                    "🏦 贷款账单\n\n",
                    f"📊 当前状态:\n",
                    f"💰 活跃贷款: {summary['active_loan_count']} 笔\n",
                    f"💸 总欠款: {current_total_debt:.2f} USDT\n\n",
                    "📋 贷款详情:\n"
                ]

                for i, loan in enumerate(loan_details, 1):
                    message_parts.append(
                        f"{i}. 贷款#{loan['loan_id']}\n" +
                        f"   💰 本金: {loan['principal']:.2f} USDT\n" +
                        f"   💸 当前欠款: {loan['current_debt']:.2f} USDT\n" +
                        f"   📈 产生利息: {loan['interest_generated']:.2f} USDT\n" +
                        f"   📅 贷款天数: {loan['days_since_loan']} 天\n\n"
                    )

                message_parts.extend([
                    "📊 历史统计:\n",
                    f"📈 总贷款次数: {summary['total_loans']}\n",
                    f"💰 累计借款: {summary['total_borrowed']:.2f} USDT\n",
                    f"💳 累计还款: {summary['total_repaid']:.2f} USDT\n\n",
                    "⚠️ 利息每6小时复利0.2%，请及时还款！"
                ])

                message = "".join(message_parts)

            return {
                "success": True,
                "message": message,
                "total_debt": current_total_debt if loan_details else 0.0,
                "active_loans": len(loan_details),
                "summary": summary
            }

        except Exception as e:
            logger.error(f"获取贷款账单失败: {e}")
            return {
                "success": False,
                "message": f"获取贷款账单失败: {str(e)}"
            }

    def _calculate_compound_interest(self, principal: float, last_interest_time: str,
                                   rate: float = None) -> float:
        """
        计算复利利息

        Args:
            principal: 本金
            last_interest_time: 最后计息时间
            rate: 利率，默认使用服务配置

        Returns:
            计算后的本金+利息
        """
        try:
            if rate is None:
                rate = self.interest_rate_per_period

            last_time = datetime.fromisoformat(last_interest_time.replace('Z', '+00:00'))
            current_time = datetime.now()

            # 计算经过的6小时周期数
            time_diff = current_time - last_time
            periods = time_diff.total_seconds() / (self.period_hours * 3600)

            if periods < 1:
                return principal  # 不足一个周期，不计息

            # 复利计算: A = P(1 + r)^n
            compound_amount = principal * ((1 + rate) ** int(periods))

            # 记录利息变化（大于0.0001时）
            interest_change = compound_amount - principal
            if abs(interest_change) > 0.0001:
                logger.debug(".10f")

            return compound_amount

        except Exception as e:
            logger.error(f"计算复利失败: {e}")
            return principal  # 返回原始金额避免错误

    def update_loan_interests(self, user_id: int, group_id: int) -> Dict:
        """
        更新用户所有贷款的利息

        Args:
            user_id: 用户ID
            group_id: 群组ID

        Returns:
            更新结果
        """
        try:
            updated_count = 0
            total_interest = 0.0

            # 获取活跃贷款
            loans_result = TradingRepository.get_active_loans(user_id, group_id)
            if not loans_result["success"]:
                return {"success": False, "message": "获取贷款信息失败"}

            for loan in loans_result["loans"]:
                original_debt = loan["remaining_debt"]
                updated_debt = self._calculate_compound_interest(
                    original_debt, loan["last_interest_time"], loan["interest_rate"]
                )

                if updated_debt != original_debt:
                    # 更新数据库
                    TradingRepository.update_loan_debt(loan["id"], updated_debt)
                    total_interest += (updated_debt - original_debt)
                    updated_count += 1

            if updated_count > 0:
                logger.info(f"更新贷款利息成功 - 用户{user_id}: {updated_count}笔贷款，累计利息{total_interest:.4f}")

            return {
                "success": True,
                "updated_count": updated_count,
                "total_interest_accrued": total_interest
            }

        except Exception as e:
            logger.error(f"批量更新贷款利息失败: {e}")
            return {
                "success": False,
                "message": f"更新失败: {str(e)}"
            }


# 全局贷款服务实例
loan_service = LoanService()