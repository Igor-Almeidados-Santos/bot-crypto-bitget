import pytest
import pandas as pd
from unittest.mock import patch
from core.strategy import TradingStrategy

@pytest.fixture
def sample_data():
    """Dados OHLCV sintéticos para testes."""
    return [
        [1710000000 + i*60000, 60000 - i*100, 60000, 59000, 60000 - i*100, 1000]
        for i in range(100)  # 100 candles em downtrend
    ]

def test_strong_buy_signal(sample_data):
    """Testa geração de sinal 'strong_buy'."""
    strategy = TradingStrategy(sample_data)
    
    # Mock correto para retornar dicionário
    with patch.object(strategy, 'calculate_rsi', return_value=30), \
         patch.object(strategy, 'calculate_macd', return_value={'macd': 15, 'signal': 10}):  # MACD > Signal
        
        signal = strategy.generate_signal()
        assert signal == 'strong_buy'

def test_strong_sell_signal(sample_data):
    """Testa geração de sinal 'strong_sell'."""
    strategy = TradingStrategy(sample_data)
    
    # Mock correto para retornar dicionário
    with patch.object(strategy, 'calculate_rsi', return_value=70), \
         patch.object(strategy, 'calculate_macd', return_value={'macd': 5, 'signal': 10}):  # MACD < Signal
        
        signal = strategy.generate_signal()
        assert signal == 'strong_sell'

def test_hold_signal(sample_data):
    """Testa geração de sinal 'hold'."""
    strategy = TradingStrategy(sample_data)
    
    # Mock correto para retornar dicionário
    with patch.object(strategy, 'calculate_rsi', return_value=50), \
         patch.object(strategy, 'calculate_macd', return_value={'macd': 10, 'signal': 10}):  # MACD == Signal
        
        signal = strategy.generate_signal()
        assert signal == 'hold'

def test_insufficient_data():
    """Testa sinal com dados insuficientes (mas estrutura válida)."""
    empty_data = [
        [0, 0.0, 0.0, 0.0, 0.0, 0.0]  # Dados vazios mas com 6 colunas
    ]
    strategy = TradingStrategy(empty_data)
    signal = strategy.generate_signal()
    assert signal == 'hold'