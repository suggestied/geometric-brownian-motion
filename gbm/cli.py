"""
Command-line interface for the GBM stock price simulator.
"""

import argparse
import sys
from pathlib import Path
from gbm.model import GBM


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description='Stock Price Simulation using Geometric Brownian Motion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s MSFT
  %(prog)s AMZN --history-period 100d --forecast-period 252 --seed 10
  %(prog)s AAPL --output forecast.png --no-plot
        """
    )
    
    parser.add_argument(
        'stock_ticker',
        type=str,
        help='Stock ticker symbol (e.g., MSFT, AMZN, AAPL)'
    )
    
    parser.add_argument(
        '--history-period',
        type=str,
        default='100d',
        help='Time period to look back for historical data (default: 100d). '
             'Examples: 100d, 1y, 6mo'
    )
    
    parser.add_argument(
        '--forecast-period',
        type=int,
        default=252,
        help='Number of trading days to forecast (default: 252)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=20,
        help='Random seed for NumPy pseudo-random number generator (default: 20)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Path to save the plot (optional)'
    )
    
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='Do not display the plot (useful for headless execution)'
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
        
        # Create GBM instance
        gbm = GBM(
            stock_ticker=args.stock_ticker,
            history_period=args.history_period,
            forecast_period=args.forecast_period,
            seed=args.seed
        )
        
        # Run simulation
        gbm.run(
            show_plot=not args.no_plot,
            output_path=args.output
        )
        
        print(f"\nSimulation completed for {args.stock_ticker}")
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
        return 1


if __name__ == '__main__':
    sys.exit(main())

