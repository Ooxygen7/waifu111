"""
统计服务
负责交易数据分析、报告生成和统计信息展示
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .price_service import price_service
from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class AnalysisService:
    """
    统计分析服务
    提供交易数据的分析报告、排行榜和统计信息
    """

    def __init__(self):
        logger.info("统计服务已初始化")

    async def get_pnl_report(self, user_id: int, group_id: int) -> Dict:
        """获取用户盈亏报告"""
        try:
            # 获取账户信息
            account_result = TradingRepository.get_account(user_id, group_id)
            if not account_result["success"] or not account_result["account"]:
                return {"success": False, "message": "未找到账户信息"}

            account = account_result["account"]
            total_pnl = account["total_pnl"]

            # 获取交易历史
            history_result = TradingRepository.get_trading_history(user_id, group_id, 15)
            if not history_result["success"]:
                return {"success": False, "message": "获取交易历史失败"}

            history = history_result["history"]

            if not history:
                pnl_status = "📈 累计盈利" if total_pnl >= 0 else "📉 累计亏损"
                pnl_color = "🟢" if total_pnl >= 0 else "🔴"
                return {
                    "success": True,
                    "message": f"📊 盈亏报告\n\n{pnl_color} {pnl_status}: {total_pnl:+.2f} USDT\n\n❌ 暂无交易记录"
                }

            # 计算胜率和统计数据
            analysis_data = self._analyze_trading_history(history)

            # 构建交易记录
            trade_records = []
            for trade in history:
                side_emoji = '📈' if trade['side'] == 'long' else '📉'
                pnl_emoji = '✅' if trade['pnl'] > 0 else '❌'
                coin = trade['symbol'].replace('/USDT', '')

                try:
                    from datetime import datetime
                    if isinstance(trade['created_at'], str):
                        dt = datetime.fromisoformat(trade['created_at'].replace('Z', '+00:00'))
                    else:
                        dt = trade['created_at']
                    time_str = dt.strftime('%m-%d %H:%M')
                except:
                    time_str = str(trade['created_at'])[:16]

                entry_price = trade.get('entry_price', trade['price'])
                trade_records.append(
                    f"{side_emoji}{pnl_emoji} | {coin} | Entry:{entry_price:.4f} | Exit:{trade['price']:.4f} | ${trade['size']:.0f} | PnL:{trade['pnl']:+.0f} | {time_str}"
                )

            recent_trades = "\n".join(trade_records)

            # 获取Win率数据
            win_rate_result = TradingRepository.get_win_rate(user_id, group_id)
            if win_rate_result["success"]:
                win_data = win_rate_result

                win_rate_info = (
                    f"📈 总交易次数: {win_data['total_trades']}\n"
                    f"🎯 盈利次数: {win_data['winning_trades']}\n"
                    f"📉 亏损次数: {win_data['losing_trades']}\n"
                    f"⚡ 强平次数: {win_data['liquidated_trades']}\n"
                    f"📊 胜率: {win_data['win_rate']:.1f}%\n"
                    f"💰 手续费贡献: ${win_data['fee_contribution']:.2f}\n"
                    f"⏱️ 平均持仓: {win_data['avg_holding_time']:.1f}小时\n"
                    f"📈 平均盈利: {win_data['avg_win']:+.2f} USDT\n"
                    f"📉 平均亏损: {win_data['avg_loss']:+.2f} USDT\n"
                    f"⚖️ 盈亏比: {win_data['profit_loss_ratio']:.2f}"
                )

                # 币种统计信息
                symbol_stats = ""
                if win_data.get('most_profitable_symbol'):
                    most_profitable_coin = win_data['most_profitable_symbol'].replace('/USDT', '')
                    symbol_stats += f"🏆 最赚钱币种: {most_profitable_coin} (+{win_data['most_profitable_pnl']:.0f} USDT)\n"

                if win_data.get('most_traded_symbol'):
                    most_traded_coin = win_data['most_traded_symbol'].replace('/USDT', '')
                    symbol_stats += f"🔥 最常交易币种: {most_traded_coin} ({win_data['most_traded_count']}次)"

                # 组合消息
                pnl_status = "📈 累计盈利" if total_pnl >= 0 else "📉 累计亏损"
                pnl_color = "🟢" if total_pnl >= 0 else "🔴"

                message_parts = [
                    "📊 盈亏报告\n",
                    f"<blockquote expandable>💰 累计盈亏\n{pnl_color} {pnl_status}: {total_pnl:+.2f} USDT</blockquote>\n",
                    f"<blockquote expandable>📋 最近15笔交易\n\n{recent_trades}</blockquote>\n",
                    f"<blockquote expandable>📈 胜率统计\n\n{win_rate_info}</blockquote>"
                ]

                if symbol_stats.strip():
                    message_parts.append(f"\n<blockquote expandable>🎯 币种统计\n\n{symbol_stats}</blockquote>")

                return {
                    "success": True,
                    "message": "".join(message_parts),
                    "total_pnl": total_pnl,
                    "win_rate": win_data.get('win_rate', 0.0)
                }

            else:
                return {
                    "success": False,
                    "message": "计算胜率失败"
                }

        except Exception as e:
            logger.error(f"获取盈亏报告失败: {e}")
            return {
                "success": False,
                "message": f"获取盈亏报告失败: {str(e)}"
            }

    async def get_ranking_data(self, group_id: int) -> Dict:
        """获取群组排行榜数据"""
        try:
            # 获取盈利排行榜
            profit_result = TradingRepository.get_group_profit_ranking(group_id, 10)
            profit_ranking = profit_result.get("ranking", []) if profit_result.get("success") else []

            # 获取亏损排行榜
            loss_result = TradingRepository.get_group_loss_ranking(group_id, 10)
            loss_ranking = loss_result.get("ranking", []) if loss_result.get("success") else []

            # 获取账户余额排行榜
            balance_accounts = await self._get_balance_ranking_with_floating(group_id, 10)

            # 获取交易量排行榜
            volume_result = TradingRepository.get_group_trading_volume_ranking(group_id, 10)
            volume_ranking = volume_result.get("ranking", []) if volume_result.get("success") else []

            # 获取强平排行榜（累计次数最多）
            liquidation_result = TradingRepository.get_group_liquidation_ranking(group_id, 10)
            liquidation_ranking = liquidation_result.get("ranking", []) if liquidation_result.get("success") else []

            return {
                "success": True,
                "profit_ranking": profit_ranking,
                "loss_ranking": loss_ranking,
                "balance_ranking": balance_accounts,
                "liquidation_ranking": liquidation_ranking,
                "volume_ranking": volume_ranking
            }

        except Exception as e:
            logger.error(f"获取排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_balance_ranking_with_floating(self, group_id: int, limit: int) -> List[Dict]:
        """获取包含浮动余额的账户排名"""
        try:
            # 获取账户余额信息
            balance_result = TradingRepository.get_group_balance_accounts(group_id)
            if not balance_result["success"]:
                return []

            accounts = balance_result["accounts"]

            # 计算每个用户的浮动余额
            balance_ranking = []
            for account in accounts:
                user_id = account["user_id"]
                balance = account["balance"]

                # 获取用户所有仓位计算未实现盈亏
                positions_result = TradingRepository.get_positions(user_id, group_id)
                total_unrealized_pnl = 0.0

                if positions_result["success"] and positions_result["positions"]:
                    for pos in positions_result["positions"]:
                        current_price = await price_service.get_current_price(pos['symbol'])
                        if current_price:
                            pnl = self._calculate_pnl(pos['entry_price'], current_price, pos['size'], pos['side'])
                            total_unrealized_pnl += pnl

                floating_balance = balance + total_unrealized_pnl
                balance_ranking.append({
                    "user_id": user_id,
                    "balance": balance,
                    "floating_balance": floating_balance,
                    "unrealized_pnl": total_unrealized_pnl
                })

            # 按浮动余额排序
            balance_ranking.sort(key=lambda x: x["floating_balance"], reverse=True)
            return balance_ranking[:limit]

        except Exception as e:
            logger.error(f"计算浮动余额排名失败: {e}")
            return []

    async def get_global_ranking_data(self) -> Dict:
        """获取跨群排行榜数据"""
        try:
            # 获取跨群盈利排行榜
            profit_result = TradingRepository.get_global_profit_ranking(10)
            profit_ranking = profit_result.get("ranking", []) if profit_result.get("success") else []

            # 获取跨群亏损排行榜
            loss_result = TradingRepository.get_global_loss_ranking(10)
            loss_ranking = loss_result.get("ranking", []) if loss_result.get("success") else []

            # 获取跨群余额排行榜
            balance_accounts = await self._get_global_balance_ranking_with_floating(10)

            # 获取跨群交易量排行榜
            volume_result = TradingRepository.get_global_trading_volume_ranking(10)
            volume_ranking = volume_result.get("ranking", []) if volume_result.get("success") else []

            # 获取跨群强平排行榜
            global_liquidation_result = TradingRepository.get_global_liquidation_ranking()
            liquidation_ranking = global_liquidation_result.get("ranking", []) if global_liquidation_result.get("success") else []
            liquidation_ranking = liquidation_ranking[:10]

            return {
                "success": True,
                "profit_ranking": profit_ranking,
                "loss_ranking": loss_ranking,
                "balance_ranking": balance_accounts,
                "liquidation_ranking": liquidation_ranking,
                "volume_ranking": volume_ranking
            }

        except Exception as e:
            logger.error(f"获取跨群排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_global_balance_ranking_with_floating(self, limit: int) -> List[Dict]:
        """获取跨群包含浮动余额的账户排名"""
        try:
            # 获取跨群账户余额信息
            balance_result = TradingRepository.get_global_balance_accounts()
            if not balance_result["success"]:
                return []

            accounts = balance_result["accounts"]

            # 按用户分组计算最优表现
            user_best_balance = {}
            for account in accounts:
                user_id = account["user_id"]
                group_id = account["group_id"]
                balance = account["balance"]

                # 获取用户在该群的所有仓位计算未实现盈亏
                positions_result = TradingRepository.get_positions(user_id, group_id)
                total_unrealized_pnl = 0.0

                if positions_result["success"] and positions_result["positions"]:
                    for pos in positions_result["positions"]:
                        current_price = await price_service.get_current_price(pos['symbol'])
                        if current_price:
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
                        "group_name": account["group_name"]
                    }

            # 转换为列表并排序
            balance_ranking = list(user_best_balance.values())
            balance_ranking.sort(key=lambda x: x["floating_balance"], reverse=True)
            return balance_ranking[:limit]

        except Exception as e:
            logger.error(f"计算跨群浮动余额排名失败: {e}")
            return []

    async def get_deadbeat_ranking_data(self, group_id: int) -> Dict:
        """获取集团赖排行榜数据"""
        try:
            # 获取集团赖排行榜数据
            result = TradingRepository.get_group_deadbeat_ranking(group_id, 10)

            if result['success']:
                # 为每个赖计算逾期天数
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
            else:
                return {
                    "success": False,
                    "error": result.get('error', '获取集团赖排行榜失败')
                }

        except Exception as e:
            logger.error(f"获取集团赖排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_global_deadbeat_ranking_data(self) -> Dict:
        """获取跨群集团赖排行榜数据"""
        try:
            # 获取跨群集团赖排行榜数据
            result = TradingRepository.get_global_deadbeat_ranking(10)

            if result['success']:
                # 为每个赖计算逾期天数
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
            else:
                return {
                    "success": False,
                    "error": result.get('error', '获取跨群集团赖排行榜失败')
                }

        except Exception as e:
            logger.error(f"获取跨群集团赖排行榜数据失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _calculate_pnl(self, entry_price: float, current_price: float, size: float, side: str) -> float:
        """计算盈亏"""
        if side == 'long':
            return (current_price - entry_price) * (size / entry_price)
        else:
            return (entry_price - current_price) * (size / entry_price)

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

    def generate_pnl_chart(self, user_id: int, group_id: int) -> Optional[bytes]:
        """
        生成盈亏折线图，包含统计信息
        
        Args:
            user_id: 用户ID
            group_id: 群组ID
            
        Returns:
            图表的字节数据，失败时返回None
        """
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
            from .account_service import account_service
            account = account_service.get_or_create_account(user_id, group_id)

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

    def _analyze_trading_history(self, history: List[Dict]) -> Dict:
        """分析交易历史数据"""
        if not history:
            return {}

        try:
            total_trades = len(history)
            winning_trades = sum(1 for trade in history if trade['pnl'] > 0)
            losing_trades = sum(1 for trade in history if trade['pnl'] <= 0)

            winning_pnl = sum(trade['pnl'] for trade in history if trade['pnl'] > 0)
            losing_pnl = sum(abs(trade['pnl']) for trade in history if trade['pnl'] <= 0)

            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            avg_win = winning_pnl / winning_trades if winning_trades > 0 else 0
            avg_loss = losing_pnl / losing_trades if losing_trades > 0 else 0
            profit_loss_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else 0

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_loss_ratio": profit_loss_ratio
            }

        except Exception as e:
            logger.error(f"分析交易历史失败: {e}")
            return {}


# 全局统计服务实例
analysis_service = AnalysisService()