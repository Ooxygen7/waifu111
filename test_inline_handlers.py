#!/usr/bin/env python3
"""
Simple test script for inline query handlers.
This script tests the basic functionality without requiring a full bot setup.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_core.inline_handlers.inline import InlineQueryHandlers


def test_query_parsing():
    """Test the inline query parsing logic."""
    print("Testing query parsing...")
    
    test_cases = [
        ("", ("", "")),
        ("help", ("help", "")),
        ("char miku", ("char", "miku")),
        ("preset nsfw mode", ("preset", "nsfw mode")),
        ("  char  hatsune  ", ("char", "hatsune")),
        ("single", ("single", "")),
    ]
    
    for query, expected in test_cases:
        result = InlineQueryHandlers.parse_inline_query(query)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{query}' -> {result} (expected: {expected})")
        if result != expected:
            return False
    
    return True


def test_handler_loading():
    """Test handler loading with real test handlers."""
    print("Testing handler loading...")
    
    try:
        # Test loading nonexistent module (should handle gracefully)
        handlers = InlineQueryHandlers.get_inline_handlers(['nonexistent'])
        print(f"  ✓ Nonexistent module handled gracefully (found {len(handlers)} handlers)")
        
        # Test loading actual test handler
        handlers = InlineQueryHandlers.get_inline_handlers(['test_handler'])
        enabled_handlers = [h for h in handlers if h.meta.enabled]
        disabled_count = len(handlers) - len(enabled_handlers)
        
        print(f"  ✓ Test handler loading completed (found {len(enabled_handlers)} enabled, {disabled_count} disabled)")
        
        # Verify we found the expected test handler
        test_handler_found = any(h.meta.trigger == 'test' for h in enabled_handlers)
        disabled_handler_filtered = not any(h.meta.trigger == 'disabled' for h in enabled_handlers)
        
        if test_handler_found and disabled_handler_filtered:
            print("  ✓ Test handler found and disabled handler filtered correctly")
            return True
        else:
            print("  ✗ Handler filtering not working correctly")
            return False
            
    except Exception as e:
        print(f"  ✗ Handler loading failed: {e}")
        return False


def test_dispatcher():
    """Test the inline query dispatcher."""
    print("Testing dispatcher...")
    
    try:
        from bot_core.inline_handlers.inline import create_inline_query_handler, InlineQueryDispatcher
        
        # Create dispatcher with test handlers
        dispatcher = create_inline_query_handler(['test_handler'])
        
        if isinstance(dispatcher, InlineQueryDispatcher):
            print("  ✓ Dispatcher created successfully")
            print(f"  ✓ Dispatcher loaded {len(dispatcher.handlers)} handlers")
            
            # Check handler mapping
            if 'test' in dispatcher._handler_map:
                print("  ✓ Handler mapping created correctly")
                return True
            else:
                print("  ✗ Handler mapping not created correctly")
                return False
        else:
            print("  ✗ Dispatcher creation failed")
            return False
            
    except Exception as e:
        print(f"  ✗ Dispatcher test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Running inline handlers tests...\n")
    
    tests = [
        test_query_parsing,
        test_handler_loading,
        test_dispatcher,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)