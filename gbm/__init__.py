"""Geometric Brownian Motion (GBM) Stock Price Simulator.

A Python package for simulating stock price movements using the Geometric
Brownian Motion stochastic calculus model.
"""

from gbm.model import GBM

# Live simulation components
from gbm.data import AlpacaClient, MultiTimeframeManager, MarketCalendar
from gbm.simulation import PathGenerator, PathManager, ReversalZoneDetector
from gbm.live import PathFilter, LiveUpdater

__version__ = "1.0.0"
__all__ = [
    "GBM",
    "AlpacaClient",
    "MultiTimeframeManager",
    "MarketCalendar",
    "PathGenerator",
    "PathManager",
    "ReversalZoneDetector",
    "PathFilter",
    "LiveUpdater",
]
