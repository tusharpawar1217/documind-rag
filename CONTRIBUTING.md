# Contributing to DocuMind RAG System

Thank you for your interest in contributing to DocuMind! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/documind-rag.git
   cd documind-rag
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original/documind-rag.git
   ```

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Google Gemini API key

### Quick Setup
```bash
# Run setup script
.\setup.ps1

# Or manual setup:
# 1. Copy .env.example to .env and add your API key
# 2. Start infrastructure
docker-compose up -d

# 3. Setup backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 4. Setup frontend
cd ../frontend
npm install
```

## Making Changes

### Branch Naming
Use descriptive branch names:
- `feature/add-multi-language-support`
- `fix/pdf-parsing-error`
- `docs/update-api-documentation`
- `test/add-integration-tests`

### Commit Messages
Follow conventional commits format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

Example:
```
feat(search): add support for multi-language queries

- Added language detection
- Updated embedding generation to handle multiple languages
- Added tests for language support

Closes #123
```

## Testing

### Running Tests
```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/unit/test_pdf_parser.py

# Specific test
pytest tests/unit/test_pdf_parser.py::test_validate_pdf_valid_file
```

### Writing Tests
- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test component interactions
- **Property tests**: Test universal properties

Example unit test:
```python
def test_cosine_similarity_identical_vectors():
    """Test that identical vectors have similarity of 1.0."""
    vec = np.array([1.0, 2.0, 3.0])
    similarity = cosine_similarity(vec, vec)
    assert np.isclose(similarity, 1.0)
```

### Test Coverage
- Aim for >80% code coverage
- All new features must include tests
- Bug fixes should include regression tests

## Code Style

### Python
- Follow PEP 8 style guide
- Use type hints for all functions
- Maximum line length: 100 characters
- Use docstrings for all public functions/classes

Format code:
```bash
# Black formatter
black app/

# Ruff linter
ruff check app/

# Type checking
mypy app/
```

Example:
```python
def calculate_score(
    query: str,
    results: List[SearchResult],
    threshold: float = 0.7
) -> float:
    """
    Calculate relevance score for query results.
    
    Args:
        query: User query string
        results: List of search results
        threshold: Minimum score threshold
        
    Returns:
        Combined relevance score
        
    Raises:
        ValueError: If results list is empty
    """
    if not results:
        raise ValueError("Results list cannot be empty")
    
    # Implementation
    return score
```

### TypeScript
- Use ESLint configuration
- Enable strict mode in tsconfig.json
- Use interfaces for data structures
- Prefer functional components with hooks

Format code:
```bash
cd frontend
npm run lint
npm run format
```

### Documentation
- Update README.md for user-facing changes
- Update API_DOCUMENTATION.md for API changes
- Add inline comments for complex logic
- Keep documentation up-to-date

## Submitting Changes

### Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open Pull Request**:
   - Go to GitHub repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in PR template
   - Link related issues

### Pull Request Checklist
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] No merge conflicts
- [ ] PR description is clear and complete

### Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Related Issues
Closes #123

## Screenshots (if applicable)
```

## Reporting Bugs

### Before Reporting
1. Check if bug already reported
2. Verify bug with latest version
3. Collect relevant information

### Bug Report Template
```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Upload document...
2. Query with...
3. See error...

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: Windows 11
- Python: 3.11.5
- Browser: Chrome 120

**Logs**
```
Paste relevant log output
```

**Screenshots**
If applicable
```

## Feature Requests

### Feature Request Template
```markdown
**Problem Statement**
What problem does this solve?

**Proposed Solution**
How should this work?

**Alternatives Considered**
Other approaches you've thought about

**Additional Context**
Any other information
```

## Areas for Contribution

### High Priority
- [ ] Frontend React components
- [ ] Redis caching implementation
- [ ] Prometheus metrics export
- [ ] Kubernetes deployment configs

### Medium Priority
- [ ] Additional language support
- [ ] Advanced table detection models
- [ ] Analytics dashboard
- [ ] Batch processing API

### Good First Issues
Look for issues labeled `good-first-issue`:
- Documentation improvements
- Test coverage expansion
- Code refactoring
- Bug fixes

## Code Review Process

1. **Automated Checks**:
   - Tests must pass
   - Linting must pass
   - Coverage must not decrease

2. **Manual Review**:
   - Code quality review
   - Design review
   - Documentation review

3. **Approval**:
   - At least one approval required
   - All comments addressed
   - CI/CD passes

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

## Questions?

- **Documentation**: Check README.md, DEPLOYMENT.md, API_DOCUMENTATION.md
- **Discussions**: Use GitHub Discussions
- **Issues**: Open an issue on GitHub

Thank you for contributing to DocuMind RAG System! 🎉
