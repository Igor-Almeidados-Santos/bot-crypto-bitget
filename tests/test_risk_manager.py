import pandas as pd
import pytest
from unittest.mock import patch
from config.settings import Settings, SettingsManager
from core.strategy import TradingStrategy, TradingSignal

@pytest.fixture
def settings():
    settings_manager = SettingsManager()
    settings_manager.settings = Settings(rsi_buy=30, rsi_sell=70, stop_loss_percent=1.0)
    return settings_manager.settings

@pytest.fixture
def sample_data():
    data = [
        [1678886400000, 45100.0, 45100.5, 45000.0, 45050.0, 1000],
        [1678972800000, 45050.0, 45200.0, 44900.0, 45150.0, 1200],
        [1679059200000, 45150.0, 45300.0, 45100.0, 45250.0, 1500]
    ]
    return data

def test_strong_buy_signal(sample_data, settings):
    with patch('core.strategy.TradingStrategy.calculate_rsi', return_value=pd.Series([25, 25, 25])), \
        patch('core.strategy.TradingStrategy.calculate_macd', return_value=(pd.Series([10, 15, 15]), pd.Series([15, 10, 10]), pd.Series([-5, 5, 5]))):

        strategy = TradingStrategy(sample_data, settings)
        assert strategy.generate_signal() == TradingSignal.STRONG_BUY

def test_strong_sell_signal(sample_data, settings):
    with patch('core.strategy.TradingStrategy.calculate_rsi', return_value=pd.Series([75, 75, 75])), \
        patch('core.strategy.TradingStrategy.calculate_macd', return_value=(pd.Series([10, 5, 5]), pd.Series([15, 10, 10]), pd.Series([-5, -5, -5]))):

        strategy = TradingStrategy(sample_data, settings)
        assert strategy.generate_signal() == TradingSignal.STRONG_SELL

def test_hold_signal(sample_data, settings):
    with patch('core.strategy.TradingStrategy.calculate_rsi', return_value=pd.Series([50, 50, 50])), \
        patch('core.strategy.TradingStrategy.calculate_macd', return_value=(pd.Series([10, 10, 10]), pd.Series([15, 10, 10]), pd.Series([-5, 0, 0]))):

        strategy = TradingStrategy(sample_data, settings)
        assert strategy.generate_signal() == TradingSignal.HOLD

def test_insufficient_data(sample_data, settings):
    """Testa sinal com dados insuficientes."""
    strategy = TradingStrategy(sample_data, settings)
    signal = strategy.generate_signal()
    assert signal == TradingSignal.HOLD

def test_calculate_stop_loss_price(sample_data, settings):
    with patch('core.strategy.TradingStrategy.calculate_rsi', return_value=pd.Series([25, 25, 25])), \
        patch('core.strategy.TradingStrategy.calculate_macd', return_value=(pd.Series([10, 15, 15]), pd.Series([15, 10, 10]), pd.Series([-5, 5, 5]))):

        strategy = TradingStrategy(sample_data, settings)
        assert strategy.calculate_stop_loss_price() == 44600.0

    with patch('core.strategy.TradingStrategy.calculate_rsi', return_value=pd.Series([75, 75, 75])), \
        patch('core.strategy.TradingStrategy.calculate_macd', return_value=(pd.Series([10, 5, 5]), pd.Series([15, 10, 10]), pd.Series([-5, -5, -5]))):

        strategy = TradingStrategy(sample_data, settings)
        assert strategy.calculate_stop_loss_price() == 45700.0

    with patch('core.strategy.TradingStrategy.calculate_rsi', return_value=pd.Series([50, 50, 50])), \
        patch('core.strategy.TradingStrategy.calculate_macd', return_value=(pd.Series([10, 10, 10]), pd.Series([15, 10, 10]), pd.Series([-5, 0, 0]))):

        strategy = TradingStrategy(sample_data, settings)
        assert strategy.calculate_stop_loss_price() == 0.0

