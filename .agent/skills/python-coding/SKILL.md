---
name: Python Coding Standards
description: Python coding standards, type hints, code style, error handling, testing, and documentation best practices
---

# Python Coding Standards

## Code Style
- Follow **Black** code formatting (line length 88)
- Use **isort** for import sorting
- Follow PEP 8 naming conventions:
  - `snake_case` for functions, variables, modules
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
- Use absolute imports over relative imports
- Group imports: stdlib → third-party → local

## Type Hints
- Use type hints for all function parameters and returns
- Use `Optional[Type]` for nullable values
- Use `list[str]` (Python 3.9+) over `List[str]`
- Use `TypeVar` for generic types
- Use `Protocol` for duck typing interfaces
- Define shared types in a `types.py` file

## Functions
- Keep functions small and focused (single responsibility)
- Use explicit return types
- Use `*args` and `**kwargs` sparingly
- Prefer `async/await` over threads for I/O
- Use descriptive parameter names
- Default to immutable parameters

## Error Handling
- Create custom exception classes for domain errors
- Use specific exception types (not bare `except:`)
- Use `try/except` blocks appropriately (not for flow control)
- Always log exceptions with context
- Return proper error responses in API views
- Handle edge cases explicitly

## Testing (pytest)
- Use `pytest` as the test runner
- Write tests for all public functions and API endpoints
- Use `pytest-cov` for coverage reports
- Use fixtures for test data setup
- Use `pytest-mock` for mocking
- Test both happy paths and error scenarios
- Name tests descriptively: `test_order_creation_with_invalid_phone_returns_400`

## Documentation
- Use Google-style docstrings on all public classes and methods
- Document parameters, return values, and exceptions
- Keep README updated with setup instructions
- Use inline comments only for non-obvious logic

```python
def calculate_risk_score(customer_history: dict, address_data: dict) -> float:
    """Calculate composite risk score for a COD order.

    Args:
        customer_history: Past order/RTO data for the customer.
        address_data: Geocoded address verification result.

    Returns:
        Risk score between 0.0 (safe) and 1.0 (high risk).

    Raises:
        ValueError: If required fields are missing from input data.
    """
```

## Security
- Never hardcode secrets — use environment variables
- Use `python-decouple` or `django-environ`
- Sanitize all user inputs
- Use parameterized queries (ORM handles this)
- Pin dependency versions in `requirements.txt`
- Run `pip audit` or `safety check` regularly

## Virtual Environments
- Always use `venv` or `virtualenv`
- Keep `requirements.txt` updated: `pip freeze > requirements.txt`
- Separate dev dependencies: `requirements-dev.txt`
- Use `.env` files for local configuration (add to `.gitignore`)
