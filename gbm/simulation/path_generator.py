"""Monte Carlo path generator using Geometric Brownian Motion."""

from typing import List, Tuple, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class PathGenerator:
    """Generates multiple Monte Carlo paths using GBM.
    
    Creates independent price paths from a starting price over a forecast
    horizon using Geometric Brownian Motion with drift and volatility.
    
    Parameters
    ----------
    starting_price : float
        Initial price from which all paths start
    mu : float
        Drift coefficient (annualized expected return)
    sigma : float
        Volatility coefficient (annualized)
    forecast_horizon_minutes : int, default=10080
        Forecast horizon in minutes (default: 1 week = 7*24*60)
    num_paths : int, default=500
        Number of independent paths to generate
    seed : int, optional
        Random seed for reproducibility
    """
    
    def __init__(
        self,
        starting_price: float,
        mu: float,
        sigma: float,
        forecast_horizon_minutes: int = 10080,  # 1 week
        num_paths: int = 500,
        seed: Optional[int] = None,
    ):
        self.starting_price = starting_price
        self.mu = mu
        self.sigma = sigma
        self.forecast_horizon_minutes = forecast_horizon_minutes
        self.num_paths = num_paths
        self.seed = seed
        
        # Time step: 1 minute
        self.dt = 1.0 / (252 * 6.5 * 60)  # 1 minute in years (trading minutes per year)
        
        # Number of steps
        self.num_steps = forecast_horizon_minutes
    
    def generate_paths(
        self,
        start_time: datetime,
    ) -> Tuple[List[np.ndarray], pd.DatetimeIndex]:
        """Generate multiple Monte Carlo paths.
        
        Parameters
        ----------
        start_time : datetime
            Starting timestamp for the paths
        
        Returns
        -------
        tuple
            (list of path arrays, datetime index)
            Each path is a numpy array of prices at 1-minute intervals
        """
        if self.seed is not None:
            np.random.seed(self.seed)
        
        # Create time index (1-minute intervals)
        time_index = pd.date_range(
            start=start_time,
            periods=self.num_steps + 1,
            freq="1min",
        )
        
        paths = []
        
        for _ in range(self.num_paths):
            path = self._generate_single_path()
            paths.append(path)
        
        return paths, time_index
    
    def _generate_single_path(self) -> np.ndarray:
        """Generate a single GBM path.
        
        Returns
        -------
        np.ndarray
            Array of prices at each time step
        """
        # Initialize path with starting price
        path = np.zeros(self.num_steps + 1)
        path[0] = self.starting_price
        
        # Generate random increments
        # dW = sqrt(dt) * N(0, 1)
        dW = np.random.normal(0, 1, self.num_steps) * np.sqrt(self.dt)
        
        # Generate path using GBM formula
        # S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*dW)
        for i in range(1, self.num_steps + 1):
            drift_term = (self.mu - 0.5 * self.sigma ** 2) * self.dt
            diffusion_term = self.sigma * dW[i - 1]
            path[i] = path[i - 1] * np.exp(drift_term + diffusion_term)
        
        return path
    
    def generate_paths_with_time(
        self,
        start_time: datetime,
    ) -> Tuple[List[Tuple[np.ndarray, pd.DatetimeIndex]], pd.DatetimeIndex]:
        """Generate paths with associated time indices.
        
        Parameters
        ----------
        start_time : datetime
            Starting timestamp
        
        Returns
        -------
        tuple
            (list of (path, time_index) tuples, overall time index)
        """
        paths, time_index = self.generate_paths(start_time)
        
        # Each path gets its own time index (they're all the same)
        paths_with_time = [(path, time_index) for path in paths]
        
        return paths_with_time, time_index

