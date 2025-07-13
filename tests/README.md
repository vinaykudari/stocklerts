# Stocklerts Test Suite

This directory contains comprehensive tests for all services and components in the stocklerts application.

## Test Structure

```
tests/
├── __init__.py                    # Test package initialization
├── run_tests.py                   # Test runner script
├── pytest.ini                    # Pytest configuration
├── README.md                      # This file
├── test_api_server.py            # API server tests
├── test_daily_recommender_service.py  # Daily recommender service tests
├── test_db_manager.py            # Database manager tests
├── test_improve_prompt_service.py # Improve prompt service tests
├── test_job_scheduler.py         # Job scheduler tests
├── test_notifier.py              # Notification system tests
├── test_price_tracker_service.py # Price tracker service tests
├── test_schemas.py               # Schema validation tests
├── test_sheets_helpers.py        # Google Sheets helper tests
├── test_ai_helpers.py            # AI helper tests (Gemini/Perplexity)
└── test_utils.py                 # Utility function tests
```

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
# or
python tests/run_tests.py --all
```

### Run Specific Test Categories
```bash
# Run only service tests
python tests/run_tests.py --services

# Run only component tests
python tests/run_tests.py --components

# Run only helper tests
python tests/run_tests.py --helpers
```

### Run Specific Test Module
```bash
python tests/run_tests.py --module test_price_tracker_service
```

### Using Pytest Directly
```bash
# Run all tests with pytest
pytest tests/

# Run specific test file
pytest tests/test_price_tracker_service.py

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run with specific markers
pytest tests/ -m "not slow"
pytest tests/ -m "unit"
pytest tests/ -m "integration"
```

## Test Categories

### Service Tests
- **test_price_tracker_service.py**: Tests for stock price monitoring and alert triggering
- **test_daily_recommender_service.py**: Tests for daily stock recommendations and performance tracking
- **test_improve_prompt_service.py**: Tests for AI prompt improvement functionality

### Component Tests
- **test_api_server.py**: Tests for HTTP API endpoints and request handling
- **test_db_manager.py**: Tests for database operations and data persistence
- **test_job_scheduler.py**: Tests for scheduled job management
- **test_notifier.py**: Tests for push notification system

### Helper Tests
- **test_sheets_helpers.py**: Tests for Google Sheets integration
- **test_ai_helpers.py**: Tests for AI service integrations (Gemini, Perplexity)
- **test_utils.py**: Tests for utility functions (time, crypto, config)
- **test_schemas.py**: Tests for JSON schema validation

## Test Features

### Mocking and Isolation
- All tests use mocking to isolate units under test
- External API calls are mocked to prevent actual API usage
- Database tests use in-memory SQLite for isolation

### Coverage Areas
- **Happy Path Testing**: Normal operation scenarios
- **Error Handling**: Exception scenarios and edge cases
- **Edge Cases**: Boundary conditions and unusual inputs
- **Integration**: Component interaction testing
- **Configuration**: Environment variable and config handling

### Test Markers
- `@pytest.mark.slow`: For tests that take longer to run
- `@pytest.mark.integration`: For integration tests
- `@pytest.mark.unit`: For unit tests
- `@pytest.mark.api`: For API endpoint tests
- `@pytest.mark.database`: For database operation tests
- `@pytest.mark.external`: For tests requiring external services

## Environment Setup

### Required Dependencies
```bash
pip install pytest pytest-cov pytest-mock
```

### Environment Variables for Testing
The following environment variables are set automatically for tests:
- `TESTING=true`
- `FINNHUB_API_KEY=test_api_key`
- `ENCRYPT_KEY=test_encrypt_key`
- Google Sheets variables are set to empty strings

### Mock Data
Tests use realistic mock data that matches the expected data structures:
- Stock quotes with proper price and percentage data
- User configurations with encrypted account IDs
- AI responses with valid JSON schemas
- Database records with proper relationships

## Best Practices

### Writing New Tests
1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external dependencies
3. **Assertions**: Use specific assertions with clear error messages
4. **Setup/Teardown**: Use setUp() and tearDown() methods appropriately
5. **Documentation**: Include docstrings explaining test purpose

### Test Naming
- Test files: `test_<module_name>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<functionality>_<scenario>`

### Example Test Structure
```python
class TestServiceName(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Initialize mocks and test data
        
    def test_function_name_success(self):
        """Test successful operation."""
        # Arrange, Act, Assert
        
    def test_function_name_error_scenario(self):
        """Test error handling."""
        # Test exception scenarios
```

## Continuous Integration

These tests are designed to run in CI/CD environments:
- No external dependencies required
- Fast execution with mocked services
- Clear pass/fail indicators
- Coverage reporting available

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure the app directory is in Python path
2. **Mock Failures**: Check that mocks match actual function signatures
3. **Database Errors**: Verify in-memory database setup
4. **Environment Variables**: Check test environment configuration

### Debug Mode
Run tests with verbose output:
```bash
python tests/run_tests.py --module test_name -v
pytest tests/test_name.py -v -s
```