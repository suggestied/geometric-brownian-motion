"""Alpaca Markets API client for fetching NASDAQ futures data."""

import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.exceptions import APIError

# Load .env file if it exists
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Also try loading from current directory
    load_dotenv()


class AlpacaClient:
    """Client for fetching historical and live market data from Alpaca.
    
    Supports NASDAQ futures (NQ) or QQQ ETF as proxy. Handles authentication
    and provides methods for fetching OHLC data across multiple timeframes.
    
    Parameters
    ----------
    api_key : str, optional
        Alpaca API key. If None, reads from ALPACA_API_KEY environment variable.
    api_secret : str, optional
        Alpaca API secret. If None, reads from ALPACA_API_SECRET environment variable.
    use_paper : bool, default=True
        Whether to use paper trading API (default) or live API.
    """
    
    @staticmethod
    def _get_timeframe(timeframe_str: str) -> TimeFrame:
        """Get Alpaca TimeFrame object for a given timeframe string.
        
        Parameters
        ----------
        timeframe_str : str
            Timeframe string (1m, 5m, 15m, 1h, 4h, 1d)
        
        Returns
        -------
        TimeFrame
            Alpaca TimeFrame object
        """
        # Map to standard Alpaca TimeFrame values
        # Note: Alpaca may not support all custom intervals directly
        # We use the closest standard timeframe and will aggregate if needed
        timeframe_map = {
            "1m": TimeFrame.Minute,
            "5m": TimeFrame.Minute,   # Will fetch 1m and aggregate to 5m
            "15m": TimeFrame.Minute,  # Will fetch 1m and aggregate to 15m
            "1h": TimeFrame.Hour,
            "4h": TimeFrame.Hour,     # Will fetch 1h and aggregate to 4h
            "1d": TimeFrame.Day,
        }
        return timeframe_map.get(timeframe_str, TimeFrame.Minute)
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        use_paper: Optional[bool] = None,
        base_url: Optional[str] = None,
    ):
        # Support both ALPACA_* and APCA_* environment variable naming conventions
        self.api_key = (
            api_key 
            or os.getenv("ALPACA_API_KEY", "") 
            or os.getenv("APCA_API_KEY_ID", "")
        )
        self.api_secret = (
            api_secret 
            or os.getenv("ALPACA_API_SECRET", "") 
            or os.getenv("APCA_API_SECRET_KEY", "")
        )
        
        # Get use_paper from .env if not provided
        if use_paper is None:
            use_paper_str = os.getenv("ALPACA_USE_PAPER", "true").lower()
            self.use_paper = use_paper_str in ("true", "1", "yes")
        else:
            self.use_paper = use_paper
        
        # Determine base URL for API endpoint
        # Support both ALPACA_BASE_URL and APCA_API_BASE_URL
        if base_url is None:
            base_url = (
                os.getenv("ALPACA_BASE_URL", "") 
                or os.getenv("APCA_API_BASE_URL", "")
            )
            
            if not base_url:
                # Default to paper or live based on use_paper flag
                if self.use_paper:
                    base_url = "https://paper-api.alpaca.markets"
                else:
                    base_url = "https://api.alpaca.markets"
        
        self.base_url = base_url
        
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca API credentials required. Set ALPACA_API_KEY/APCA_API_KEY_ID and "
                "ALPACA_API_SECRET/APCA_API_SECRET_KEY environment variables or pass them directly."
            )
        
        # Set environment variable for Alpaca SDK (it reads from env)
        # This ensures the SDK uses the correct endpoint
        os.environ["APCA_API_BASE_URL"] = self.base_url
        
        # Create client - the SDK will read base_url from environment
        # Some versions of alpaca-py accept base_url parameter directly
        try:
            # Try with base_url parameter (newer versions)
            self.client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                base_url=self.base_url,
            )
        except TypeError:
            # Fallback: SDK reads from APCA_API_BASE_URL environment variable
            self.client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
            )
    
    def normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker symbol for Alpaca.
        
        Alpaca may not support NQ futures directly. This method handles
        ticker normalization and suggests alternatives.
        
        Parameters
        ----------
        ticker : str
            Ticker symbol (e.g., "NQ", "QQQ")
        
        Returns
        -------
        str
            Normalized ticker symbol
        """
        ticker = ticker.upper().strip()
        
        # If NQ, try NQ=F first, then fallback to QQQ
        if ticker == "NQ":
            # Try NQ=F format (Yahoo Finance futures format)
            # If that doesn't work, we'll use QQQ as proxy
            return "QQQ"  # Use QQQ as proxy for now
        return ticker
    
    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Fetch historical OHLC bars for a symbol.
        
        Parameters
        ----------
        symbol : str
            Ticker symbol
        timeframe : str
            One of: "1m", "5m", "15m", "1h", "4h", "1d"
        start : datetime
            Start time for data fetch
        end : datetime, optional
            End time. If None, uses current time.
        limit : int, optional
            Maximum number of bars to return
        
        Returns
        -------
        pd.DataFrame
            DataFrame with columns: timestamp, open, high, low, close, volume
            Index is datetime.
        
        Raises
        ------
        ValueError
            If timeframe is invalid or symbol not found
        APIError
            If Alpaca API returns an error
        """
        symbol = self.normalize_ticker(symbol)
        
        valid_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        if timeframe not in valid_timeframes:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. "
                f"Must be one of: {valid_timeframes}"
            )
        
        alpaca_timeframe = self._get_timeframe(timeframe)
        
        if end is None:
            end = datetime.now()
        
        # Adjust end time to be at least 15 minutes ago to avoid SIP restriction
        # Free tier can only access SIP data that's 15+ minutes old
        now = datetime.now()
        
        # Normalize timezone for comparison - make both naive
        start_naive = start.replace(tzinfo=None) if start.tzinfo else start
        
        if end:
            end_naive = end.replace(tzinfo=None) if end.tzinfo else end
            # Calculate time difference
            time_diff = (now - end_naive)
            # Check if it's a timedelta and get seconds
            if hasattr(time_diff, 'total_seconds'):
                seconds_diff = time_diff.total_seconds()
            else:
                # Fallback: calculate manually
                seconds_diff = (now - end_naive).days * 86400 + (now - end_naive).seconds
            
            if seconds_diff < 900:  # Less than 15 minutes
                # Data is too recent, adjust to 15 minutes ago
                end = now - timedelta(minutes=15)
                if end < start_naive:
                    # If adjusted end is before start, use start + 1 day
                    end = start_naive + timedelta(days=1)
            else:
                end = end_naive
        else:
            end = now - timedelta(minutes=15)
        
        # Ensure start is also timezone-naive for consistency
        start = start_naive
        
        try:
            # Try with IEX feed first (free tier supports IEX for recent data)
            request_params = {
                "symbol_or_symbols": symbol,
                "timeframe": alpaca_timeframe,
                "start": start,
                "end": end,
            }
            if limit:
                request_params["limit"] = limit
            
            # Try to add feed parameter (IEX is free tier compatible)
            try:
                request = StockBarsRequest(**request_params, feed="iex")
            except TypeError:
                # If feed parameter not supported, use without it
                request = StockBarsRequest(**request_params)
            
            bars = self.client.get_stock_bars(request)
            
            if not bars.data or symbol not in bars.data or not bars.data[symbol]:
                # Try with older data if recent data fails
                end_for_comparison = end.replace(tzinfo=None) if end.tzinfo else end
                time_diff = (now - end_for_comparison)
                if hasattr(time_diff, 'total_seconds') and time_diff.total_seconds() < 3600:
                    # Try going back further
                    older_end = now - timedelta(hours=1)
                    if older_end > start:
                        request_params["end"] = older_end
                        try:
                            request = StockBarsRequest(**request_params, feed="iex")
                        except TypeError:
                            request = StockBarsRequest(**request_params)
                        bars = self.client.get_stock_bars(request)
            
            if not bars.data or symbol not in bars.data or not bars.data[symbol]:
                raise ValueError(f"No data returned for {symbol} from {start} to {end}")
            
            # Convert to DataFrame
            data = []
            for bar in bars.data[symbol]:
                data.append({
                    "timestamp": bar.timestamp,
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume),
                })
            
            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except APIError as e:
            error_msg = str(e)
            # If it's a SIP subscription error, provide helpful message
            if "subscription" in error_msg.lower() or "sip" in error_msg.lower():
                raise ValueError(
                    f"Alpaca free tier limitation: {error_msg}. "
                    f"Try using data that's at least 15 minutes old, or upgrade to a paid plan."
                ) from e
            raise ValueError(f"Alpaca API error for {symbol}: {error_msg}") from e
        except KeyError as e:
            raise ValueError(
                f"Symbol {symbol} not found or not supported. "
                "Try QQQ as a proxy for NASDAQ futures."
            ) from e
    
    def get_latest_bar(self, symbol: str, timeframe: str = "1m") -> Optional[Dict]:
        """Get the most recent bar for a symbol.
        
        Parameters
        ----------
        symbol : str
            Ticker symbol
        timeframe : str, default="1m"
            Timeframe for the bar
        
        Returns
        -------
        dict, optional
            Dictionary with open, high, low, close, volume, timestamp.
            Returns None if no data available.
        """
        symbol = self.normalize_ticker(symbol)
        
        end = datetime.now()
        start = end - timedelta(days=1)  # Look back 1 day to ensure we get data
        
        try:
            df = self.fetch_bars(symbol, timeframe, start, end, limit=1)
            
            if df.empty:
                return None
            
            latest = df.iloc[-1]
            return {
                "timestamp": df.index[-1],
                "open": float(latest["open"]),
                "high": float(latest["high"]),
                "low": float(latest["low"]),
                "close": float(latest["close"]),
                "volume": int(latest["volume"]),
            }
        except Exception:
            return None
    
    def is_market_open(self) -> bool:
        """Check if market is currently open.
        
        Returns
        -------
        bool
            True if market is open, False otherwise
        """
        # Simple check: market hours are 9:30 AM - 4:00 PM ET, Mon-Fri
        # This is a simplified version; can be enhanced with actual market calendar
        now = datetime.now()
        # Note: This doesn't account for timezone or holidays
        # For production, use a proper market calendar
        return now.weekday() < 5  # Monday = 0, Friday = 4

