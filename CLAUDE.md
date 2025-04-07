# Project Guidelines for LLMgine

## Build & Test Commands
- Install dependencies: `make install` or `uv sync`
- Lint: `make check` or `uv run pre-commit run -a`
- Type check: `uv run mypy`
- Run all tests: `make test` or `uv run python -m pytest --doctest-modules`
- Run specific test: `uv run python -m pytest tests/test_file.py::test_function -v`
- Build documentation: `make docs`

## Code Style Guidelines
- **Python Version**: Python 3.9+
- **Formatting**: Ruff for linting and formatting
- **Line Length**: 120 characters maximum
- **Imports**: Use isort (via Ruff) - group imports by standard library, third-party, local
- **Types**: Strict typing with MyPy - all functions must have type annotations
- **Naming**: Follow PEP8 - snake_case for functions/variables, PascalCase for classes
- **Documentation**: Docstrings for all public modules, classes, and functions
- **Error Handling**: Use specific exception types, handle exceptions explicitly
- **Pre-commit Hooks**: All code must pass pre-commit hooks before committing

## Architecture & Design Philosophy
- Follow Domain-Driven Design principles from Cosmic Python book
- Use event-driven architecture with command/event message buses
- Embrace "ports and adapters" / hexagonal architecture
- Practice inversion of control and dependency injection
- Focus on small, composable patterns rather than monolithic frameworks
- Separate domain models from infrastructure concerns
- Design for testability with clear abstractions and interfaces

## Development Workflow
- Use `make help` to see all available commands
- Always run `make check` before committing changes