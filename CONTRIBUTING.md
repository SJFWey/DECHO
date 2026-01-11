# Contributing to DECHO

Thank you for your interest in contributing to DECHO! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

Please be respectful and considerate in all interactions. We aim to maintain a welcoming and inclusive community.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/decho.git
   cd decho
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/decho.git
   ```

## Development Setup

### Prerequisites

- Python 3.13+
- Node.js 18+
- uv (recommended) or pip

### Backend Setup

```bash
# Create virtual environment and install dependencies
uv sync

# Install development dependencies
uv sync --dev

# Download required spaCy models
uv run python -m spacy download en_core_web_md
```

### Frontend Setup

```bash
cd web
npm install
npx prisma generate
npx prisma db push
```

### Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-language` - New features
- `fix/audio-playback-issue` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/cleanup-api` - Code refactoring

### Commit Messages

Follow conventional commits format:

```
type(scope): description

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(asr): add support for whisper model
fix(frontend): resolve audio player memory leak
docs: update installation instructions
```

## Code Style

### Python

We use the following tools for Python code quality:

```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

**Guidelines:**
- Follow PEP 8 style guide
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small

### TypeScript/React

```bash
cd web
npm run lint
```

**Guidelines:**
- Use TypeScript for all new code
- Follow React best practices
- Use functional components with hooks
- Keep components small and reusable

## Testing

### Backend Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend --cov=server

# Run specific test file
uv run pytest tests/test_api.py
```

### Frontend Tests

```bash
cd web
npm test
```

### Writing Tests

- Write tests for new features
- Update tests when modifying existing functionality
- Aim for meaningful test coverage

## Submitting Changes

### Pull Request Process

1. **Update your fork** with latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your branch**:
   ```bash
   git push origin feature/your-feature
   ```

3. **Create a Pull Request** on GitHub

4. **Fill out the PR template** with:
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)

### PR Checklist

- [ ] Code follows the project style guidelines
- [ ] Self-review performed
- [ ] Documentation updated (if needed)
- [ ] Tests added/updated
- [ ] All tests pass locally
- [ ] No merge conflicts

### Review Process

- PRs require at least one approval before merging
- Address review comments promptly
- Keep PRs focused and reasonably sized

## Questions?

Feel free to open an issue for any questions or discussions about contributing.

---

Thank you for contributing to DECHO! 🎉
