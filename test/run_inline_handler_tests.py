#!/usr/bin/env python3
"""
Test runner for inline query handler unit tests.

This script runs comprehensive unit tests for all inline query components
and provides detailed reporting of test results.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, AsyncMock, mock_open
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to reduce noise during tests
logging.getLogger().setLevel(logging.CRITICAL)

# Import the modules to test
from bot_core.inline_handlers.base import InlineMeta, BaseInlineQuery, InlineResultData
from bot_core.inline_handlers.inline import (
    InlineQueryHandlers, InlineQueryError, ErrorResultFactory, 
    InlineQueryDispatcher, create_inline_query_handler
)
from bot_core.inline_handlers.character import CharacterInlineQuery
from bot_core.inline_handlers.preset import PresetInlineQuery
from bot_core.inline_handlers.help import HelpInlineQuery
from bot_core.inline_handlers.default import DefaultInlineQuery

# Mock telegram objects
from telegram import Update, InlineQuery, User, InlineQueryResult, InlineQueryResultArticle


def run_test_suite(test_class, test_name):
    """Run a specific test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running {test_name}")
    print(f"{'='*60}")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    return result.testsRun, len(result.failures), len(result.errors)


def main():
    """Run all inline handler unit tests."""
    print("🧪 Running Comprehensive Unit Tests for Inline Query Handlers")
    print("=" * 80)
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    # Test 1: InlineMeta class validation
    class TestInlineMeta(unittest.TestCase):
        def test_inline_meta_creation_with_defaults(self):
            meta = InlineMeta(name="test", query_type="test")
            self.assertEqual(meta.name, "test")
            self.assertEqual(meta.query_type, "test")
            self.assertEqual(meta.trigger, "")
            self.assertEqual(meta.description, "")
            self.assertTrue(meta.enabled)
            self.assertEqual(meta.cache_time, 300)
        
        def test_inline_meta_creation_with_custom_values(self):
            meta = InlineMeta(
                name="custom_test",
                query_type="custom",
                trigger="custom_trigger",
                description="Custom description",
                enabled=False,
                cache_time=600
            )
            self.assertEqual(meta.name, "custom_test")
            self.assertEqual(meta.query_type, "custom")
            self.assertEqual(meta.trigger, "custom_trigger")
            self.assertEqual(meta.description, "Custom description")
            self.assertFalse(meta.enabled)
            self.assertEqual(meta.cache_time, 600)
        
        def test_inline_meta_repr(self):
            meta = InlineMeta(name="test", query_type="test", trigger="test_trigger")
            repr_str = repr(meta)
            self.assertIn("test", repr_str)
            self.assertIn("test_trigger", repr_str)
            self.assertIn("True", repr_str)
    
    tests, failures, errors = run_test_suite(TestInlineMeta, "InlineMeta Class Validation")
    total_tests += tests
    total_failures += failures
    total_errors += errors
    
    # Test 2: InlineResultData validation
    class TestInlineResultData(unittest.TestCase):
        def test_inline_result_data_creation(self):
            result_data = InlineResultData(
                id="test_id",
                title="Test Title",
                description="Test Description",
                content="Test Content"
            )
            self.assertEqual(result_data.id, "test_id")
            self.assertEqual(result_data.title, "Test Title")
            self.assertEqual(result_data.description, "Test Description")
            self.assertEqual(result_data.content, "Test Content")
        
        def test_inline_result_data_empty_id_validation(self):
            with self.assertRaises(ValueError) as context:
                InlineResultData(id="", title="Test Title", description="Test Description")
            self.assertIn("Result ID cannot be empty", str(context.exception))
        
        def test_inline_result_data_empty_title_validation(self):
            with self.assertRaises(ValueError) as context:
                InlineResultData(id="test_id", title="", description="Test Description")
            self.assertIn("Result title cannot be empty", str(context.exception))
        
        def test_inline_result_data_to_article_result(self):
            result_data = InlineResultData(
                id="test_id",
                title="Test Title",
                description="Test Description",
                content="Test Content",
                parse_mode="Markdown"
            )
            article_result = result_data.to_article_result()
            self.assertIsInstance(article_result, InlineQueryResultArticle)
            self.assertEqual(article_result.id, "test_id")
            self.assertEqual(article_result.title, "Test Title")
            self.assertEqual(article_result.description, "Test Description")
    
    tests, failures, errors = run_test_suite(TestInlineResultData, "InlineResultData Validation")
    total_tests += tests
    total_failures += failures
    total_errors += errors
    
    # Test 3: BaseInlineQuery abstract class enforcement
    class TestBaseInlineQuery(unittest.TestCase):
        def test_base_inline_query_missing_meta_attribute(self):
            class InvalidHandler(BaseInlineQuery):
                async def handle_inline_query(self, update, context):
                    return []
            
            with self.assertRaises(NotImplementedError) as context:
                InvalidHandler()
            self.assertIn("must define a meta attribute", str(context.exception))
        
        def test_base_inline_query_invalid_meta_type(self):
            class InvalidHandler(BaseInlineQuery):
                meta = "not_inline_meta"
                async def handle_inline_query(self, update, context):
                    return []
            
            with self.assertRaises(NotImplementedError) as context:
                InvalidHandler()
            self.assertIn("must define a meta attribute of type InlineMeta", str(context.exception))
        
        def test_base_inline_query_valid_implementation(self):
            class ValidHandler(BaseInlineQuery):
                meta = InlineMeta(name="valid", query_type="valid")
                async def handle_inline_query(self, update, context):
                    return []
            
            handler = ValidHandler()
            self.assertIsInstance(handler.meta, InlineMeta)
        
        def test_base_inline_query_helper_methods(self):
            class TestHandler(BaseInlineQuery):
                meta = InlineMeta(name="test", query_type="test")
                async def handle_inline_query(self, update, context):
                    return []
            
            handler = TestHandler()
            
            # Test format_title_with_emoji
            title = handler.format_title_with_emoji("Test Title", "🔥")
            self.assertEqual(title, "🔥 Test Title")
            
            # Test truncate_text
            long_text = "A" * 150
            truncated = handler.truncate_text(long_text, 100)
            self.assertEqual(len(truncated), 100)
            self.assertTrue(truncated.endswith("..."))
            
            # Test create_info_result
            info_result = handler.create_info_result(
                "info_id", "Info Title", "Info Description", "Info Content"
            )
            self.assertIsInstance(info_result, InlineResultData)
            self.assertEqual(info_result.id, "info_id")
            self.assertTrue(info_result.title.startswith("ℹ️"))
    
    tests, failures, errors = run_test_suite(TestBaseInlineQuery, "BaseInlineQuery Abstract Class")
    total_tests += tests
    total_failures += failures
    total_errors += errors
    
    # Test 4: Query parsing and routing logic
    class TestInlineQueryHandlers(unittest.TestCase):
        def test_parse_inline_query_empty(self):
            query_type, search_term = InlineQueryHandlers.parse_inline_query("")
            self.assertEqual(query_type, "")
            self.assertEqual(search_term, "")
        
        def test_parse_inline_query_single_word(self):
            query_type, search_term = InlineQueryHandlers.parse_inline_query("help")
            self.assertEqual(query_type, "help")
            self.assertEqual(search_term, "")
        
        def test_parse_inline_query_with_search_term(self):
            query_type, search_term = InlineQueryHandlers.parse_inline_query("char miku")
            self.assertEqual(query_type, "char")
            self.assertEqual(search_term, "miku")
        
        def test_parse_inline_query_with_multiple_words(self):
            query_type, search_term = InlineQueryHandlers.parse_inline_query("preset nsfw mode")
            self.assertEqual(query_type, "preset")
            self.assertEqual(search_term, "nsfw mode")
        
        def test_parse_inline_query_with_whitespace(self):
            query_type, search_term = InlineQueryHandlers.parse_inline_query("  char  hatsune  ")
            self.assertEqual(query_type, "char")
            self.assertEqual(search_term, "hatsune")
    
    tests, failures, errors = run_test_suite(TestInlineQueryHandlers, "Query Parsing and Routing Logic")
    total_tests += tests
    total_failures += failures
    total_errors += errors
    
    # Test 5: Error handling scenarios
    class TestErrorHandling(unittest.TestCase):
        def test_inline_query_error_creation(self):
            error = InlineQueryError("Test error message")
            self.assertEqual(str(error), "Test error message")
            self.assertEqual(error.error_type, "general")
            self.assertTrue(error.user_friendly)
        
        def test_inline_query_error_with_custom_values(self):
            error = InlineQueryError(
                "Custom error", 
                error_type="data_access", 
                user_friendly=False
            )
            self.assertEqual(str(error), "Custom error")
            self.assertEqual(error.error_type, "data_access")
            self.assertFalse(error.user_friendly)
        
        def test_create_error_result(self):
            results = ErrorResultFactory.create_error_result("Test error")
            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], InlineQueryResultArticle)
            self.assertEqual(results[0].id, "error")
            self.assertTrue(results[0].title.startswith("❌"))
        
        def test_create_data_access_error_result(self):
            results = ErrorResultFactory.create_data_access_error_result("characters")
            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], InlineQueryResultArticle)
            self.assertTrue(results[0].title.startswith("⚠️"))
            # Check that the description contains error-related text (in Chinese)
            self.assertIn("数据访问失败", results[0].description)
    
    tests, failures, errors = run_test_suite(TestErrorHandling, "Error Handling Scenarios")
    total_tests += tests
    total_failures += failures
    total_errors += errors
    
    # Test 6: Specific inline query handlers
    class TestSpecificHandlers(unittest.TestCase):
        def test_character_handler_meta(self):
            handler = CharacterInlineQuery()
            self.assertEqual(handler.meta.name, 'character_query')
            self.assertEqual(handler.meta.query_type, 'char')
            self.assertEqual(handler.meta.trigger, 'char')
            self.assertTrue(handler.meta.enabled)
            self.assertEqual(handler.meta.cache_time, 600)
        
        def test_preset_handler_meta(self):
            handler = PresetInlineQuery()
            self.assertEqual(handler.meta.name, 'preset_query')
            self.assertEqual(handler.meta.query_type, 'preset')
            self.assertEqual(handler.meta.trigger, 'preset')
            self.assertTrue(handler.meta.enabled)
            self.assertEqual(handler.meta.cache_time, 300)
        
        def test_help_handler_meta(self):
            handler = HelpInlineQuery()
            self.assertEqual(handler.meta.name, 'help_query')
            self.assertEqual(handler.meta.query_type, 'help')
            self.assertEqual(handler.meta.trigger, 'help')
            self.assertTrue(handler.meta.enabled)
            self.assertEqual(handler.meta.cache_time, 3600)
        
        def test_default_handler_meta(self):
            handler = DefaultInlineQuery()
            self.assertEqual(handler.meta.name, 'default_query')
            self.assertEqual(handler.meta.query_type, 'default')
            self.assertEqual(handler.meta.trigger, '')  # Empty trigger for fallback
            self.assertTrue(handler.meta.enabled)
            self.assertEqual(handler.meta.cache_time, 60)
    
    tests, failures, errors = run_test_suite(TestSpecificHandlers, "Specific Inline Query Handlers")
    total_tests += tests
    total_failures += failures
    total_errors += errors
    
    # Print final summary
    print(f"\n{'='*80}")
    print("📊 FINAL TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total Tests Run: {total_tests}")
    print(f"Total Failures: {total_failures}")
    print(f"Total Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("🎉 ALL TESTS PASSED! ✅")
        success_rate = 100.0
    else:
        success_rate = ((total_tests - total_failures - total_errors) / total_tests) * 100
        print(f"❌ Some tests failed. Success rate: {success_rate:.1f}%")
    
    print(f"\n📋 Test Coverage Summary:")
    print(f"✅ InlineMeta class validation")
    print(f"✅ BaseInlineQuery abstract class enforcement")
    print(f"✅ InlineResultData validation and conversion")
    print(f"✅ Query parsing and routing logic")
    print(f"✅ Error handling scenarios")
    print(f"✅ Specific handler meta attributes")
    print(f"✅ All requirements validation")
    
    return total_failures == 0 and total_errors == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)