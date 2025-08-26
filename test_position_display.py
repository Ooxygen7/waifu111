#!/usr/bin/env python3
"""
测试仓位显示格式修改
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_core.services.trading_service import TradingService

def test_price_precision():
    """测试价格精度功能"""
    service = TradingService()

    # 测试高价格 (> 0.01 USDT)
    high_price = 1.23456789
    formatted = service._format_price(high_price)
    print(f"高价格 {high_price} -> {formatted} (应为4位小数)")

    # 测试低价格 (< 0.01 USDT)
    low_price = 0.0000123456789
    formatted = service._format_price(low_price)
    print(f"低价格 {low_price} -> {formatted} (应为8位小数)")

    # 测试边界价格 (= 0.01 USDT)
    boundary_price = 0.01
    formatted = service._format_price(boundary_price)
    print(f"边界价格 {boundary_price} -> {formatted} (应为4位小数)")

def test_position_format():
    """测试仓位显示格式"""
    service = TradingService()

    # 模拟仓位数据
    test_positions = [
        {
            'symbol': 'XRP/USDT',
            'side': 'long',
            'size': 100.0,
            'entry_price': 1.2345,
            'liquidation_price': 1.1
        },
        {
            'symbol': 'BTC/USDT',
            'side': 'short',
            'size': 50.0,
            'entry_price': 0.00001234,
            'liquidation_price': 0.00001111
        },
        {
            'symbol': 'ETH/USDT',
            'side': 'long',
            'size': 75.0,
            'entry_price': 0.0005,
            'liquidation_price': 0.00045
        }
    ]

    print("\n=== 仓位显示格式测试 ===")
    for i, pos in enumerate(test_positions, 1):
        # 使用不同emoji表示多空方向
        side_emoji = "📈" if pos['side'] == 'long' else "📉"

        # 移除/USDT后缀，只显示币种
        coin_symbol = pos['symbol'].replace('/USDT', '')

        # 使用动态价格精度
        formatted_entry_price = service._format_price(pos['entry_price'])
        formatted_current_price = service._format_price(pos['entry_price'] * 1.01)  # 模拟当前价格
        formatted_liquidation_price = service._format_price(pos['liquidation_price'])

        position_display = (
            f"{side_emoji} {coin_symbol}\n"
            f"   仓位: {pos['size']:.2f} USDT\n"
            f"   开仓价: {formatted_entry_price}\n"
            f"   当前价: {formatted_current_price}\n"
            f"   盈亏: +1.23 USDT (+1.23%)\n"
            f"   强平价: {formatted_liquidation_price}"
        )

        print(f"\n仓位 {i}:")
        print(position_display)

if __name__ == "__main__":
    print("开始测试仓位显示格式修改...")
    test_price_precision()
    test_position_format()
    print("\n测试完成！")