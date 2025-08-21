#!/usr/bin/env python3
"""
测试修改后的市场深度获取功能
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.tools import MarketTools

async def test_market_depth():
    """测试市场深度获取功能"""
    try:
        print("开始测试市场深度获取功能...")

        # 测试获取市场深度
        result = await MarketTools.get_market_depth(
            symbol="BTC/USDT",
            depth=10,
            exchange="binance"
        )

        print("测试结果:")
        print(result["display"])

        # 验证聚合逻辑
        print("\n=== 验证聚合逻辑 ===")

        # 测试聚合函数
        test_orders = [
            [100.0, 1.0],
            [101.0, 2.0],
            [99.0, 1.5],
            [102.0, 0.5],
            [98.0, 2.5]
        ]
        current_price = 100.0

        aggregated = MarketTools.aggregate_by_dynamic_levels(test_orders, 5)
        print(f"测试订单: {test_orders}")
        print(f"当前价格: {current_price}")
        print(f"聚合结果: {aggregated}")

        print("\n测试完成!")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_market_depth())