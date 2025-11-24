"""Main live update loop for continuous path elimination."""

import time
from typing import Optional, Callable
from datetime import datetime, timedelta
from gbm.data.multi_timeframe import MultiTimeframeManager
from gbm.data.market_calendar import MarketCalendar
from gbm.simulation.path_manager import PathManager
from gbm.live.path_filter import PathFilter
from gbm.simulation.reversal_zones import ReversalZoneDetector
from gbm.visualization import plot_paths_with_zones


class LiveUpdater:
    """Main loop for live updating and path elimination.
    
    Polls for new market data at regular intervals, filters paths,
    and maintains the simulation state.
    
    Parameters
    ----------
    path_manager : PathManager
        Path manager with simulated paths
    multi_tf_manager : MultiTimeframeManager
        Multi-timeframe data manager
    path_filter : PathFilter
        Path filter for elimination logic
    update_interval_seconds : int, default=60
        How often to check for new data (in seconds)
    callback : callable, optional
        Optional callback function called after each update
    """
    
    def __init__(
        self,
        path_manager: PathManager,
        multi_tf_manager: MultiTimeframeManager,
        path_filter: PathFilter,
        update_interval_seconds: int = 60,  # 1 minute default
        callback: Optional[Callable] = None,
        weekly_open_price: Optional[float] = None,
        daily_open_price: Optional[float] = None,
        output_path: Optional[str] = None,
        plot_update_frequency: int = 5,  # Update plot every N updates
    ):
        self.path_manager = path_manager
        self.multi_tf_manager = multi_tf_manager
        self.path_filter = path_filter
        self.update_interval_seconds = update_interval_seconds
        self.callback = callback
        self.weekly_open_price = weekly_open_price
        self.daily_open_price = daily_open_price
        self.output_path = output_path
        self.plot_update_frequency = plot_update_frequency
        
        self.calendar = MarketCalendar()
        self.reversal_detector = ReversalZoneDetector(path_manager)
        
        self.running = False
        self.last_update_time: Optional[datetime] = None
        self.update_count = 0
        self.start_time = datetime.now()
    
    def start(self) -> None:
        """Start the live update loop.
        
        This will run continuously until stop() is called.
        """
        self.running = True
        print(f"Starting live updater (interval: {self.update_interval_seconds}s)")
        
        while self.running:
            try:
                self.update()
                time.sleep(self.update_interval_seconds)
            except KeyboardInterrupt:
                print("\nStopping live updater...")
                self.stop()
                break
            except Exception as e:
                print(f"Error in update loop: {e}")
                time.sleep(self.update_interval_seconds)  # Continue despite errors
    
    def stop(self) -> None:
        """Stop the live update loop."""
        self.running = False
        print("Live updater stopped")
    
    def update(self) -> dict:
        """Perform a single update cycle.
        
        Returns
        -------
        dict
            Update statistics and results
        """
        self.update_count += 1
        current_time = datetime.now()
        
        # Fetch latest data
        self.multi_tf_manager.update_latest_bars()
        
        # Get latest 1-minute close price
        latest_price = self.multi_tf_manager.get_latest_close("1m")
        
        if latest_price is None:
            print(f"Update {self.update_count}: No price data available")
            return {"status": "no_data"}
        
        # Filter paths based on latest price
        eliminated = self.path_filter.filter_paths(
            actual_price=latest_price,
            timestamp=current_time,
        )
        
        # Get statistics
        stats = self.path_manager.get_statistics()
        survival_rate = self.path_filter.get_survival_rate()
        
        # Detect reversal zones
        zones = self.reversal_detector.detect_zones(timestamp=current_time)
        
        # Prepare update info
        update_info = {
            "update_count": self.update_count,
            "timestamp": current_time,
            "latest_price": latest_price,
            "paths_eliminated": eliminated,
            "paths_active": stats["num_active"],
            "paths_total": stats["num_total"],
            "survival_rate": survival_rate,
            "reversal_zones": zones[:5],  # Top 5 zones
        }
        
        self.last_update_time = current_time
        
        # Print update info with formatting
        print("-" * 80)
        print(f"Update #{self.update_count} | {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        print(f"Current Price: ${latest_price:.2f}")
        
        # Show weekly/daily opens if available
        if self.weekly_open_price is not None:
            diff_weekly = ((latest_price - self.weekly_open_price) / self.weekly_open_price) * 100
            print(f"Weekly Open: ${self.weekly_open_price:.2f} ({diff_weekly:+.2f}%)")
        if self.daily_open_price is not None:
            diff_daily = ((latest_price - self.daily_open_price) / self.daily_open_price) * 100
            print(f"Daily Open: ${self.daily_open_price:.2f} ({diff_daily:+.2f}%)")
        
        print(f"\nPath Status:")
        print(f"  Active: {stats['num_active']}/{stats['num_total']} ({survival_rate*100:.1f}%)")
        print(f"  Eliminated this update: {eliminated}")
        
        # Display reversal zones
        if zones:
            print(f"\nReversal Zones (Top {min(5, len(zones))}):")
            for i, zone in enumerate(zones[:5], 1):
                zone_type_icon = "🟢" if zone['zone_type'] == 'support' else "🔴" if zone['zone_type'] == 'resistance' else "🟡"
                print(
                    f"  {i}. {zone_type_icon} {zone['zone_type'].title():12s} "
                    f"@ ${zone['price_level']:.2f} "
                    f"(Probability: {zone['probability']*100:.1f}%, "
                    f"Paths: {zone['path_count']})"
                )
        else:
            print("\nReversal Zones: None detected yet")
        
        # Show "radiation" progress
        elapsed_minutes = (current_time - self.start_time).total_seconds() / 60
        if elapsed_minutes > 0:
            elimination_rate = (stats['num_total'] - stats['num_active']) / elapsed_minutes
            print(f"\nRadiation Progress: {elimination_rate:.1f} paths eliminated/minute")
        
        # Update visualization periodically (every N updates or on first update)
        should_update_plot = (
            self.output_path and 
            (self.update_count == 1 or self.update_count % self.plot_update_frequency == 0)
        )
        
        if should_update_plot:
            print(f"\n🖼️  Generating visualization (update #{self.update_count})...")
            try:
                from pathlib import Path
                import os
                import sys
                
                # Ensure output directory exists
                output_path_obj = Path(self.output_path)
                output_dir = output_path_obj.parent
                if output_dir:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    print(f"   Output directory: {output_dir.resolve()}")
                    print(f"   Directory exists: {output_dir.exists()}")
                
                print(f"   Output path: {output_path_obj.resolve()}")
                print(f"   Active paths: {len(self.path_manager.active_paths)}")
                sys.stdout.flush()
                
                print("   Calling plot_paths_with_zones...")
                sys.stdout.flush()
                
                plot_paths_with_zones(
                    path_manager=self.path_manager,
                    reversal_detector=self.reversal_detector,
                    current_price=latest_price,
                    current_time=current_time,
                    weekly_open=self.weekly_open_price,
                    daily_open=self.daily_open_price,
                    output_path=str(self.output_path),
                    show_plot=False,
                )
                
                sys.stdout.flush()
                print(f"📊 Visualization saved: {self.output_path}")
                sys.stdout.flush()
            except Exception as e:
                import traceback
                print(f"\n⚠️  Could not update visualization: {e}")
                traceback.print_exc()
                sys.stdout.flush()
        
        print("=" * 80)
        
        # Call callback if provided
        if self.callback:
            try:
                self.callback(update_info)
            except Exception as e:
                print(f"Callback error: {e}")
        
        return update_info
    
    def get_status(self) -> dict:
        """Get current status of the updater.
        
        Returns
        -------
        dict
            Status information
        """
        stats = self.path_manager.get_statistics()
        
        return {
            "running": self.running,
            "update_count": self.update_count,
            "last_update": self.last_update_time,
            "update_interval_seconds": self.update_interval_seconds,
            "paths_active": stats["num_active"],
            "paths_total": stats["num_total"],
            "survival_rate": stats["survival_rate"],
        }
    
    def run_single_update(self) -> dict:
        """Run a single update without starting the loop.
        
        Useful for testing or manual updates.
        
        Returns
        -------
        dict
            Update results
        """
        return self.update()

