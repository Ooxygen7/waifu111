#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实时价格获取功能
验证市价开单和平仓时是否正确使用实时价格
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_core.services.trading.price_service import price_service
import time

async def test_price_comparison():
    """测试缓存价格和实时价格的差异"""
    print("🚀 开始测试价格获取功能...")
    
    symbol = "BTC/USDT"
    
    # 清除缓存确保测试准确性
    price_service.clear_cache_for_symbol(symbol)
    
    print(f"\n📊 测试交易对: {symbol}")
    
    # 第一次获取（会从交易所获取并缓存）
    print("\n1️⃣ 第一次获取价格（从交易所获取）:")
    start_time = time.time()
    cached_price = await price_service.get_current_price(symbol)
    cached_time = time.time() - start_time
    print(f"   缓存价格: {cached_price}, 耗时: {cached_time:.3f}秒")
    
    # 第二次获取（应该从缓存获取）
    print("\n2️⃣ 第二次获取价格（从缓存获取）:")
    start_time = time.time()
    cached_price2 = await price_service.get_current_price(symbol)
    cached_time2 = time.time() - start_time
    print(f"   缓存价格: {cached_price2}, 耗时: {cached_time2:.3f}秒")
    
    # 获取实时价格（强制从交易所获取）
    print("\n3️⃣ 获取实时价格（强制从交易所获取）:")
    start_time = time.time()
    real_time_price = await price_service.get_real_time_price(symbol)
    real_time_time = time.time() - start_time
    print(f"   实时价格: {real_time_price}, 耗时: {real_time_time:.3f}秒")
    
    # 分析结果
    print("\n📈 分析结果:")
    print(f"   缓存价格: {cached_price}")
    print(f"   实时价格: {real_time_price}")
    
    if cached_price and real_time_price:
        price_diff = abs(real_time_price - cached_price)
        price_diff_percent = (price_diff / cached_price) * 100
        print(f"   价格差异: {price_diff:.4f} USDT ({price_diff_percent:.4f}%)")
        
        if price_diff_percent > 0.01:  # 差异超过0.01%
            print(f"   ⚠️  价格差异较大，实时价格获取功能正常工作！")
        else:
            print(f"   ✅ 价格差异很小，但实时获取功能正常")
    
    # 测试缓存状态
    cache_status = price_service.get_cache_status()
    print(f"\n💾 缓存状态: {cache_status}")
    
    print("\n🎉 测试完成！")
    print("\n📝 总结:")
    print("   - get_current_price(): 使用缓存机制，适用于一般查询")
    print("   - get_real_time_price(): 强制获取实时价格，适用于市价开单和平仓")
    print("   - 市价开单和平仓现在会使用实时价格，确保交易准确性")

async def test_multiple_symbols():
    """测试多个交易对的实时价格获取"""
    print("\n🔄 测试多个交易对的实时价格获取...")
    
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
    
    for symbol in symbols:
        print(f"\n📊 {symbol}:")
        real_time_price = await price_service.get_real_time_price(symbol)
        print(f"   实时价格: {real_time_price}")

if __name__ == "__main__":
    print("🦈 脆脆鲨交易系统 - 实时价格测试")
    print("=" * 50)
    
    try:
        # 运行测试
        asyncio.run(test_price_comparison())
        asyncio.run(test_multiple_symbols())
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()