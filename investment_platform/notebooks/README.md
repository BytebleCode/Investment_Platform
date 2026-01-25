# Investment Platform Jupyter Notebooks

## Overview

This directory contains Jupyter notebooks for interactive portfolio analysis and strategy backtesting.

## Notebooks

### 1. portfolio_analysis.ipynb

Interactive portfolio analysis including:
- Current holdings overview
- Performance metrics
- Gain/loss visualization
- Sector allocation analysis

### 2. strategy_backtesting.ipynb

Strategy testing and comparison:
- Historical performance simulation
- Strategy comparison charts
- Risk metrics (Sharpe ratio, max drawdown)
- Parameter sensitivity analysis

## Setup

### Prerequisites

```bash
# Install Jupyter
pip install jupyter ipywidgets

# Enable widgets
jupyter nbextension enable --py widgetsnbextension
```

### Running Notebooks

```bash
# Start Jupyter
cd investment_platform/notebooks
jupyter notebook

# Or use JupyterLab
jupyter lab
```

### API Connection

Notebooks connect to the API running at `http://localhost:5000/api`.
Ensure the server is running before executing notebook cells.

## Usage from JupyterHub

If running on a mainframe with JupyterHub:

1. Upload notebooks to your JupyterHub workspace
2. Update `BASE_URL` if needed
3. Run cells in order

## Creating Custom Analysis

```python
import requests
import pandas as pd

BASE_URL = 'http://localhost:5000/api'

# Get portfolio data
portfolio = requests.get(f'{BASE_URL}/portfolio/settings').json()
holdings = requests.get(f'{BASE_URL}/holdings').json()

# Convert to DataFrame for analysis
df = pd.DataFrame(holdings)

# Your analysis here...
```
