# 1. Adoption of Pre-Commit Hooks

Date: 2026-02-19

## Status

Accepted

## Context

The project codebase was suffering from inconsistent formatting, unused imports, and potential security risks (hardcoded secrets). Manual enforcement of coding standards was inefficient and prone to error. We needed a way to automatically enforce these standards before code is committed to the repository.

## Decision

We decided to adopt **pre-commit hooks** to automate code quality and security checks.

We configured the following hooks:
*   **Ruff**: For extremely fast Python linting and formatting. It replaces Flake8, Black, and isort.
*   **Gitleaks**: To scan for potential hardcoded secrets and API keys.
*   **Trailing Whitespace & End-of-File Fixer**: For general file hygiene.
*   **Check YAML**: To ensure validity of configuration files.

We also integrated these tools with `uv` for dependency management.

## Consequences

### Positive
*   **Consistent Code Style**: Code is automatically formatted, eliminating debates about style.
*   **Early Error Detection**: Syntax errors, unused imports, and other bugs are caught before commit.
*   **Security**: Accidental commitment of secrets is significantly reduced.
*   **Cleaner History**: Commits are focused on logic changes rather than formatting fixes.

### Negative
*   **Setup Overhead**: New contributors must install pre-commit (`uv run pre-commit install`) to benefit from the checks locally.
*   **Commit Latency**: Commits take slightly longer (seconds) to run the checks.
