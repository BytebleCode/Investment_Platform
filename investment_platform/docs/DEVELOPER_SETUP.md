# Investment Platform Developer Setup Guide

## Overview

This guide helps developers set up a local development environment for the Investment Platform.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [Code Style](#code-style)
7. [Architecture](#architecture)
8. [Contributing](#contributing)

---

## Prerequisites

### Required Software

- **Python 3.9 - 3.13** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/)
- **pip** - Included with Python
- **virtualenv** - `pip install virtualenv`

### Optional Software

- **DB2 Express** - For testing with real DB2 (otherwise SQLite is used)
- **VS Code** - Recommended IDE with Python extension
- **Postman** - For API testing

### Verify Installation

```bash
python --version   # Should be 3.9 - 3.13
pip --version
git --version
```

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Live_Trading_Platform_Mainframe/investment_platform
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env file with your settings
# For development, defaults should work
```

### 5. Initialize Database

```bash
# Create database tables and initialize with default data
python scripts/init_database.py

# Optionally fetch market data from Yahoo Finance
python scripts/init_database.py --with-market-data
```

### 6. Run Development Server

```bash
python run.py
```

### 7. Access the Application

- **Dashboard:** http://localhost:5000/dashboard/
- **API:** http://localhost:5000/api/
- **Health Check:** http://localhost:5000/api/health

---

## Project Structure

```
investment_platform/
├── app/                        # Flask application
│   ├── __init__.py            # App factory
│   ├── config.py              # Configuration classes
│   ├── logging_config.py      # Logging setup
│   ├── security.py            # Security utilities
│   │
│   ├── api/                   # REST API endpoints
│   │   ├── __init__.py
│   │   ├── portfolio_routes.py
│   │   ├── holdings_routes.py
│   │   ├── trades_routes.py
│   │   ├── strategy_routes.py
│   │   ├── market_data_routes.py
│   │   ├── trading_routes.py
│   │   └── health_routes.py
│   │
│   ├── models/                # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── portfolio.py
│   │   ├── holdings.py
│   │   ├── trades.py
│   │   ├── strategy.py
│   │   ├── market_data.py
│   │   └── market_metadata.py
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── market_data_service.py
│   │   ├── portfolio_service.py
│   │   ├── price_generator.py
│   │   └── trading_engine.py
│   │
│   ├── data/                  # Static data definitions
│   │   ├── __init__.py
│   │   ├── stock_universe.py
│   │   └── strategies.py
│   │
│   └── validation/            # Input validation
│       ├── __init__.py
│       └── schemas.py
│
├── dashboard/                  # Dash application
│   ├── __init__.py
│   ├── app.py                 # Dash app factory
│   │
│   ├── layouts/               # UI layouts
│   │   ├── __init__.py
│   │   ├── main_layout.py
│   │   └── components/        # UI components
│   │       ├── header.py
│   │       ├── portfolio_summary.py
│   │       ├── portfolio_chart.py
│   │       ├── holdings_table.py
│   │       ├── allocation_pie.py
│   │       ├── strategy_selector.py
│   │       ├── strategy_modal.py
│   │       └── trade_history.py
│   │
│   └── callbacks/             # Dash callbacks
│       ├── __init__.py
│       ├── data_callbacks.py
│       ├── trading_callbacks.py
│       ├── chart_callbacks.py
│       └── strategy_callbacks.py
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── test_models.py
│   ├── test_api.py
│   ├── test_trading_engine.py
│   ├── test_price_generator.py
│   ├── test_portfolio_service.py
│   ├── test_market_data_service.py
│   ├── test_data.py
│   └── test_e2e.py
│
├── migrations/                 # Alembic migrations
│   └── versions/
│
├── scripts/                    # Utility scripts
│   ├── migrate_sqlite_to_db2.py
│   └── verify_migration.py
│
├── docs/                       # Documentation
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── USER_GUIDE.md
│   └── DEVELOPER_SETUP.md
│
├── notebooks/                  # Jupyter notebooks
│
├── run.py                      # Development entry point
├── wsgi.py                     # Production entry point
├── gunicorn.conf.py           # Gunicorn configuration
├── uwsgi.ini                   # uWSGI configuration
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
├── .env.template              # Environment template
└── production.env.template    # Production env template
```

---

## Development Workflow

### Running the Application

```bash
# Development mode (with auto-reload)
python run.py

# With specific port
PORT=8000 python run.py

# Debug mode
FLASK_DEBUG=1 python run.py
```

### Making Changes

1. **Create a branch:**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes**

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

4. **Check code style:**
   ```bash
   flake8 app/ dashboard/
   ```

5. **Commit changes:**
   ```bash
   git add .
   git commit -m "Add my new feature"
   ```

### Database Changes

When modifying models:

1. Make changes to models in `app/models/`

2. Re-initialize database (development only):
   ```bash
   # WARNING: This drops existing data
   python scripts/init_database.py --drop-existing
   ```

3. For production, manually alter tables or use a migration tool

### Adding New API Endpoints

1. Create route file in `app/api/` (or add to existing)

2. Define resource class:
   ```python
   from flask_restful import Resource

   class MyResource(Resource):
       def get(self):
           return {'message': 'Hello'}
   ```

3. Register in `app/api/__init__.py`:
   ```python
   api.add_resource(MyResource, '/my-endpoint')
   ```

4. Add validation schema in `app/validation/schemas.py`

5. Add tests in `tests/test_api.py`

### Adding Dashboard Components

1. Create component in `dashboard/layouts/components/`:
   ```python
   from dash import html
   import dash_mantine_components as dmc

   def create_my_component():
       return dmc.Card([
           dmc.Text("My Component")
       ])
   ```

2. Import in `dashboard/layouts/components/__init__.py`

3. Add to layout in `dashboard/layouts/main_layout.py`

4. Add callbacks in `dashboard/callbacks/` if needed

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::TestPortfolioEndpoints::test_get_portfolio_settings -v

# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration
```

### Test Markers

```python
# Mark a test
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_api():
    pass

@pytest.mark.e2e
def test_full_flow():
    pass
```

### Writing Tests

```python
# tests/test_my_feature.py

import pytest
from app.services.my_service import MyService

class TestMyFeature:
    """Tests for my feature."""

    def test_basic_functionality(self, db_session):
        """Test that basic functionality works."""
        service = MyService()
        result = service.do_something()
        assert result is not None

    def test_edge_case(self, db_session):
        """Test edge case handling."""
        service = MyService()
        with pytest.raises(ValueError):
            service.do_something_invalid()
```

### Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `app` - Flask application
- `client` - Test client
- `db_session` - Database session with cleanup
- `sample_portfolio` - Sample portfolio data
- `sample_holdings` - Sample holdings data
- `sample_trades` - Sample trade history
- `current_prices` - Mock current prices

---

## Code Style

### Python Style Guide

Follow PEP 8 with these additions:
- Max line length: 100 characters
- Use type hints for function signatures
- Use docstrings for all public functions

### Linting

```bash
# Check style
flake8 app/ dashboard/ --max-line-length=100

# Auto-format
black app/ dashboard/ --line-length=100
```

### Example Code Style

```python
"""
Module docstring explaining purpose.
"""
from typing import Optional, List, Dict
from decimal import Decimal


def calculate_value(
    quantity: Decimal,
    price: Decimal,
    include_fees: bool = False
) -> Decimal:
    """
    Calculate total value of a position.

    Args:
        quantity: Number of shares
        price: Price per share
        include_fees: Whether to subtract trading fees

    Returns:
        Total value as Decimal

    Raises:
        ValueError: If quantity or price is negative
    """
    if quantity < 0 or price < 0:
        raise ValueError("Quantity and price must be positive")

    value = quantity * price

    if include_fees:
        value -= value * Decimal('0.001')

    return value
```

---

## Architecture

### Application Layers

```
┌─────────────────────────────────────────┐
│           Dashboard (Dash/Plotly)        │
├─────────────────────────────────────────┤
│              REST API (Flask)            │
├─────────────────────────────────────────┤
│         Services (Business Logic)        │
├─────────────────────────────────────────┤
│          Models (SQLAlchemy ORM)         │
├─────────────────────────────────────────┤
│        Database (SQLite/DB2)             │
└─────────────────────────────────────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `app/` | Flask REST API |
| `dashboard/` | Dash UI application |
| `models/` | Database models |
| `services/` | Business logic |
| `data/` | Static configuration |
| `validation/` | Input validation |

### Request Flow

1. **Dashboard** → HTTP request → **Flask API**
2. **API Route** → validates input → calls **Service**
3. **Service** → business logic → queries **Model**
4. **Model** → SQLAlchemy → **Database**
5. Response flows back up the chain

---

## Contributing

### Before Submitting

- [ ] All tests pass
- [ ] Code follows style guide
- [ ] New code has tests
- [ ] Documentation updated
- [ ] No debug code left in

### Commit Messages

Use conventional commits:

```
feat: add new trading feature
fix: correct portfolio calculation
docs: update API reference
test: add tests for trading engine
refactor: simplify price generator
```

### Pull Request Process

1. Create feature branch
2. Make changes
3. Run tests
4. Submit PR with description
5. Address review feedback
6. Merge when approved

---

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure you're in the right directory
cd investment_platform

# Ensure venv is activated
source venv/bin/activate  # or venv\Scripts\activate
```

**Database errors:**
```bash
# Delete SQLite database and start fresh
rm investment_platform.db
python run.py
```

**Port already in use:**
```bash
# Use a different port
PORT=8080 python run.py
```

### Getting Help

1. Check existing documentation
2. Search existing issues
3. Ask in team chat
4. Create an issue with:
   - What you expected
   - What happened
   - Steps to reproduce
   - Error messages

---

## Useful Commands

```bash
# Start development server
python run.py

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=app --cov-report=html

# Check code style
flake8 app/ dashboard/

# Initialize database
python scripts/init_database.py

# Fetch market data
python scripts/fetch_yahoo_data.py --days 30

# Check cache status
python scripts/fetch_yahoo_data.py --status

# Start Python shell with app context
flask shell

# View routes
flask routes
```

Happy coding! 🚀
