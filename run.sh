#!/bin/bash
# Quick run script for GBM simulator using Docker

set -e

# Default values
STOCK_TICKER=${1:-MSFT}
OUTPUT_FILE=${2:-output/forecast.png}

# Create output directory if it doesn't exist
mkdir -p output

echo "Running GBM simulation for $STOCK_TICKER..."
echo "Output will be saved to: $OUTPUT_FILE"

# Build image if it doesn't exist
if ! docker image inspect gbm-simulator >/dev/null 2>&1; then
    echo "Building Docker image..."
    docker build -t gbm-simulator .
fi

# Run the simulation
docker run --rm \
    -v "$(pwd)/output:/app/output" \
    gbm-simulator \
    python -m gbm.cli "$STOCK_TICKER" \
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

