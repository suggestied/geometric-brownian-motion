"""Path manager for tracking and eliminating Monte Carlo paths."""

from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from datetime import datetime


class PathManager:
    """Manages a collection of Monte Carlo paths.
    
    Tracks all simulated paths, provides methods for elimination based on
    actual price data, and maintains statistics about surviving paths.
    
    Parameters
    ----------
    paths : list of np.ndarray
        List of path arrays (each is a time series of prices)
    time_index : pd.DatetimeIndex
        Datetime index corresponding to path time steps
    """
    
    def __init__(
        self,
        paths: List[np.ndarray],
        time_index: pd.DatetimeIndex,
    ):
        self.paths = paths
        self.time_index = time_index
        self.num_paths = len(paths)
        
        # Track which paths are still active (not eliminated)
        self.active_paths = set(range(self.num_paths))
        
        # Store path metadata
        self.path_metadata: Dict[int, Dict] = {
            i: {"eliminated": False, "eliminated_at": None} for i in range(self.num_paths)
        }
    
    def get_active_paths(self) -> List[np.ndarray]:
        """Get all currently active (non-eliminated) paths.
        
        Returns
        -------
        list
            List of active path arrays
        """
        return [self.paths[i] for i in self.active_paths]
    
    def get_active_path_indices(self) -> List[int]:
        """Get indices of active paths.
        
        Returns
        -------
        list
            List of active path indices
        """
        return list(self.active_paths)
    
    def get_path_at_time(
        self,
        path_index: int,
        timestamp: datetime,
    ) -> Optional[float]:
        """Get the price value of a path at a specific timestamp.
        
        Parameters
        ----------
        path_index : int
            Index of the path
        timestamp : datetime
            Timestamp to get price at
        
        Returns
        -------
        float, optional
            Price at the timestamp, or None if timestamp is out of range
        """
        if path_index < 0 or path_index >= self.num_paths:
            return None
        
        # Find the closest time index
        try:
            idx = self.time_index.get_indexer([timestamp], method="nearest")[0]
            if idx < 0 or idx >= len(self.paths[path_index]):
                return None
            return float(self.paths[path_index][idx])
        except Exception:
            return None
    
    def eliminate_paths(
        self,
        actual_price: float,
        timestamp: datetime,
        tolerance: float = 0.01,  # 1% default
    ) -> int:
        """Eliminate paths that diverge too far from actual price.
        
        Parameters
        ----------
        actual_price : float
            Actual observed price
        timestamp : datetime
            Timestamp of the observation
        tolerance : float, default=0.01
            Maximum allowed deviation (as fraction, e.g., 0.01 = 1%)
        
        Returns
        -------
        int
            Number of paths eliminated in this update
        """
        eliminated_count = 0
        
        # Check each active path
        paths_to_remove = []
        
        for path_idx in list(self.active_paths):
            path_price = self.get_path_at_time(path_idx, timestamp)
            
            if path_price is None:
                continue
            
            # Calculate deviation
            deviation = abs(path_price - actual_price) / actual_price
            
            if deviation > tolerance:
                paths_to_remove.append(path_idx)
                self.path_metadata[path_idx]["eliminated"] = True
                self.path_metadata[path_idx]["eliminated_at"] = timestamp
                eliminated_count += 1
        
        # Remove eliminated paths from active set
        for path_idx in paths_to_remove:
            self.active_paths.remove(path_idx)
        
        return eliminated_count
    
    def get_statistics(self) -> Dict:
        """Get statistics about the path collection.
        
        Returns
        -------
        dict
            Dictionary with statistics:
            - num_total: Total number of paths
            - num_active: Number of active paths
            - num_eliminated: Number of eliminated paths
            - survival_rate: Fraction of paths still active
        """
        num_active = len(self.active_paths)
        num_eliminated = self.num_paths - num_active
        
        return {
            "num_total": self.num_paths,
            "num_active": num_active,
            "num_eliminated": num_eliminated,
            "survival_rate": num_active / self.num_paths if self.num_paths > 0 else 0.0,
        }
    
    def get_path_bounds_at_time(
        self,
        timestamp: datetime,
    ) -> Optional[Dict[str, float]]:
        """Get min/max/mean of active paths at a specific timestamp.
        
        Parameters
        ----------
        timestamp : datetime
            Timestamp to analyze
        
        Returns
        -------
        dict, optional
            Dictionary with 'min', 'max', 'mean', 'std' keys, or None if no active paths
        """
        if not self.active_paths:
            return None
        
        prices = []
        for path_idx in self.active_paths:
            price = self.get_path_at_time(path_idx, timestamp)
            if price is not None:
                prices.append(price)
        
        if not prices:
            return None
        
        prices = np.array(prices)
        
        return {
            "min": float(np.min(prices)),
            "max": float(np.max(prices)),
            "mean": float(np.mean(prices)),
            "std": float(np.std(prices)),
            "median": float(np.median(prices)),
        }
    
    def get_all_paths_at_time(
        self,
        timestamp: datetime,
    ) -> List[float]:
        """Get all active path prices at a specific timestamp.
        
        Parameters
        ----------
        timestamp : datetime
            Timestamp to get prices at
        
        Returns
        -------
        list
            List of prices from all active paths
        """
        prices = []
        for path_idx in self.active_paths:
            price = self.get_path_at_time(path_idx, timestamp)
            if price is not None:
                prices.append(price)
        return prices

