"""Reversal zone detection from surviving Monte Carlo paths."""

from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd
from datetime import datetime
from scipy import stats
from scipy.signal import find_peaks
from gbm.simulation.path_manager import PathManager


class ReversalZoneDetector:
    """Detects probable reversal zones from surviving paths.
    
    Analyzes active paths to identify:
    - Price levels where paths cluster (convergence zones)
    - Areas where paths change direction (reversal points)
    - High-probability support/resistance levels
    """
    
    def __init__(self, path_manager: PathManager):
        """Initialize reversal zone detector.
        
        Parameters
        ----------
        path_manager : PathManager
            Path manager instance with active paths
        """
        self.path_manager = path_manager
    
    def detect_zones(
        self,
        timestamp: Optional[datetime] = None,
        num_bins: int = 50,
        min_paths: int = 10,
    ) -> List[Dict]:
        """Detect reversal zones from active paths.
        
        Parameters
        ----------
        timestamp : datetime, optional
            Timestamp to analyze. If None, uses current time or end of paths.
        num_bins : int, default=50
            Number of price bins for clustering analysis
        min_paths : int, default=10
            Minimum number of paths needed in a zone to consider it significant
        
        Returns
        -------
        list
            List of zone dictionaries, each with:
            - price_level: Center price of the zone
            - probability: Fraction of paths in this zone
            - path_count: Number of paths in zone
            - zone_type: "support", "resistance", or "convergence"
        """
        if timestamp is None:
            # Use the last timestamp in the time index
            if len(self.path_manager.time_index) > 0:
                timestamp = self.path_manager.time_index[-1]
            else:
                return []
        
        # Get all active path prices at this timestamp
        prices = self.path_manager.get_all_paths_at_time(timestamp)
        
        if len(prices) < min_paths:
            return []
        
        prices = np.array(prices)
        
        # Use histogram to find clusters
        hist, bin_edges = np.histogram(prices, bins=num_bins)
        
        # Find bins with high density (potential zones)
        zones = []
        threshold = max(hist) * 0.3  # At least 30% of max density
        
        for i, count in enumerate(hist):
            if count >= min_paths and count >= threshold:
                # Calculate zone center and range
                zone_low = bin_edges[i]
                zone_high = bin_edges[i + 1]
                zone_center = (zone_low + zone_high) / 2
                
                # Determine zone type based on position relative to current price
                bounds = self.path_manager.get_path_bounds_at_time(timestamp)
                if bounds:
                    if zone_center < bounds["mean"]:
                        zone_type = "support"
                    elif zone_center > bounds["mean"]:
                        zone_type = "resistance"
                    else:
                        zone_type = "convergence"
                else:
                    zone_type = "convergence"
                
                probability = count / len(prices)
                
                zones.append({
                    "price_level": float(zone_center),
                    "price_low": float(zone_low),
                    "price_high": float(zone_high),
                    "probability": float(probability),
                    "path_count": int(count),
                    "zone_type": zone_type,
                })
        
        # Sort by probability (highest first)
        zones.sort(key=lambda x: x["probability"], reverse=True)
        
        return zones
    
    def detect_reversal_points(
        self,
        lookback_minutes: int = 60,
        min_paths: int = 10,
    ) -> List[Dict]:
        """Detect points where paths tend to reverse direction.
        
        Parameters
        ----------
        lookback_minutes : int, default=60
            Number of minutes to look back for reversal detection
        min_paths : int, default=10
            Minimum paths needed for significance
        
        Returns
        -------
        list
            List of reversal point dictionaries
        """
        if not self.path_manager.active_paths:
            return []
        
        # Get current timestamp
        current_time = self.path_manager.time_index[-1]
        lookback_time = current_time - pd.Timedelta(minutes=lookback_minutes)
        
        # Find indices
        try:
            current_idx = self.path_manager.time_index.get_loc(current_time)
            lookback_idx = self.path_manager.time_index.get_loc(lookback_time, method="nearest")
        except Exception:
            return []
        
        reversals = []
        
        # Analyze each active path for reversals
        for path_idx in self.path_manager.active_paths:
            path = self.path_manager.paths[path_idx]
            
            if current_idx >= len(path) or lookback_idx >= len(path):
                continue
            
            # Get price segment
            segment = path[lookback_idx:current_idx + 1]
            
            if len(segment) < 3:
                continue
            
            # Find local extrema
            # Local minima (potential support)
            for i in range(1, len(segment) - 1):
                if segment[i] < segment[i - 1] and segment[i] < segment[i + 1]:
                    timestamp = self.path_manager.time_index[lookback_idx + i]
                    reversals.append({
                        "timestamp": timestamp,
                        "price": float(segment[i]),
                        "type": "support",
                        "path_index": path_idx,
                    })
            
            # Local maxima (potential resistance)
            for i in range(1, len(segment) - 1):
                if segment[i] > segment[i - 1] and segment[i] > segment[i + 1]:
                    timestamp = self.path_manager.time_index[lookback_idx + i]
                    reversals.append({
                        "timestamp": timestamp,
                        "price": float(segment[i]),
                        "type": "resistance",
                        "path_index": path_idx,
                    })
        
        # Cluster reversal points by price
        if not reversals:
            return []
        
        reversal_prices = np.array([r["price"] for r in reversals])
        
        # Use KDE to find density peaks
        try:
            kde = stats.gaussian_kde(reversal_prices)
            price_range = np.linspace(reversal_prices.min(), reversal_prices.max(), 100)
            density = kde(price_range)
            
            # Find peaks in density
            peaks, properties = find_peaks(density, height=np.max(density) * 0.3)
            
            significant_reversals = []
            for peak_idx in peaks:
                price_level = price_range[peak_idx]
                
                # Count reversals near this price
                tolerance = (reversal_prices.max() - reversal_prices.min()) * 0.02  # 2% tolerance
                nearby = np.abs(reversal_prices - price_level) < tolerance
                count = np.sum(nearby)
                
                if count >= min_paths:
                    # Determine type based on nearby reversals
                    nearby_reversals = [reversals[i] for i in range(len(reversals)) if nearby[i]]
                    support_count = sum(1 for r in nearby_reversals if r["type"] == "support")
                    resistance_count = sum(1 for r in nearby_reversals if r["type"] == "resistance")
                    
                    zone_type = "support" if support_count > resistance_count else "resistance"
                    
                    significant_reversals.append({
                        "price_level": float(price_level),
                        "probability": float(count / len(reversals)),
                        "reversal_count": int(count),
                        "zone_type": zone_type,
                    })
        except Exception:
            # Fallback: simple clustering
            significant_reversals = self._simple_reversal_clustering(reversals, min_paths)
        
        return significant_reversals
    
    def _simple_reversal_clustering(
        self,
        reversals: List[Dict],
        min_paths: int,
    ) -> List[Dict]:
        """Simple clustering of reversal points.
        
        Parameters
        ----------
        reversals : list
            List of reversal dictionaries
        min_paths : int
            Minimum paths needed
        
        Returns
        -------
        list
            Clustered reversal zones
        """
        if not reversals:
            return []
        
        prices = np.array([r["price"] for r in reversals])
        
        # Simple binning approach
        num_bins = 20
        hist, bin_edges = np.histogram(prices, bins=num_bins)
        
        zones = []
        for i, count in enumerate(hist):
            if count >= min_paths:
                zone_center = (bin_edges[i] + bin_edges[i + 1]) / 2
                
                # Count types
                zone_reversals = [
                    r for r in reversals
                    if bin_edges[i] <= r["price"] < bin_edges[i + 1]
                ]
                support_count = sum(1 for r in zone_reversals if r["type"] == "support")
                resistance_count = sum(1 for r in zone_reversals if r["type"] == "resistance")
                
                zone_type = "support" if support_count > resistance_count else "resistance"
                
                zones.append({
                    "price_level": float(zone_center),
                    "probability": float(count / len(reversals)),
                    "reversal_count": int(count),
                    "zone_type": zone_type,
                })
        
        return zones
    
    def get_convergence_zones(
        self,
        future_minutes: int = 240,  # 4 hours
        num_zones: int = 5,
    ) -> List[Dict]:
        """Get zones where paths converge in the future.
        
        Parameters
        ----------
        future_minutes : int, default=240
            How many minutes into the future to analyze
        num_zones : int, default=5
            Maximum number of zones to return
        
        Returns
        -------
        list
            List of convergence zones
        """
        if not self.path_manager.active_paths:
            return []
        
        # Get future timestamp
        current_time = self.path_manager.time_index[-1]
        future_time = current_time + pd.Timedelta(minutes=future_minutes)
        
        # Get path bounds at future time
        bounds = self.path_manager.get_path_bounds_at_time(future_time)
        if not bounds:
            return []
        
        # Analyze path distribution at future time
        future_prices = self.path_manager.get_all_paths_at_time(future_time)
        
        if len(future_prices) < 10:
            return []
        
        future_prices = np.array(future_prices)
        
        # Use percentiles to find convergence zones
        percentiles = [10, 25, 50, 75, 90]
        zones = []
        
        for i in range(len(percentiles) - 1):
            p_low = np.percentile(future_prices, percentiles[i])
            p_high = np.percentile(future_prices, percentiles[i + 1])
            
            # Count paths in this range
            in_range = (future_prices >= p_low) & (future_prices <= p_high)
            count = np.sum(in_range)
            
            if count > 0:
                zones.append({
                    "price_level": float((p_low + p_high) / 2),
                    "price_low": float(p_low),
                    "price_high": float(p_high),
                    "probability": float(count / len(future_prices)),
                    "path_count": int(count),
                    "zone_type": "convergence",
                    "time_horizon_minutes": future_minutes,
                })
        
        # Sort by probability and return top zones
        zones.sort(key=lambda x: x["probability"], reverse=True)
        return zones[:num_zones]

