"""
Tests for the Geometric Brownian Motion model.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from gbm.model import GBM


class TestGBM:
    """Test suite for the GBM class."""
    
    @pytest.fixture
    def sample_stock_data(self):
        """Create sample stock price data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        return pd.DataFrame({
            'Close': prices,
            'Open': prices * 0.99,
            'High': prices * 1.01,
            'Low': prices * 0.98,
            'Volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)
    
    @pytest.fixture
    def gbm_instance(self):
        """Create a GBM instance for testing."""
        return GBM(
            stock_ticker='TEST',
            history_period='100d',
            forecast_period=252,
            seed=42
        )
    
    @patch('gbm.model.yf.Ticker')
    def test_fetch_prices_success(self, mock_ticker, gbm_instance, sample_stock_data):
        """Test successful price fetching."""
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = sample_stock_data
        mock_ticker.return_value = mock_ticker_instance
        
        stock_price, int_period = gbm_instance.fetch_prices()
        
        assert stock_price is not None
        assert len(stock_price) > 0
        assert int_period == 100
        assert gbm_instance.stock_price is not None
    
    @patch('gbm.model.yf.Ticker')
    def test_fetch_prices_empty_data(self, mock_ticker, gbm_instance):
        """Test handling of empty stock data."""
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance
        
        with pytest.raises(ValueError, match="No data found"):
            gbm_instance.fetch_prices()
    
    @patch('gbm.model.yf.Ticker')
    def test_fetch_prices_invalid_ticker(self, mock_ticker, gbm_instance):
        """Test handling of invalid ticker."""
        mock_ticker.side_effect = Exception("Ticker not found")
        
        with pytest.raises(ValueError, match="Error fetching data"):
            gbm_instance.fetch_prices()
    
    def test_calculate_mu_sigma(self, gbm_instance, sample_stock_data):
        """Test calculation of mu and sigma."""
        gbm_instance.stock_price = sample_stock_data.copy()
        gbm_instance.int_of_history_period = 100
        
        stock_price, mu, sigma = gbm_instance.calculate_mu_sigma()
        
        assert mu is not None
        assert sigma is not None
        assert isinstance(mu, (int, float))
        assert isinstance(sigma, (int, float))
        assert sigma >= 0  # Volatility should be non-negative
        assert 'Daily return' in stock_price.columns
    
    def test_calculate_mu_sigma_no_data(self, gbm_instance):
        """Test that calculate_mu_sigma raises error when no data."""
        with pytest.raises(ValueError, match="Stock price data not available"):
            gbm_instance.calculate_mu_sigma()
    
    def test_brownian_motion(self, gbm_instance):
        """Test Brownian motion generation."""
        W = gbm_instance.brownian_motion()
        
        assert W is not None
        assert len(W) == gbm_instance.forecast_period
        assert isinstance(W, np.ndarray)
        assert gbm_instance.W is not None
    
    def test_brownian_motion_reproducibility(self, gbm_instance):
        """Test that Brownian motion is reproducible with same seed."""
        gbm1 = GBM('TEST', seed=42, forecast_period=100)
        gbm2 = GBM('TEST', seed=42, forecast_period=100)
        
        W1 = gbm1.brownian_motion()
        W2 = gbm2.brownian_motion()
        
        np.testing.assert_array_equal(W1, W2)
    
    def test_geometric_brownian_motion(self, gbm_instance, sample_stock_data):
        """Test GBM price calculation."""
        gbm_instance.stock_price = sample_stock_data.copy()
        gbm_instance.int_of_history_period = 100
        gbm_instance.mu = 0.1
        gbm_instance.sigma = 0.2
        gbm_instance.brownian_motion()
        
        S, x_axis = gbm_instance.geometric_brownian_motion()
        
        assert S is not None
        assert len(S) == gbm_instance.forecast_period + 1
        assert len(x_axis) == gbm_instance.forecast_period + 1
        assert S[0] == gbm_instance.So  # First price should be initial price
        assert all(s > 0 for s in S)  # All prices should be positive
        assert gbm_instance.S is not None
        assert gbm_instance.x_axis is not None
    
    def test_geometric_brownian_motion_missing_data(self, gbm_instance):
        """Test that GBM raises error when data is missing."""
        with pytest.raises(ValueError, match="Stock price data not available"):
            gbm_instance.geometric_brownian_motion()
    
    def test_geometric_brownian_motion_missing_mu_sigma(self, gbm_instance, sample_stock_data):
        """Test that GBM raises error when mu/sigma not calculated."""
        gbm_instance.stock_price = sample_stock_data.copy()
        gbm_instance.int_of_history_period = 100
        
        with pytest.raises(ValueError, match="Mu and sigma not calculated"):
            gbm_instance.geometric_brownian_motion()
    
    @patch('gbm.model.plt.show')
    @patch('gbm.model.plt.figure')
    @patch('gbm.model.plt.plot')
    @patch('gbm.model.plt.legend')
    @patch('gbm.model.plt.ylabel')
    @patch('gbm.model.plt.xlabel')
    @patch('gbm.model.plt.title')
    @patch('gbm.model.plt.grid')
    def test_plot(
        self,
        mock_grid,
        mock_title,
        mock_xlabel,
        mock_ylabel,
        mock_legend,
        mock_plot,
        mock_figure,
        mock_show,
        gbm_instance,
        sample_stock_data
    ):
        """Test plotting functionality."""
        gbm_instance.stock_price = sample_stock_data.copy()
        gbm_instance.int_of_history_period = 100
        gbm_instance.S = [100.0] * 253
        gbm_instance.x_axis = np.linspace(100, 352, 253)
        
        gbm_instance.plot(show_plot=True)
        
        mock_figure.assert_called_once()
        assert mock_plot.call_count == 2  # Actual and forecast
        mock_legend.assert_called_once()
        mock_show.assert_called_once()
    
    @patch('gbm.model.plt.savefig')
    @patch('gbm.model.plt.close')
    def test_plot_save_output(self, mock_close, mock_savefig, gbm_instance, sample_stock_data):
        """Test saving plot to file."""
        gbm_instance.stock_price = sample_stock_data.copy()
        gbm_instance.int_of_history_period = 100
        gbm_instance.S = [100.0] * 253
        gbm_instance.x_axis = np.linspace(100, 352, 253)
        
        gbm_instance.plot(output_path='test.png', show_plot=False)
        
        mock_savefig.assert_called_once_with('test.png', dpi=300, bbox_inches='tight')
        mock_close.assert_called_once()
    
    def test_plot_missing_data(self, gbm_instance):
        """Test that plot raises error when data is missing."""
        with pytest.raises(ValueError, match="Forecasted prices not available"):
            gbm_instance.plot()
    
    @patch('gbm.model.yf.Ticker')
    @patch('gbm.model.plt.show')
    def test_run_complete_pipeline(self, mock_show, mock_ticker, gbm_instance, sample_stock_data):
        """Test the complete run pipeline."""
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = sample_stock_data
        mock_ticker.return_value = mock_ticker_instance
        
        gbm_instance.run(show_plot=True)
        
        assert gbm_instance.stock_price is not None
        assert gbm_instance.mu is not None
        assert gbm_instance.sigma is not None
        assert gbm_instance.W is not None
        assert gbm_instance.S is not None
        mock_show.assert_called_once()
    
    def test_gbm_initialization(self):
        """Test GBM initialization with default and custom parameters."""
        # Test with defaults
        gbm1 = GBM('MSFT')
        assert gbm1.stock_ticker == 'MSFT'
        assert gbm1.history_period == '100d'
        assert gbm1.forecast_period == 252
        assert gbm1.seed == 20
        
        # Test with custom parameters
        gbm2 = GBM('AMZN', history_period='200d', forecast_period=500, seed=42)
        assert gbm2.stock_ticker == 'AMZN'
        assert gbm2.history_period == '200d'
        assert gbm2.forecast_period == 500
        assert gbm2.seed == 42

