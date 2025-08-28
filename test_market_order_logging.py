#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试市价单执行日志记录
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_core.services.trading.order_service import order_service

async def test_market_order_execution():
    """测试市价单执行并观察日志"""
    print("开始测试市价单执行日志...")
    
    # 测试用户ID和群组ID
    test_user_id = 7007822593
    test_group_id = -1002683607935
    
    try:
        print(f"为用户 {test_user_id} 创建市价多单...")
        
        # 创建市价多单
        result = await order_service.create_market_order(
            user_id=test_user_id,
            group_id=test_group_id,
            symbol="BTC/USDT",
            direction="bid",  # 多单
            order_type="open",  # 开仓
            volume=1000.0  # 1000 USDT
        )
        
        print(f"订单创建结果: {result}")
        
        if result["success"]:
            print(f"订单ID: {result['order_id']}")
            if result.get("executed"):
                print("订单已立即执行")
            else:
                print("订单未立即执行，转为挂单")
        else:
            print(f"订单创建失败: {result.get('message')}")
            
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("测试完成")

if __name__ == "__main__":
    asyncio.run(test_market_order_execution())