# Geometric Brownian Motion Stock Price Simulator

A Python package for forecasting stock price movements using the Geometric Brownian Motion (GBM) stochastic calculus model.

## Overview

This package uses the Geometric Brownian Motion model to simulate possible paths of stock prices in discrete time. The model dynamically fetches stock prices from Yahoo Finance and calculates forecasted price movements based on historical data.

The path of the stock can vary based on the seed used from the NumPy library. Different seed sequences have different fixed random blocks of data, so when you change the seed value, the path of the stock price changes.

## Features

- Fetch historical stock data from Yahoo Finance
- Calculate drift (mu) and volatility (sigma) from historical returns
- Simulate future stock prices using Geometric Brownian Motion
- Generate visualizations of historical and forecasted prices
- Command-line interface for easy usage
- Comprehensive test suite
- **Docker support for easy setup without installing dependencies**

## Quick Start with Docker (Recommended)

The easiest way to run this without installing Python dependencies:

### Option 1: Use the run script (Easiest!)

```bash
# Run with defaults (MSFT stock, saves to output/forecast.png)
./run.sh

# Run with custom stock ticker
./run.sh AAPL

# Run with custom stock and output file
./run.sh AMZN output/amzn_forecast.png
```

The script will automatically build the Docker image if needed and save the chart to the `output/` directory.

### Option 2: Manual Docker commands

```bash
# Build the image (first time only)
docker build -t gbm-simulator .

# Run simulation
docker run --rm -v $(pwd)/output:/app/output gbm-simulator \
  python -m gbm.cli MSFT --output /app/output/forecast.png --no-plot

# With custom parameters
docker run --rm -v $(pwd)/output:/app/output gbm-simulator \
  python -m gbm.cli AMZN --history-period 200d --forecast-period 252 --seed 42 \
  --output /app/output/amzn_forecast.png --no-plot
```

### View the Chart

After running, the chart will be saved in the `./output/` directory. Open it with:

```bash
# macOS
open output/forecast.png

# Linux
xdg-open output/forecast.png

# Windows
start output/forecast.png
```

## Installation

### Using pip

```bash
pip install -r requirements.txt
```

### Development Installation

For development with testing and linting tools:

```bash
pip install -r requirements.txt
pip install pytest pytest-cov black flake8
```

## Usage

### Quick Docker Usage (No Installation Required)

```bash
# Create output directory
mkdir -p output

# Run simulation and save chart
docker run --rm -v $(pwd)/output:/app/output gbm-simulator \
  python -m gbm.cli AAPL --output /app/output/aapl_forecast.png --no-plot

# Open the chart
open output/aapl_forecast.png  # macOS
# or
xdg-open output/aapl_forecast.png  # Linux
```

### Command-Line Interface

The easiest way to use the package is through the command-line interface:

```bash
# Basic usage with defaults
python -m gbm.cli MSFT

# Custom parameters
python -m gbm.cli AMZN --history-period 100d --forecast-period 252 --seed 10

# Save plot to file without displaying
python -m gbm.cli AAPL --output forecast.png --no-plot

# Full example
python -m gbm.cli MSFT --history-period 504d --forecast-period 252 --seed 10 --output msft_forecast.png
```

### Python API

You can also use the package programmatically:

```python
from gbm import GBM

# Create GBM instance
gbm = GBM(
    stock_ticker='MSFT',
    history_period='504d',
    forecast_period=252,
    seed=10
)

# Run complete simulation pipeline
gbm.run(show_plot=True, output_path='forecast.png')

# Or use individual methods
gbm.fetch_prices()
gbm.calculate_mu_sigma()
gbm.brownian_motion()
gbm.geometric_brownian_motion()
gbm.plot(output_path='forecast.png', show_plot=True)

# Access results
print(f"Initial price: ${gbm.So:.2f}")
print(f"Final forecasted price: ${gbm.S[-1]:.2f}")
print(f"Annualized return (mu): {gbm.mu:.4f}")
print(f"Annualized volatility (sigma): {gbm.sigma:.4f}")

# Get forecasted prices and x-axis values
forecasted_prices, x_axis = gbm.geometric_brownian_motion()
```

## Parameters

### GBM Class Parameters

- **stock_ticker** (str): Stock ticker symbol (e.g., 'MSFT', 'AMZN', 'AAPL')
- **history_period** (str, default='100d'): Time period to look back for historical data
  - Examples: '100d' (100 days), '1y' (1 year), '6mo' (6 months)
- **forecast_period** (int, default=252): Number of trading days to forecast
- **seed** (int, default=20): Random seed for NumPy pseudo-random number generator

### GBM Model Parameters

- **So**: Initial stock price (last trading day price)
- **dt**: Time increment - daily in this case
- **T**: Length of the prediction time horizon (same unit with dt, days)
- **N**: Number of time points in the prediction time horizon → T/dt
- **t**: Array for time points in the prediction time horizon [1, 2, 3, .., N]
- **mu**: Mean of historical daily returns (drift coefficient), annualized
- **sigma**: Standard deviation of historical daily returns (diffusion coefficient), annualized
- **b**: Array for Brownian increments
- **W**: Array for Brownian path

## Project Structure

```
gbm-simulator/
├── gbm/
│   ├── __init__.py      # Package initialization
│   ├── model.py         # GBM model implementation
│   └── cli.py           # Command-line interface
├── tests/
│   ├── __init__.py
│   └── test_gbm.py      # Test suite
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project configuration
├── .gitignore          # Git ignore rules
├── .github/
│   └── workflows/
│       └── ci.yml       # GitHub Actions CI/CD
└── README.md           # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gbm --cov-report=html

# Run specific test file
pytest tests/test_gbm.py
```

### Code Formatting

```bash
# Format code with black
black gbm/ tests/

# Check formatting
black --check gbm/ tests/
```

### Linting

```bash
# Run flake8
flake8 gbm/ tests/
```

## CI/CD

The project includes GitHub Actions workflows for continuous integration:

- **Test Suite**: Runs on multiple Python versions (3.8, 3.9, 3.10, 3.11) and operating systems
- **Linting**: Checks code formatting and style
- **Coverage**: Tracks test coverage

## Sample Output

![GBM Plot](/output/forecast.png)

## Mathematical Background

The Geometric Brownian Motion model is described by the stochastic differential equation:

```
dS(t) = μS(t)dt + σS(t)dW(t)
```

Where:
- S(t) is the stock price at time t
- μ is the drift coefficient (expected return)
- σ is the volatility coefficient
- dW(t) is a Wiener process (Brownian motion)

The solution to this equation is:

```
S(t) = S(0) * exp((μ - 0.5σ²)t + σW(t))
```

This implementation uses discrete-time approximation with daily time steps.

## Dependencies

- **numpy**: Numerical computations
- **yfinance**: Fetching stock data from Yahoo Finance
- **matplotlib**: Plotting and visualization
- **pandas**: Data manipulation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Any contribution to improve this model is appreciated.

## License

MIT License

## Acknowledgments

- Original implementation by harishangaran
- Uses Yahoo Finance API via yfinance library
