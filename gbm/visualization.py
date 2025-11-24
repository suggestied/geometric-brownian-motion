"""Visualization utilities for plotting paths and reversal zones."""

import os
import matplotlib
# Use non-interactive backend for headless environments (Docker)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path
from gbm.simulation.path_manager import PathManager
from gbm.simulation.reversal_zones import ReversalZoneDetector
from gbm.data.market_calendar import MarketCalendar


def plot_paths_with_zones(
    path_manager: PathManager,
    reversal_detector: ReversalZoneDetector,
    current_price: float,
    current_time: datetime,
    weekly_open: Optional[float] = None,
    daily_open: Optional[float] = None,
    output_path: Optional[str] = None,
    show_plot: bool = True,
) -> None:
    """Plot active paths with reversal zones and annotations.
    
    Parameters
    ----------
    path_manager : PathManager
        Path manager with active paths
    reversal_detector : ReversalZoneDetector
        Reversal zone detector
    current_price : float
        Current market price
    current_time : datetime
        Current timestamp
    weekly_open : float, optional
        Weekly open price to annotate
    daily_open : float, optional
        Daily open price to annotate
    output_path : str, optional
        Path to save the plot
    show_plot : bool, default=True
        Whether to display the plot
    """
    if not path_manager.active_paths:
        return
    
    # Get active paths
    active_paths = path_manager.get_active_paths()
    if len(active_paths) == 0:
        return
    
    # Ensure output directory exists
    if output_path:
        output_dir = Path(output_path).parent
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    time_index = path_manager.time_index
    
    # Normalize time_index to naive for plotting
    if hasattr(time_index, 'tz') and time_index.tz is not None:
        time_index_plot = time_index.tz_localize(None)
    else:
        time_index_plot = time_index
    
    # Normalize current_time for bounds calculation
    current_time_naive = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
    
    # Plot all active paths (with transparency)
    for path in active_paths:
        ax.plot(
            time_index_plot[:len(path)],
            path,
            alpha=0.1,
            color='blue',
            linewidth=0.5,
        )
    
    # Get path bounds for shading (sample to avoid too many calls)
    bounds_data = []
    sample_size = min(100, len(time_index_plot), len(active_paths[0]))
    step = max(1, len(time_index_plot) // sample_size)
    
    for idx in range(0, min(len(time_index_plot), len(active_paths[0])), step):
        timestamp = time_index_plot[idx]
        bounds = path_manager.get_path_bounds_at_time(timestamp)
        if bounds:
            bounds_data.append({
                'time': timestamp,
                'min': bounds['min'],
                'max': bounds['max'],
                'mean': bounds['mean'],
            })
    
    if bounds_data:
        bounds_df = pd.DataFrame(bounds_data)
        bounds_df.set_index('time', inplace=True)
        
        # Shade the range
        ax.fill_between(
            bounds_df.index,
            bounds_df['min'],
            bounds_df['max'],
            alpha=0.2,
            color='blue',
            label='Path Range',
        )
        
        # Plot mean path
        ax.plot(
            bounds_df.index,
            bounds_df['mean'],
            color='darkblue',
            linewidth=2,
            label='Mean Path',
        )
    
    # Plot current price
    ax.axhline(
        y=current_price,
        color='red',
        linestyle='--',
        linewidth=2,
        label=f'Current Price: ${current_price:.2f}',
    )
    
    # Annotate weekly open
    if weekly_open is not None:
        ax.axhline(
            y=weekly_open,
            color='green',
            linestyle='--',
            linewidth=1.5,
            alpha=0.7,
            label=f'Weekly Open: ${weekly_open:.2f}',
        )
        ax.annotate(
            'Weekly Open',
            xy=(time_index_plot[0], weekly_open),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='green', alpha=0.3),
            fontsize=9,
        )
    
    # Annotate daily open
    if daily_open is not None:
        ax.axhline(
            y=daily_open,
            color='orange',
            linestyle='--',
            linewidth=1.5,
            alpha=0.7,
            label=f'Daily Open: ${daily_open:.2f}',
        )
        ax.annotate(
            'Daily Open',
            xy=(time_index_plot[0], daily_open),
            xytext=(10, -20),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.3),
            fontsize=9,
        )
    
    # Get and plot reversal zones
    zones = reversal_detector.detect_zones(timestamp=current_time_naive)
    top_zones = zones[:5]  # Top 5 zones
    
    for i, zone in enumerate(top_zones):
        color = 'purple' if zone['zone_type'] == 'support' else 'brown'
        ax.axhspan(
            zone.get('price_low', zone['price_level'] * 0.999),
            zone.get('price_high', zone['price_level'] * 1.001),
            alpha=0.15,
            color=color,
        )
        ax.annotate(
            f"{zone['zone_type'].title()}: ${zone['price_level']:.2f}\n"
            f"({zone['probability']*100:.1f}%)",
            xy=(time_index_plot[-1], zone['price_level']),
            xytext=(10, 0),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.5),
            fontsize=8,
        )
    
    # Statistics
    stats = path_manager.get_statistics()
    title = (
        f"Active Paths: {stats['num_active']}/{stats['num_total']} "
        f"({stats['survival_rate']*100:.1f}%) | "
        f"Current: ${current_price:.2f}"
    )
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Price ($)', fontsize=12)
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # Format x-axis dates
    fig.autofmt_xdate()
    plt.tight_layout()
    
    if output_path:
        output_path_abs = Path(output_path).resolve()
        output_path_abs.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(str(output_path_abs), dpi=300, bbox_inches='tight')
    
    if show_plot:
        plt.show()
    else:
        plt.close(fig)

