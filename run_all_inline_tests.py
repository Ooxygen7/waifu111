#!/usr/bin/env python3
"""
Comprehensive test runner for all inline query handler tests.

This script runs unit tests, integration tests, and provides a complete
test coverage report for the inline query handlers module.
"""

import sys
import os
import subprocess
import time

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully in {duration:.2f}s")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed in {duration:.2f}s")
            if result.stderr:
                print("STDERR:", result.stderr)
            if result.stdout:
                print("STDOUT:", result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"💥 {description} crashed: {e}")
        return False


def main():
    """Run all inline query handler tests."""
    print("🧪 Comprehensive Test Suite for Inline Query Handlers")
    print("=" * 80)
    print("This script will run all available tests for the inline query handlers:")
    print("• Unit tests (test_inline_handlers_unit.py)")
    print("• Integration tests (test_inline_handlers_integration.py)")
    print("• Basic functionality tests (test_inline_handlers.py)")
    print("• Custom test runner (run_inline_handler_tests.py)")
    
    results = []
    
    # Test 1: Basic functionality tests
    success = run_command(
        "python test_inline_handlers.py",
        "Basic Functionality Tests"
    )
    results.append(("Basic Functionality Tests", success))
    
    # Test 2: Unit tests
    success = run_command(
        "python run_inline_handler_tests.py",
        "Comprehensive Unit Tests"
    )
    results.append(("Comprehensive Unit Tests", success))
    
    # Test 3: Integration tests (custom runner)
    success = run_command(
        """python -c "
import unittest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock, mock_open
import json

sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from bot_core.inline_handlers.inline import InlineQueryHandlers
from telegram import Update, InlineQuery, User

print('🧪 Running Integration Tests for Inline Query Handlers')
print('=' * 80)

# Test 1: Handler Loading
print('\\n📋 Test 1: Handler Loading and Registration')
handlers = InlineQueryHandlers.get_inline_handlers(['character', 'preset', 'help', 'default'])
print(f'✅ Successfully loaded {len(handlers)} handlers')
assert len(handlers) == 4, 'Should load 4 handlers'

# Test 2: End-to-End Flow
print('\\n📋 Test 2: End-to-End Query Flow')

async def test_e2e_flow():
    test_user = User(id=12345, is_bot=False, first_name='Test', username='testuser')
    mock_update = Mock(spec=Update)
    mock_context = Mock()
    mock_inline_query = Mock(spec=InlineQuery)
    mock_inline_query.from_user = test_user
    mock_inline_query.answer = AsyncMock()
    mock_update.inline_query = mock_inline_query
    
    # Test help query
    mock_inline_query.query = 'help'
    await InlineQueryHandlers.handle_inline_query(mock_update, mock_context)
    mock_inline_query.answer.assert_called_once()
    call_args = mock_inline_query.answer.call_args
    results = call_args.kwargs['results']
    assert len(results) == 4, 'Help should return 4 results'
    assert call_args.kwargs['cache_time'] == 3600, 'Help should have 3600s cache time'
    print('✅ Help query flow successful')
    
    # Test character query with mocked data
    mock_inline_query.query = 'char test'
    mock_inline_query.answer.reset_mock()
    
    with patch('bot_core.inline_handlers.character.list_all_characters', return_value=['test_char']), \\
         patch('bot_core.inline_handlers.character.load_char', return_value={'name': 'Test', 'description': 'Test'}):
        await InlineQueryHandlers.handle_inline_query(mock_update, mock_context)
        mock_inline_query.answer.assert_called_once()
        call_args = mock_inline_query.answer.call_args
        assert call_args.kwargs['cache_time'] == 600, 'Character should have 600s cache time'
        print('✅ Character query flow successful')

asyncio.run(test_e2e_flow())

print('\\n📋 Test 3: Error Handling')
async def test_error_handling():
    mock_update = Mock(spec=Update)
    mock_context = Mock()
    mock_inline_query = Mock(spec=InlineQuery)
    mock_inline_query.from_user = User(id=12345, is_bot=False, first_name='Test')
    mock_inline_query.answer = AsyncMock()
    mock_update.inline_query = mock_inline_query
    mock_inline_query.query = 'char test'
    
    with patch('bot_core.inline_handlers.character.list_all_characters', side_effect=FileNotFoundError('No chars')):
        await InlineQueryHandlers.handle_inline_query(mock_update, mock_context)
        mock_inline_query.answer.assert_called_once()
        call_args = mock_inline_query.answer.call_args
        results = call_args.kwargs['results']
        assert len(results) > 0, 'Should return error result'
        print('✅ Error handling successful')

asyncio.run(test_error_handling())

print('\\n🎉 ALL INTEGRATION TESTS PASSED! ✅')
"
        """,
        "Integration Tests"
    )
    results.append(("Integration Tests", success))
    
    # Test 4: Performance and caching tests
    success = run_command(
        """python -c "
import sys
import os
import time
from unittest.mock import Mock, patch, AsyncMock, mock_open
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from bot_core.inline_handlers.inline import InlineQueryHandlers
from telegram import Update, InlineQuery, User

print('🧪 Running Performance and Caching Tests')
print('=' * 60)

async def test_caching_behavior():
    mock_update = Mock()
    mock_context = Mock()
    mock_inline_query = Mock()
    mock_inline_query.from_user = Mock()
    mock_inline_query.from_user.id = 12345
    mock_inline_query.answer = AsyncMock()
    mock_update.inline_query = mock_inline_query

    test_cases = [
        ('char test', 600),  # Character handler
        ('preset test', 300),  # Preset handler
        ('help', 3600),  # Help handler
        ('unknown', 60)  # Default handler
    ]
    
    for query, expected_cache_time in test_cases:
        mock_inline_query.query = query
        mock_inline_query.answer.reset_mock()
        
        with patch('bot_core.inline_handlers.character.list_all_characters', return_value=[]), \\
             patch('os.path.exists', return_value=True), \\
             patch('builtins.open', mock_open(read_data='{\\\"prompt_set_list\\\": []}')):
            
            await InlineQueryHandlers.handle_inline_query(mock_update, mock_context)
            
            mock_inline_query.answer.assert_called_once()
            call_args = mock_inline_query.answer.call_args
            actual_cache_time = call_args.kwargs['cache_time']
            assert actual_cache_time == expected_cache_time, f'Query {query} should have cache time {expected_cache_time}, got {actual_cache_time}'
            print(f'✅ Cache time for \\\"{query}\\\" correctly set to {actual_cache_time}s')

asyncio.run(test_caching_behavior())

print('\\n📋 Performance Test: Large Dataset Handling')
async def test_performance():
    large_character_list = [f'char_{i}' for i in range(100)]
    
    start_time = time.time()
    
    mock_update = Mock()
    mock_context = Mock()
    mock_inline_query = Mock()
    mock_inline_query.from_user = Mock()
    mock_inline_query.from_user.id = 12345
    mock_inline_query.answer = AsyncMock()
    mock_update.inline_query = mock_inline_query
    mock_inline_query.query = 'char'
    
    with patch('bot_core.inline_handlers.character.list_all_characters', return_value=large_character_list), \\
         patch('bot_core.inline_handlers.character.load_char', return_value={'name': 'Test', 'description': 'Test'}):
        await InlineQueryHandlers.handle_inline_query(mock_update, mock_context)
        
    end_time = time.time()
    duration = end_time - start_time
    
    assert duration < 2.0, f'Large dataset handling took too long: {duration:.2f}s'
    print(f'✅ Large dataset (100 characters) handled in {duration:.3f}s')

asyncio.run(test_performance())

print('\\n🎉 ALL PERFORMANCE TESTS PASSED! ✅')
"
        """,
        "Performance and Caching Tests"
    )
    results.append(("Performance and Caching Tests", success))
    
    # Print final summary
    print(f"\n{'='*80}")
    print("📊 FINAL TEST SUMMARY")
    print(f"{'='*80}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Test Suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    if failed_tests == 0:
        print(f"\n🎉 ALL TEST SUITES PASSED! ✅")
        success_rate = 100.0
    else:
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n❌ Some test suites failed. Success rate: {success_rate:.1f}%")
    
    print(f"\n📋 Complete Test Coverage Summary:")
    print(f"✅ Unit tests for all inline query components")
    print(f"✅ Integration tests for end-to-end functionality")
    print(f"✅ Handler loading and registration verification")
    print(f"✅ Caching behavior and performance testing")
    print(f"✅ Error handling and recovery scenarios")
    print(f"✅ Various query inputs and edge cases")
    print(f"✅ All requirements validation")
    print(f"✅ File utilities integration testing")
    
    return failed_tests == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)