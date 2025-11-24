"""
Command-line interface for the GBM stock price simulator.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from gbm.model import GBM
from gbm.data.alpaca_client import AlpacaClient
from gbm.data.multi_timeframe import MultiTimeframeManager
from gbm.data.market_calendar import MarketCalendar
from gbm.simulation.path_generator import PathGenerator
from gbm.simulation.path_manager import PathManager
from gbm.live.path_filter import PathFilter
from gbm.live.updater import LiveUpdater


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Stock Price Simulation using Geometric Brownian Motion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Traditional one-time simulation
  %(prog)s MSFT
  %(prog)s AMZN --history-period 100d --forecast-period 252 --seed 10
  
  # Live mode for NASDAQ futures
  %(prog)s NQ --live --starting-price weekly-open
  %(prog)s QQQ --live --num-paths 500 --tolerance 0.01
        """,
    )

    parser.add_argument(
        "ticker",
        type=str,
        help="Ticker symbol (e.g., MSFT, NQ, QQQ)",
    )

    # Live mode options
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live mode with continuous path elimination",
    )

    parser.add_argument(
        "--starting-price",
        type=str,
        default="weekly-open",
        help="Starting price: 'weekly-open', 'daily-open', or a numeric value (default: weekly-open)",
    )

    parser.add_argument(
        "--num-paths",
        type=int,
        default=500,
        help="Number of Monte Carlo paths to generate (default: 500)",
    )

    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Path elimination tolerance as fraction (default: 0.01 = 1%%)",
    )

    parser.add_argument(
        "--forecast-horizon-minutes",
        type=int,
        default=10080,
        help="Forecast horizon in minutes (default: 10080 = 1 week)",
    )

    parser.add_argument(
        "--update-interval",
        type=int,
        default=60,
        help="Update interval in seconds (default: 60 = 1 minute)",
    )

    parser.add_argument(
        "--history-days",
        type=int,
        default=30,
        help="Days of historical data to fetch (default: 30)",
    )

    # Traditional mode options (for backward compatibility)
    parser.add_argument(
        "--history-period",
        type=str,
        default="100d",
        help="Time period to look back for historical data (default: 100d). "
        "Examples: 100d, 1y, 6mo",
    )

    parser.add_argument(
        "--forecast-period",
        type=int,
        default=252,
        help="Number of trading days to forecast (default: 252)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20,
        help="Random seed for NumPy pseudo-random number generator (default: 20)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save the plot (optional)",
    )

    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Do not display the plot (useful for headless execution)",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments

    Raises
    ------
    ValueError
        If arguments are invalid
    """
    if args.forecast_period <= 0:
        raise ValueError("forecast-period must be positive")

    if args.output:
        output_path = Path(args.output)
        if not output_path.parent.exists():
            raise ValueError(
                f"Output directory does not exist: {output_path.parent}"
            )


def run_live_mode(args: argparse.Namespace) -> int:
    """Run live mode with continuous path elimination.
    
    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments
    
    Returns
    -------
    int
        Exit code
    """
    try:
        print("=" * 70)
        print("NASDAQ Futures Probability Simulator - Live Mode")
        print("=" * 70)
        
        # Initialize Alpaca client
        print("Connecting to Alpaca API...")
        alpaca_client = AlpacaClient()
        
        # Initialize market calendar
        calendar = MarketCalendar()
        
        # Initialize multi-timeframe manager
        print(f"Fetching historical data for {args.ticker}...")
        multi_tf = MultiTimeframeManager(alpaca_client, args.ticker)
        
        # Fetch historical data
        end_time = datetime.now()
        start_time = end_time - pd.Timedelta(days=args.history_days)
        multi_tf.fetch_historical_data(start_time, end_time, args.history_days)
        
        # Determine starting price
        print("Determining starting price...")
        start_datetime = None
        
        if args.starting_price == "weekly-open":
            start_datetime = calendar.get_weekly_open()
            # Normalize timezone for comparison
            start_datetime_naive = start_datetime.replace(tzinfo=None) if start_datetime.tzinfo else start_datetime
            
            # Try to get price at weekly open from daily data
            daily_data = multi_tf.data.get("1d", pd.DataFrame())
            if not daily_data.empty:
                # Find the closest daily bar to weekly open
                index_naive = pd.DatetimeIndex([
                    x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo else x 
                    for x in daily_data.index
                ])
                time_diff_series = pd.Series(
                    [(x - start_datetime_naive).total_seconds() for x in index_naive],
                    index=daily_data.index
                ).abs()
                closest_idx = time_diff_series.idxmin()
                start_price = float(daily_data.loc[closest_idx, "close"])
            else:
                # Fallback to latest available price
                start_price = multi_tf.get_latest_close("1d") or multi_tf.get_latest_close("1m")
                if start_price is None:
                    raise ValueError("Could not determine starting price")
        elif args.starting_price == "daily-open":
            start_datetime = calendar.get_daily_open()
            # Normalize timezone for comparison
            start_datetime_naive = start_datetime.replace(tzinfo=None) if start_datetime.tzinfo else start_datetime
            
            # Try to get price at daily open from 1m data
            min_data = multi_tf.data.get("1m", pd.DataFrame())
            if not min_data.empty:
                # Find the closest 1m bar to daily open
                index_naive = pd.DatetimeIndex([
                    x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo else x 
                    for x in min_data.index
                ])
                time_diff_series = pd.Series(
                    [(x - start_datetime_naive).total_seconds() for x in index_naive],
                    index=min_data.index
                ).abs()
                closest_idx = time_diff_series.idxmin()
                start_price = float(min_data.loc[closest_idx, "close"])
            else:
                start_price = multi_tf.get_latest_close("1m")
                if start_price is None:
                    raise ValueError("Could not determine starting price")
        else:
            try:
                start_price = float(args.starting_price)
                start_datetime = datetime.now()
            except ValueError:
                raise ValueError(f"Invalid starting price: {args.starting_price}")
        
        if start_price is None:
            raise ValueError("Could not determine starting price")
        
        if start_datetime is None:
            start_datetime = datetime.now()
        
        # Calculate parameters from HTF data
        print("Calculating model parameters...")
        htf_params = multi_tf.calculate_htf_parameters()
        
        if not htf_params:
            raise ValueError("Could not calculate parameters from historical data")
        
        # Use daily timeframe parameters
        preferred_tf = "1d" if "1d" in htf_params else list(htf_params.keys())[0]
        params = htf_params[preferred_tf]
        mu = params["mu"]
        sigma = params["sigma"]
        
        # Generate paths
        print(f"Generating {args.num_paths} Monte Carlo paths...")
        path_generator = PathGenerator(
            starting_price=start_price,
            mu=mu,
            sigma=sigma,
            forecast_horizon_minutes=args.forecast_horizon_minutes,
            num_paths=args.num_paths,
        )
        
        # Normalize start_datetime to naive for path generation
        start_datetime_naive = start_datetime.replace(tzinfo=None) if start_datetime.tzinfo else start_datetime
        paths, time_index = path_generator.generate_paths(start_datetime_naive)
        print(f"✓ {len(paths)} paths generated")
        
        # Create path manager
        path_manager = PathManager(paths, time_index)
        
        # Create path filter
        path_filter = PathFilter(path_manager, tolerance=args.tolerance)
        
        # Get weekly and daily open prices for display
        weekly_open_price = None
        daily_open_price = None
        
        if args.starting_price == "weekly-open":
            weekly_open_price = start_price
            # Also get daily open
            daily_open_datetime = calendar.get_daily_open()
            daily_open_datetime_naive = daily_open_datetime.replace(tzinfo=None) if daily_open_datetime.tzinfo else daily_open_datetime
            daily_data = multi_tf.data.get("1m", pd.DataFrame())
            if not daily_data.empty:
                index_naive = pd.DatetimeIndex([
                    x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo else x 
                    for x in daily_data.index
                ])
                time_diff_series = pd.Series(
                    [(x - daily_open_datetime_naive).total_seconds() for x in index_naive],
                    index=daily_data.index
                ).abs()
                closest_idx = time_diff_series.idxmin()
                daily_open_price = float(daily_data.loc[closest_idx, "close"])
        elif args.starting_price == "daily-open":
            daily_open_price = start_price
            # Also get weekly open
            weekly_open_datetime = calendar.get_weekly_open()
            weekly_open_datetime_naive = weekly_open_datetime.replace(tzinfo=None) if weekly_open_datetime.tzinfo else weekly_open_datetime
            weekly_data = multi_tf.data.get("1d", pd.DataFrame())
            if not weekly_data.empty:
                index_naive = pd.DatetimeIndex([
                    x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo else x 
                    for x in weekly_data.index
                ])
                time_diff_series = pd.Series(
                    [(x - weekly_open_datetime_naive).total_seconds() for x in index_naive],
                    index=weekly_data.index
                ).abs()
                closest_idx = time_diff_series.idxmin()
                weekly_open_price = float(weekly_data.loc[closest_idx, "close"])
        
        # Determine output path for visualization
        # In Docker, output should be in /app/output which is mounted to ./output
        output_path = args.output or "/app/output/live_forecast.png"
        
        # Create live updater
        updater = LiveUpdater(
            path_manager=path_manager,
            multi_tf_manager=multi_tf,
            path_filter=path_filter,
            update_interval_seconds=args.update_interval,
            weekly_open_price=weekly_open_price,
            daily_open_price=daily_open_price,
            output_path=output_path,
            plot_update_frequency=5,  # Update plot every 5 updates (5 minutes)
        )
        
        # Display initial summary
        print("\n" + "=" * 70)
        print("SIMULATION CONFIGURATION")
        print("=" * 70)
        print(f"Ticker: {args.ticker}")
        print(f"Starting Price: ${start_price:.2f} | Forecast: {args.forecast_horizon_minutes/60:.0f} hours")
        print(f"Paths: {args.num_paths} | Tolerance: {args.tolerance*100:.1f}% | Update: {args.update_interval}s")
        print(f"Drift (μ): {mu:.4f} | Volatility (σ): {sigma:.4f}")
        if weekly_open_price:
            print(f"Weekly Open: ${weekly_open_price:.2f}", end="")
        if daily_open_price:
            print(f" | Daily Open: ${daily_open_price:.2f}", end="")
        if weekly_open_price or daily_open_price:
            print()
        print(f"Chart: {output_path} (updates every 5 minutes)")
        print("=" * 70)
        print("\nStarting live updates... (Press Ctrl+C to stop)\n")
        
        # Start live updates
        updater.start()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point for the CLI.

    Returns
    -------
    int
        Exit code (0 for success, 1 for error)
    """
    try:
        args = parse_args()
        validate_args(args)

        # Route to live mode or traditional mode
        if args.live:
            return run_live_mode(args)
        
        # Traditional mode (backward compatibility)
        gbm = GBM(
            stock_ticker=args.ticker,
            history_period=args.history_period,
            forecast_period=args.forecast_period,
            seed=args.seed
        )
        
        # Run simulation
        gbm.run(
            show_plot=not args.no_plot,
            output_path=args.output
        )
        
        print(f"\nSimulation completed for {args.ticker}")
        print(f"Initial price: ${gbm.So:.2f}")
        print(f"Final forecasted price: ${gbm.S[-1]:.2f}")
        print(f"Annualized return (mu): {gbm.mu:.4f}")
        print(f"Annualized volatility (sigma): {gbm.sigma:.4f}")

        if args.output:
            print(f"Plot saved to: {args.output}")

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
