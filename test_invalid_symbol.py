#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不存在币种的订单创建逻辑
验证挂单时无法获取价格是否正确拒绝创建委托
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_core.services.trading.order_service import order_service
from bot_core.services.trading.account_service import account_service

async def test_invalid_symbol_orders():
    """测试不存在币种的订单创建"""
    print("🦈 脆脆鲨交易系统 - 不存在币种测试")
    print("=" * 50)
    
    # 测试用户信息
    user_id = 999999
    group_id = -999999
    
    # 确保测试群组存在
    from bot_core.data_repository.groups_repository import GroupsRepository
    try:
        result = GroupsRepository.group_info_create(group_id)
        if result['success']:
            print("🏠 已创建测试群组")
    except:
        pass  # 群组可能已存在
    
    # 确保用户有足够余额
    account = account_service.get_or_create_account(user_id, group_id)
    if account['balance'] < 1000:
        from bot_core.data_repository.trading_repository import TradingRepository
        TradingRepository.update_account_balance(user_id, group_id, 10000.0, 0.0)
        print("💰 已为测试用户充值余额")
    
    # 测试案例
    test_cases = [
        {
            "name": "限价单 - 不存在的币种",
            "symbol": "INVALIDCOIN/USDT",
            "role": "maker",
            "price": 1.0
        },
        {
            "name": "市价单 - 不存在的币种", 
            "symbol": "FAKECOIN/USDT",
            "role": "taker",
            "price": None
        },
        {
            "name": "限价单 - 拼写错误的币种",
            "symbol": "BTCC/USDT",  # 故意拼错BTC
            "role": "maker",
            "price": 50000.0
        },
        {
            "name": "市价单 - 随机字符串币种",
            "symbol": "BASDLKJ/USDT",  # 用户输入的例子
            "role": "taker", 
            "price": None
        }
    ]
    
    print("\n🧪 开始测试不存在币种的订单创建...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📋 测试 {i}: {test_case['name']}")
        print(f"   币种: {test_case['symbol']}")
        print(f"   类型: {'限价单' if test_case['role'] == 'maker' else '市价单'}")
        
        try:
            result = await order_service.create_order(
                user_id=user_id,
                group_id=group_id,
                symbol=test_case['symbol'],
                direction='bid',
                role=test_case['role'],
                order_type='open',
                operation='addition',
                volume=100.0,
                price=test_case['price']
            )
            
            if result['success']:
                print(f"   ❌ 测试失败: 订单创建成功了（不应该成功）")
                print(f"      订单ID: {result.get('order_id')}")
                # 如果意外创建成功，尝试取消订单
                if 'order_id' in result:
                    cancel_result = order_service.cancel_order(result['order_id'])
                    if cancel_result['success']:
                        print(f"      已取消意外创建的订单")
            else:
                print(f"   ✅ 测试通过: 正确拒绝了订单创建")
                print(f"      错误信息: {result.get('message')}")
                
        except Exception as e:
            print(f"   ⚠️  测试异常: {e}")
        
        print()
    
    print("🎯 测试总结:")
    print("   - 限价单应该在价格验证阶段检查币种有效性")
    print("   - 市价单应该在执行阶段检查币种有效性")
    print("   - 所有不存在的币种都应该被正确拒绝")
    print("   - 不应该创建任何无效的委托订单")

async def test_valid_symbol_orders():
    """测试存在币种的订单创建（对比测试）"""
    print("\n🔄 对比测试 - 有效币种订单创建...\n")
    
    user_id = 999999
    group_id = -999999
    
    # 测试有效币种
    valid_cases = [
        {
            "name": "限价单 - BTC/USDT",
            "symbol": "BTC/USDT",
            "role": "maker",
            "price": 50000.0
        },
        {
            "name": "市价单 - ETH/USDT",
            "symbol": "ETH/USDT", 
            "role": "taker",
            "price": None
        }
    ]
    
    for i, test_case in enumerate(valid_cases, 1):
        print(f"📋 对比测试 {i}: {test_case['name']}")
        print(f"   币种: {test_case['symbol']}")
        
        try:
            result = await order_service.create_order(
                user_id=user_id,
                group_id=group_id,
                symbol=test_case['symbol'],
                direction='bid',
                role=test_case['role'],
                order_type='open',
                operation='addition',
                volume=100.0,
                price=test_case['price']
            )
            
            if result['success']:
                print(f"   ✅ 有效币种订单创建成功")
                if 'order_id' in result:
                    # 立即取消测试订单
                    cancel_result = order_service.cancel_order(result['order_id'])
                    if cancel_result['success']:
                        print(f"      已取消测试订单: {result['order_id']}")
            else:
                print(f"   ⚠️  有效币种订单创建失败: {result.get('message')}")
                
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
        
        print()

if __name__ == "__main__":
    try:
        # 运行测试
        asyncio.run(test_invalid_symbol_orders())
        asyncio.run(test_valid_symbol_orders())
        
        print("\n🎉 所有测试完成！")
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()