# Contributing to Personal ATS

Thank you for your interest in contributing!

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis 7+
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/BODAPATI88/personal-ats.git
cd personal-ats

# Create feature branch
git checkout -b feature/your-feature-name

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your local settings
```

## Development Workflow

### 1. Make Changes

```bash
# Create feature branch
git checkout -b feature/descriptive-name

# Make your changes
vim backend/services/scoring_service.py
```

### 2. Test Changes

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_scoring.py::test_quality_score

# Run with coverage
pytest --cov=backend tests/
```

### 3. Code Quality

```bash
# Format code
black backend/

# Lint
flake8 backend/

# Type checking
mypy backend/

# Sort imports
isort backend/
```

### 4. Commit & Push

```bash
git add .
git commit -m "feat: add smart split feature"
git push origin feature/your-feature-name
```

## Code Style

### Python Style Guide

```python
# Use type hints
def calculate_score(candidate_id: int, job_id: int) -> float:
    """Calculate candidate quality score.
    
    Args:
        candidate_id: Candidate identifier
        job_id: Job identifier
        
    Returns:
        Quality score between 0 and 100
    """
    pass

# Use meaningful names
candidate_quality_scores = {}

# Add docstrings
class ScoringService:
    """Service for calculating candidate quality scores."""
    
    def calculate(self, candidate: Candidate) -> float:
        """Calculate score for candidate."""
        pass
```

## Testing Requirements

### Test Coverage
- Aim for > 80% code coverage
- Write tests for new features
- Update tests when changing code

### Test Structure

```python
import pytest
from backend.services.scoring_service import ScoringService

@pytest.fixture
def scoring_service():
    """Provide scoring service instance."""
    return ScoringService()

def test_calculate_score_high_quality(scoring_service):
    """Test score calculation for high quality candidate."""
    score = scoring_service.calculate(candidate_id=1)
    assert score > 75
    assert isinstance(score, float)

def test_calculate_score_invalid_input(scoring_service):
    """Test score calculation with invalid input."""
    with pytest.raises(ValueError):
        scoring_service.calculate(candidate_id=-1)
```

## Commit Message Guidelines

Use conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Testing
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance

### Examples

```
feat(scoring): implement ML-based quality scoring

Add machine learning model for intelligent candidate
quality assessment based on historical hiring data.

Closes #456

---

fix(validation): correct URL validation regex

Fixed regex pattern that was failing on valid URLs
with query parameters.

Closes #123
```

## Pull Request Process

### Before Submitting
1. [ ] Code formatted with black
2. [ ] Linting passes (flake8)
3. [ ] Tests pass (pytest)
4. [ ] Coverage > 80%
5. [ ] Documentation updated
6. [ ] No breaking changes

### PR Template

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How have these changes been tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted
- [ ] Linting passes
- [ ] Coverage maintained

## Related Issues
Closes #123
```

## Documentation

Update relevant documentation:
- README.md for overview changes
- docs/API.md for API changes
- docs/ARCHITECTURE.md for structural changes
- CONTRIBUTING.md for process changes

## Questions?

Feel free to:
- Open an issue
- Comment on PRs
- Ask in discussions

Thank you for contributing!
