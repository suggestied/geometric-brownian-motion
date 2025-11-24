"""Multi-timeframe data manager for fetching and storing OHLC data."""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pandas as pd
from gbm.data.alpaca_client import AlpacaClient
from gbm.data.market_calendar import MarketCalendar


class MultiTimeframeManager:
    """Manages historical and live data across multiple timeframes.
    
    Fetches and stores OHLC data for:
    - Higher Time Frames (HTF): daily, 4h, 1h
    - Lower Time Frames (LTF): 15m, 5m, 1m
    
    Parameters
    ----------
    alpaca_client : AlpacaClient
        Alpaca API client instance
    symbol : str
        Ticker symbol (e.g., "NQ", "QQQ")
    """
    
    TIMEFRAMES = ["1d", "4h", "1h", "15m", "5m", "1m"]
    HTF_TIMEFRAMES = ["1d", "4h", "1h"]
    LTF_TIMEFRAMES = ["15m", "5m", "1m"]
    
    def __init__(self, alpaca_client: AlpacaClient, symbol: str):
        self.client = alpaca_client
        self.symbol = symbol
        self.calendar = MarketCalendar()
        
        # Store data for each timeframe
        self.data: Dict[str, pd.DataFrame] = {}
        
        # Cache for latest bars
        self.latest_bars: Dict[str, Optional[Dict]] = {}
    
    def fetch_historical_data(
        self,
        start: datetime,
        end: Optional[datetime] = None,
        history_days: int = 30,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for all timeframes.
        
        Parameters
        ----------
        start : datetime
            Start time for data fetch
        end : datetime, optional
            End time. If None, uses current time.
        history_days : int, default=30
            Number of days of history to fetch (used if start is None)
        
        Returns
        -------
        dict
            Dictionary mapping timeframe strings to DataFrames
        """
        if end is None:
            end = datetime.now()
        
        if start is None:
            start = end - timedelta(days=history_days)
        
        for timeframe in self.TIMEFRAMES:
            try:
                # Calculate appropriate lookback period for each timeframe
                lookback_days = self._get_lookback_days(timeframe, history_days)
                timeframe_start = end - timedelta(days=lookback_days)
                
                df = self.client.fetch_bars(
                    self.symbol,
                    timeframe,
                    timeframe_start,
                    end,
                )
                
                self.data[timeframe] = df
                
            except Exception as e:
                print(f"Warning: Could not fetch {timeframe} data: {e}")
                self.data[timeframe] = pd.DataFrame()
        
        return self.data
    
    def _get_lookback_days(self, timeframe: str, base_days: int) -> int:
        """Calculate appropriate lookback period for a timeframe.
        
        Parameters
        ----------
        timeframe : str
            Timeframe string
        base_days : int
            Base number of days
        
        Returns
        -------
        int
            Number of days to look back
        """
        # For higher timeframes, we need more history to get meaningful data
        multipliers = {
            "1d": 1,
            "4h": 1,
            "1h": 1,
            "15m": 1,
            "5m": 1,
            "1m": 1,
        }
        return int(base_days * multipliers.get(timeframe, 1))
    
    def update_latest_bars(self) -> Dict[str, Optional[Dict]]:
        """Fetch the latest bar for each timeframe.
        
        Returns
        -------
        dict
            Dictionary mapping timeframe to latest bar data
        """
        for timeframe in self.TIMEFRAMES:
            try:
                bar = self.client.get_latest_bar(self.symbol, timeframe)
                self.latest_bars[timeframe] = bar
                
                # If we have data and got a new bar, append it
                if bar and timeframe in self.data and not self.data[timeframe].empty:
                    bar_timestamp = bar["timestamp"]
                    if isinstance(bar_timestamp, str):
                        bar_timestamp = pd.to_datetime(bar_timestamp)
                    
                    # Check if this is a new bar (not already in data)
                    if bar_timestamp not in self.data[timeframe].index:
                        new_row = pd.DataFrame({
                            "open": [bar["open"]],
                            "high": [bar["high"]],
                            "low": [bar["low"]],
                            "close": [bar["close"]],
                            "volume": [bar["volume"]],
                        }, index=[bar_timestamp])
                        self.data[timeframe] = pd.concat([self.data[timeframe], new_row])
                        self.data[timeframe].sort_index(inplace=True)
                
            except Exception as e:
                print(f"Warning: Could not update {timeframe} bar: {e}")
                self.latest_bars[timeframe] = None
        
        return self.latest_bars
    
    def get_latest_close(self, timeframe: str = "1m") -> Optional[float]:
        """Get the latest close price for a timeframe.
        
        Parameters
        ----------
        timeframe : str, default="1m"
            Timeframe to get close price from
        
        Returns
        -------
        float, optional
            Latest close price, or None if not available
        """
        if timeframe in self.latest_bars and self.latest_bars[timeframe]:
            return self.latest_bars[timeframe]["close"]
        
        if timeframe in self.data and not self.data[timeframe].empty:
            return float(self.data[timeframe]["close"].iloc[-1])
        
        return None
    
    def get_htf_data(self) -> Dict[str, pd.DataFrame]:
        """Get all higher timeframe data.
        
        Returns
        -------
        dict
            Dictionary of HTF DataFrames
        """
        return {tf: self.data.get(tf, pd.DataFrame()) for tf in self.HTF_TIMEFRAMES}
    
    def get_ltf_data(self) -> Dict[str, pd.DataFrame]:
        """Get all lower timeframe data.
        
        Returns
        -------
        dict
            Dictionary of LTF DataFrames
        """
        return {tf: self.data.get(tf, pd.DataFrame()) for tf in self.LTF_TIMEFRAMES}
    
    def calculate_htf_parameters(self) -> Dict[str, Dict[str, float]]:
        """Calculate drift and volatility from HTF data.
        
        Returns
        -------
        dict
            Dictionary mapping timeframe to dict with 'mu' and 'sigma' keys
        """
        params = {}
        
        for timeframe in self.HTF_TIMEFRAMES:
            if timeframe not in self.data or self.data[timeframe].empty:
                continue
            
            df = self.data[timeframe]
            if len(df) < 2:
                continue
            
            # Calculate returns
            returns = df["close"].pct_change().dropna()
            
            if len(returns) == 0:
                continue
            
            # Annualize based on timeframe
            periods_per_year = self._get_periods_per_year(timeframe)
            
            mu = returns.mean() * periods_per_year
            sigma = returns.std() * (periods_per_year ** 0.5)
            
            params[timeframe] = {
                "mu": float(mu),
                "sigma": float(sigma),
            }
        
        return params
    
    def _get_periods_per_year(self, timeframe: str) -> float:
        """Get number of periods per year for a timeframe.
        
        Parameters
        ----------
        timeframe : str
            Timeframe string
        
        Returns
        -------
        float
            Number of periods per year
        """
        # Trading days per year ≈ 252
        # Trading hours per day ≈ 6.5 (9:30 AM - 4:00 PM ET)
        trading_hours_per_year = 252 * 6.5
        
        periods = {
            "1d": 252,
            "4h": trading_hours_per_year / 4,
            "1h": trading_hours_per_year,
            "15m": trading_hours_per_year * 4,
            "5m": trading_hours_per_year * 12,
            "1m": trading_hours_per_year * 60,
        }
        
        return periods.get(timeframe, 252)

