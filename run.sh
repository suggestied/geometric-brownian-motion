#!/bin/bash
# Quick run script for GBM simulator using Docker

set -e

# Default values
TICKER=${1:-MSFT}
MODE=${2:-traditional}  # 'traditional' or 'live'

# Create output directory if it doesn't exist
mkdir -p output

echo "=========================================="
echo "GBM Simulator - Docker Mode"
echo "=========================================="
echo "Ticker: $TICKER"
echo "Mode: $MODE"
echo ""

# Build image if it doesn't exist or if --rebuild flag is set
if [[ "$3" == "--rebuild" ]] || ! docker image inspect gbm-simulator >/dev/null 2>&1; then
    echo "Building Docker image..."
    docker build -t gbm-simulator .
    echo ""
fi

# Check for live mode
if [[ "$MODE" == "live" ]]; then
    echo "Starting LIVE mode..."
    echo ""
    
    # Check for .env file
    if [[ -f ".env" ]]; then
        echo "Found .env file, will load credentials from it"
        ENV_FILE_FLAG="-v $(pwd)/.env:/app/.env"
    else
        echo "WARNING: .env file not found!"
        echo "Create a .env file with ALPACA_API_KEY and ALPACA_API_SECRET"
        echo "Or set environment variables:"
        echo "  export ALPACA_API_KEY='your_key'"
        echo "  export ALPACA_API_SECRET='your_secret'"
        echo ""
        
        # Check if API keys are set in environment
        if [[ -z "$ALPACA_API_KEY" ]] || [[ -z "$ALPACA_API_SECRET" ]]; then
            echo "ERROR: Alpaca API credentials not found!"
            echo "Please create a .env file or set environment variables."
            exit 1
        fi
        ENV_FILE_FLAG=""
    fi
    
    # Run live mode
    docker run --rm -it \
        -v "$(pwd)/output:/app/output" \
        $ENV_FILE_FLAG \
        -e ALPACA_API_KEY="$ALPACA_API_KEY" \
        -e ALPACA_API_SECRET="$ALPACA_API_SECRET" \
        -e ALPACA_USE_PAPER="$ALPACA_USE_PAPER" \
        gbm-simulator \
        python -m gbm.cli "$TICKER" \
        --live \
        --starting-price weekly-open \
        --num-paths 500 \
        --tolerance 0.01 \
        --forecast-horizon-minutes 10080 \
        --update-interval 60 \
        --history-days 30
    
else
    # Traditional mode
    OUTPUT_FILE=${3:-output/forecast.png}
    
    echo "Running traditional simulation..."
    echo "Output will be saved to: $OUTPUT_FILE"
    echo ""
    
    docker run --rm \
        -v "$(pwd)/output:/app/output" \
        gbm-simulator \
        python -m gbm.cli "$TICKER" \
        --output "/app/output/$(basename $OUTPUT_FILE)" \
        --no-plot
    
    echo ""
    echo "✓ Simulation complete!"
    echo "Chart saved to: $OUTPUT_FILE"
    echo ""
    echo "To view the chart:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  open $OUTPUT_FILE"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  xdg-open $OUTPUT_FILE"
    else
        echo "  Open $OUTPUT_FILE in your image viewer"
    fi
fi

