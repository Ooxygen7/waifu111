#!/usr/bin/env python3
"""
测试函数迁移后的插件系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_function_imports():
    """测试函数导入是否正常"""
    print("=== 测试函数导入 ===")
    
    try:
        from plugins.fuck_plugin import analyze_image_for_rating
        print("✅ analyze_image_for_rating 从 fuck_plugin 导入成功")
    except ImportError as e:
        print(f"❌ analyze_image_for_rating 导入失败: {e}")
        return False
    
    try:
        from plugins.kao_plugin import analyze_image_for_kao
        print("✅ analyze_image_for_kao 从 kao_plugin 导入成功")
    except ImportError as e:
        print(f"❌ analyze_image_for_kao 导入失败: {e}")
        return False
    
    return True

def test_agent_functions_removed():
    """测试agent模块中的函数是否已被移除"""
    print("\n=== 测试agent模块函数移除 ===")
    
    try:
        from agent.llm_functions import analyze_image_for_rating
        print("❌ analyze_image_for_rating 仍在 agent.llm_functions 中")
        return False
    except ImportError:
        print("✅ analyze_image_for_rating 已从 agent.llm_functions 中移除")
    
    try:
        from agent.llm_functions import analyze_image_for_kao
        print("❌ analyze_image_for_kao 仍在 agent.llm_functions 中")
        return False
    except ImportError:
        print("✅ analyze_image_for_kao 已从 agent.llm_functions 中移除")
    
    return True

def test_features_import():
    """测试features模块的导入更新"""
    print("\n=== 测试features模块导入更新 ===")
    
    try:
        import bot_core.message_handlers.features
        print("✅ features模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ features模块导入失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试函数迁移...\n")
    
    tests = [
        test_function_imports,
        test_agent_functions_removed,
        test_features_import
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！函数迁移成功完成。")
        return True
    else:
        print("❌ 部分测试失败，请检查相关问题。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)