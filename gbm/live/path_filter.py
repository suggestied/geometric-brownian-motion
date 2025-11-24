"""Path filtering logic for eliminating incompatible paths."""

from typing import Optional
from datetime import datetime
from gbm.simulation.path_manager import PathManager


class PathFilter:
    """Filters paths based on actual market data.
    
    Compares actual prices to simulated paths and eliminates those
    that diverge beyond a tolerance threshold.
    
    Parameters
    ----------
    path_manager : PathManager
        Path manager instance to filter
    tolerance : float, default=0.01
        Maximum allowed deviation (1% = 0.01)
    """
    
    def __init__(
        self,
        path_manager: PathManager,
        tolerance: float = 0.01,  # 1% default
    ):
        self.path_manager = path_manager
        self.tolerance = tolerance
    
    def filter_paths(
        self,
        actual_price: float,
        timestamp: datetime,
    ) -> int:
        """Filter paths based on actual price observation.
        
        Parameters
        ----------
        actual_price : float
            Observed market price
        timestamp : datetime
            Timestamp of the observation
        
        Returns
        -------
        int
            Number of paths eliminated in this update
        """
        return self.path_manager.eliminate_paths(
            actual_price=actual_price,
            timestamp=timestamp,
            tolerance=self.tolerance,
        )
    
    def get_survival_rate(self) -> float:
        """Get current survival rate of paths.
        
        Returns
        -------
        float
            Fraction of paths still active (0.0 to 1.0)
        """
        stats = self.path_manager.get_statistics()
        return stats["survival_rate"]
    
    def get_active_count(self) -> int:
        """Get number of active paths.
        
        Returns
        -------
        int
            Number of paths still active
        """
        stats = self.path_manager.get_statistics()
        return stats["num_active"]
    
    def update_tolerance(self, new_tolerance: float) -> None:
        """Update the tolerance threshold.
        
        Parameters
        ----------
        new_tolerance : float
            New tolerance value (as fraction, e.g., 0.01 = 1%)
        """
        if new_tolerance <= 0 or new_tolerance >= 1:
            raise ValueError("Tolerance must be between 0 and 1")
        self.tolerance = new_tolerance

