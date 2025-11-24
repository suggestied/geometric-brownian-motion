"""
Geometric Brownian Motion model for stock price simulation.

This module implements the GBM stochastic process to forecast stock prices
based on historical data from Yahoo Finance.
"""

from typing import Tuple, Optional
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd


class GBM:
    """
    Geometric Brownian Motion model for stock price forecasting.
    
    The GBM model uses historical stock data to calculate drift (mu) and
    volatility (sigma) parameters, then simulates future price paths using
    stochastic calculus.
    
    Parameters
    ----------
    stock_ticker : str
        Stock ticker symbol (e.g., 'MSFT', 'AMZN')
    history_period : str, default='100d'
        Time period to look back for historical data (e.g., '100d', '1y')
    forecast_period : int, default=252
        Number of trading days to forecast
    seed : int, default=20
        Random seed for NumPy pseudo-random number generator
    
    Attributes
    ----------
    stock_ticker : str
        Stock ticker symbol
    history_period : str
        Historical data period
    forecast_period : int
        Forecast period in trading days
    seed : int
        Random seed value
    stock_price : pd.DataFrame
        Historical stock price data
    mu : float
        Annualized mean return (drift coefficient)
    sigma : float
        Annualized volatility (diffusion coefficient)
    So : float
        Initial stock price (last trading day price)
    S : list[float]
        Forecasted stock prices
    x_axis : np.ndarray
        X-axis values for plotting forecast
    W : np.ndarray
        Brownian path
    """
    
    def __init__(
        self,
        stock_ticker: str,
        history_period: str = '100d',
        forecast_period: int = 252,
        seed: int = 20
    ):
        self.stock_ticker = stock_ticker
        self.history_period = history_period
        self.forecast_period = forecast_period
        self.seed = seed
        
        # Initialize attributes
        self.stock_price: Optional[pd.DataFrame] = None
        self.mu: Optional[float] = None
        self.sigma: Optional[float] = None
        self.So: Optional[float] = None
        self.S: Optional[list] = None
        self.x_axis: Optional[np.ndarray] = None
        self.W: Optional[np.ndarray] = None
        self.int_of_history_period: Optional[int] = None
        
    def fetch_prices(self) -> Tuple[pd.DataFrame, int]:
        """
        Fetch historical stock prices from Yahoo Finance.
        
        Returns
        -------
        Tuple[pd.DataFrame, int]
            Historical stock price DataFrame and integer representation
            of history period in days
        
        Raises
        ------
        ValueError
            If stock ticker is invalid or data cannot be fetched
        """
        try:
            ticker = yf.Ticker(self.stock_ticker)
            self.stock_price = ticker.history(self.history_period)
            
            if self.stock_price.empty:
                raise ValueError(
                    f"No data found for ticker '{self.stock_ticker}'. "
                    "Please check the ticker symbol."
                )
            
            # Extract integer days from history_period string (e.g., '100d' -> 100)
            if 'd' in self.history_period:
                self.int_of_history_period = int(self.history_period.split('d')[0])
            elif 'y' in self.history_period:
                # Approximate: 1 year ≈ 252 trading days
                years = float(self.history_period.split('y')[0])
                self.int_of_history_period = int(years * 252)
            else:
                # Default to actual number of trading days in the data
                self.int_of_history_period = len(self.stock_price)
            
            return self.stock_price, self.int_of_history_period
            
        except Exception as e:
            raise ValueError(
                f"Error fetching data for '{self.stock_ticker}': {str(e)}"
            ) from e
    
    def calculate_mu_sigma(self) -> Tuple[pd.DataFrame, float, float]:
        """
        Calculate annualized mean return (mu) and volatility (sigma).
        
        Returns
        -------
        Tuple[pd.DataFrame, float, float]
            Stock price DataFrame with daily returns, mu, and sigma
        
        Raises
        ------
        ValueError
            If stock price data is not available
        """
        if self.stock_price is None:
            raise ValueError(
                "Stock price data not available. Call fetch_prices() first."
            )
        
        # Calculate daily returns
        self.stock_price['Daily return'] = self.stock_price['Close'].pct_change(1)
        
        # Calculate annualized mean return (252 trading days per year)
        self.mu = self.stock_price['Daily return'].mean() * 252
        
        # Calculate annualized volatility
        self.sigma = self.stock_price['Daily return'].std() * np.sqrt(252)
        
        return self.stock_price, self.mu, self.sigma
    
    def brownian_motion(self) -> np.ndarray:
        """
        Generate Brownian motion path.
        
        Returns
        -------
        np.ndarray
            Cumulative Brownian path (W)
        """
        np.random.seed(self.seed)
        
        # Time step
        dt = 1 / self.forecast_period
        
        # Brownian increments
        b = np.random.normal(0, 1, int(self.forecast_period)) * np.sqrt(dt)
        
        # Brownian path (cumulative sum)
        self.W = np.cumsum(b)
        
        return self.W
    
    def geometric_brownian_motion(self) -> Tuple[list, np.ndarray]:
        """
        Calculate forecasted stock prices using Geometric Brownian Motion.
        
        The GBM formula: S(t) = S(0) * exp((mu - 0.5*sigma²)*t + sigma*W(t))
        
        Returns
        -------
        Tuple[list, np.ndarray]
            Forecasted stock prices (S) and x-axis values for plotting
        
        Raises
        ------
        ValueError
            If required attributes are not calculated
        """
        if self.stock_price is None:
            raise ValueError(
                "Stock price data not available. Call fetch_prices() first."
            )
        if self.mu is None or self.sigma is None:
            raise ValueError(
                "Mu and sigma not calculated. Call calculate_mu_sigma() first."
            )
        if self.W is None:
            raise ValueError(
                "Brownian motion not calculated. Call brownian_motion() first."
            )
        
        # Initial stock price (last trading day price)
        self.So = float(self.stock_price['Close'].iloc[-1])
        
        # Get actual data length for proper x-axis alignment
        actual_data_length = len(self.stock_price['Close'])
        
        # Time axis for GBM calculation
        time_axis = np.linspace(0, 1, self.forecast_period + 1)
        
        # X-axis for plotting forecast (starts from end of historical data)
        self.x_axis = np.linspace(
            actual_data_length,
            self.forecast_period + actual_data_length,
            self.forecast_period + 1
        )
        
        # Calculate forecasted prices using GBM formula
        self.S = [self.So]
        for i in range(1, int(self.forecast_period + 1)):
            drift = (self.mu - 0.5 * self.sigma**2) * time_axis[i]
            diffusion = self.sigma * self.W[i - 1]
            S_temp = self.So * np.exp(drift + diffusion)
            self.S.append(S_temp)
        
        return self.S, self.x_axis
    
    def plot(
        self,
        output_path: Optional[str] = None,
        show_plot: bool = True
    ) -> None:
        """
        Plot historical and forecasted stock prices.
        
        Parameters
        ----------
        output_path : str, optional
            Path to save the plot. If None, plot is not saved.
        show_plot : bool, default=True
            Whether to display the plot
        
        Raises
        ------
        ValueError
            If forecasted prices are not available
        """
        if self.S is None or self.x_axis is None:
            raise ValueError(
                "Forecasted prices not available. "
                "Call geometric_brownian_motion() first."
            )
        if self.stock_price is None:
            raise ValueError(
                "Stock price data not available. Call fetch_prices() first."
            )
        
        # X-axis for historical prices (use actual data length, not calculated period)
        actual_data_length = len(self.stock_price['Close'])
        pt = np.linspace(0, actual_data_length, actual_data_length)
        
        plt.figure(figsize=(12, 8), dpi=300)
        plt.plot(pt, self.stock_price['Close'], label='Actual')
        plt.plot(self.x_axis, self.S, label='Forecast')
        plt.legend()
        plt.ylabel('Stock Price, $')
        plt.xlabel('Trading Days')
        plt.title(
            f'Geometric Brownian Motion of {self.stock_ticker} '
            f'over next {self.forecast_period} trading days'
        )
        plt.grid(True, alpha=0.3)
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        if show_plot:
            plt.show()
        else:
            plt.close()
    
    def run(self, show_plot: bool = True, output_path: Optional[str] = None) -> None:
        """
        Run the complete GBM simulation pipeline.
        
        This method executes all steps in order:
        1. Fetch historical prices
        2. Calculate mu and sigma
        3. Generate Brownian motion
        4. Calculate forecasted prices
        5. Plot results
        
        Parameters
        ----------
        show_plot : bool, default=True
            Whether to display the plot
        output_path : str, optional
            Path to save the plot
        """
        self.fetch_prices()
        self.calculate_mu_sigma()
        self.brownian_motion()
        self.geometric_brownian_motion()
        self.plot(output_path=output_path, show_plot=show_plot)

