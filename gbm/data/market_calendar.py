"""Market calendar utilities for detecting weekly and daily opens."""

from typing import Optional, Tuple
from datetime import datetime, timedelta
import pytz


class MarketCalendar:
    """Utilities for detecting market opens and managing trading calendar.
    
    Handles detection of weekly opens (Monday) and daily opens (09:30 ET)
    for NASDAQ futures trading.
    """
    
    # Market timezone (Eastern Time)
    ET = pytz.timezone("America/New_York")
    
    # Market hours (ET)
    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 30
    MARKET_CLOSE_HOUR = 16
    MARKET_CLOSE_MINUTE = 0
    
    def __init__(self):
        """Initialize market calendar."""
        pass
    
    def get_current_et_time(self) -> datetime:
        """Get current time in Eastern Timezone.
        
        Returns
        -------
        datetime
            Current datetime in ET timezone
        """
        return datetime.now(self.ET)
    
    def get_weekly_open(self, date: Optional[datetime] = None) -> datetime:
        """Get the weekly open (Monday 09:30 ET) for a given date.
        
        If the date is a Monday before market open, returns that Monday.
        Otherwise, returns the most recent Monday.
        
        Parameters
        ----------
        date : datetime, optional
            Reference date. If None, uses current date.
        
        Returns
        -------
        datetime
            Weekly open datetime (Monday 09:30 ET)
        """
        if date is None:
            date = self.get_current_et_time()
        else:
            # Ensure date is in ET timezone
            if date.tzinfo is None:
                date = self.ET.localize(date)
            else:
                date = date.astimezone(self.ET)
        
        # Find the Monday of the week
        days_since_monday = date.weekday()  # Monday = 0
        monday = date - timedelta(days=days_since_monday)
        
        # Set to market open time (09:30 ET)
        weekly_open = monday.replace(
            hour=self.MARKET_OPEN_HOUR,
            minute=self.MARKET_OPEN_MINUTE,
            second=0,
            microsecond=0,
        )
        
        # If we're before Monday 09:30, go back to previous Monday
        if date < weekly_open:
            weekly_open = weekly_open - timedelta(days=7)
        
        return weekly_open
    
    def get_daily_open(self, date: Optional[datetime] = None) -> datetime:
        """Get the daily open (09:30 ET) for a given date.
        
        Parameters
        ----------
        date : datetime, optional
            Reference date. If None, uses current date.
        
        Returns
        -------
        datetime
            Daily open datetime (09:30 ET on the specified date)
        """
        if date is None:
            date = self.get_current_et_time()
        else:
            # Ensure date is in ET timezone
            if date.tzinfo is None:
                date = self.ET.localize(date)
            else:
                date = date.astimezone(self.ET)
        
        # Set to market open time
        daily_open = date.replace(
            hour=self.MARKET_OPEN_HOUR,
            minute=self.MARKET_OPEN_MINUTE,
            second=0,
            microsecond=0,
        )
        
        # If we're before market open today, use yesterday's open
        if date < daily_open:
            daily_open = daily_open - timedelta(days=1)
        
        return daily_open
    
    def is_market_open(self, date: Optional[datetime] = None) -> bool:
        """Check if market is open at a given time.
        
        Parameters
        ----------
        date : datetime, optional
            Time to check. If None, uses current time.
        
        Returns
        -------
        bool
            True if market is open, False otherwise
        """
        if date is None:
            date = self.get_current_et_time()
        else:
            if date.tzinfo is None:
                date = self.ET.localize(date)
            else:
                date = date.astimezone(self.ET)
        
        # Check if weekday (Monday=0, Friday=4)
        if date.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if within market hours (9:30 AM - 4:00 PM ET)
        market_open = date.replace(
            hour=self.MARKET_OPEN_HOUR,
            minute=self.MARKET_OPEN_MINUTE,
            second=0,
            microsecond=0,
        )
        market_close = date.replace(
            hour=self.MARKET_CLOSE_HOUR,
            minute=self.MARKET_CLOSE_MINUTE,
            second=0,
            microsecond=0,
        )
        
        return market_open <= date < market_close
    
    def get_next_market_open(self, date: Optional[datetime] = None) -> datetime:
        """Get the next market open time after a given date.
        
        Parameters
        ----------
        date : datetime, optional
            Reference date. If None, uses current date.
        
        Returns
        -------
        datetime
            Next market open datetime
        """
        if date is None:
            date = self.get_current_et_time()
        else:
            if date.tzinfo is None:
                date = self.ET.localize(date)
            else:
                date = date.astimezone(self.ET)
        
        # Get today's market open
        today_open = date.replace(
            hour=self.MARKET_OPEN_HOUR,
            minute=self.MARKET_OPEN_MINUTE,
            second=0,
            microsecond=0,
        )
        
        # If we're before today's open, return today's open
        if date < today_open:
            # Check if today is a weekday
            if today_open.weekday() < 5:
                return today_open
            else:
                # If weekend, find next Monday
                days_ahead = 7 - today_open.weekday()
                return today_open + timedelta(days=days_ahead)
        
        # Otherwise, find next trading day
        next_day = date + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day = next_day + timedelta(days=1)
        
        return next_day.replace(
            hour=self.MARKET_OPEN_HOUR,
            minute=self.MARKET_OPEN_MINUTE,
            second=0,
            microsecond=0,
        )

