import pytest
import unittest
import sys
import os

# Add the app directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def run_all_tests():
    """Run all tests in the tests directory."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_specific_test_module(module_name):
    """Run tests for a specific module."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{module_name}')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_service_tests():
    """Run tests for all service modules."""
    service_test_modules = [
        'test_price_tracker_service',
        'test_daily_recommender_service',
        'test_improve_prompt_service'
    ]
    
    all_passed = True
    for module in service_test_modules:
        print(f"\n{'='*50}")
        print(f"Running {module}")
        print('='*50)
        
        success = run_specific_test_module(module)
        if not success:
            all_passed = False
    
    return all_passed

def run_component_tests():
    """Run tests for all component modules."""
    component_test_modules = [
        'test_notifier',
        'test_db_manager',
        'test_job_scheduler',
        'test_api_server'
    ]
    
    all_passed = True
    for module in component_test_modules:
        print(f"\n{'='*50}")
        print(f"Running {module}")
        print('='*50)
        
        success = run_specific_test_module(module)
        if not success:
            all_passed = False
    
    return all_passed

def run_helper_tests():
    """Run tests for all helper modules."""
    helper_test_modules = [
        'test_sheets_helpers',
        'test_ai_helpers',
        'test_utils',
        'test_schemas'
    ]
    
    all_passed = True
    for module in helper_test_modules:
        print(f"\n{'='*50}")
        print(f"Running {module}")
        print('='*50)
        
        success = run_specific_test_module(module)
        if not success:
            all_passed = False
    
    return all_passed

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run tests for the stocklerts application')
    parser.add_argument('--services', action='store_true', help='Run only service tests')
    parser.add_argument('--components', action='store_true', help='Run only component tests')
    parser.add_argument('--helpers', action='store_true', help='Run only helper tests')
    parser.add_argument('--module', type=str, help='Run tests for a specific module')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    
    args = parser.parse_args()
    
    success = True
    
    if args.module:
        success = run_specific_test_module(args.module)
    elif args.services:
        success = run_service_tests()
    elif args.components:
        success = run_component_tests()
    elif args.helpers:
        success = run_helper_tests()
    else:
        # Run all tests by default
        print("Running all tests...")
        success = run_all_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)