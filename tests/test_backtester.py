import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from core.backtester import Backtester
from config.settings import Settings, SettingsManager

# Dados de teste OHLCV
@pytest.fixture
def sample_ohlcv():
    return [
        [1625097600000, 30000, 31000, 29500, 30500, 1000],
        [1625184000000, 30500, 31500, 30400, 31000, 1200],
        [1625270400000, 31000, 31500, 30800, 31200, 1500]
    ]

@pytest.fixture
def settings():
    settings_manager = SettingsManager()
    settings_manager.settings = Settings(order_size=1, slippage=0.001, commission=0.0005, take_profit_percent=1.0, stop_loss_percent=1.0) # Define order_size
    return settings_manager

@pytest.fixture
def backtester(sample_ohlcv, settings):
    return Backtester(
        historical_data=sample_ohlcv,
        settings=settings,
        initial_balance=10000,
        slippage=0.001,
        commission=0.0005
    )

class TestBacktester:
    def test_initialization(self, sample_ohlcv, settings):
        # Teste com dados válidos
        bt = Backtester(sample_ohlcv, settings)
        assert len(bt.data) == 3
        assert 'datetime' in bt.data.columns
        
        # Teste com dados inválidos (faltando coluna)
        invalid_data = [[1625097600000, 30000, 31000, 29500, 30500]]  # falta volume
        with pytest.raises(ValueError):
            Backtester(invalid_data, settings)

    def test_run(self, backtester):
        with patch('backtester.TradingStrategy') as MockStrategy:
            # Configura mock de sinais
            mock_strategy = MagicMock()
            mock_strategy.signal = 'strong_buy'
            MockStrategy.return_value = mock_strategy
            
            results = backtester.run()
            
            # Verifica se os trades foram registrados
            # Verifica se backtester.run() retorna as métricas
            assert isinstance(results, dict)
            assert "total_trades" in results

    def test_analyze_results(self, backtester):
        # Configura trades simulados
        backtester.results = [
            {'pnl': 100},
            {'pnl': -50},
            {'pnl': 200}
        ]
        
        metrics = backtester.analyze_results()
        assert metrics['total_trades'] == 3
        assert metrics['win_rate'] == (2/3)*100
        assert metrics['net_profit'] == 250
        assert metrics['profit_factor'] == (300 / 50)

    def test_plot_results(self, backtester):
        with patch('backtester.mpf.plot') as mock_plot:
            backtester.results = [{'datetime': pd.Timestamp.now(), 'pnl': 100}]
            backtester.plot_results()
            mock_plot.assert_called_once()

    def test_helper_methods(self, backtester):
        # Testa cálculo de slippage (compra)
        price = 100.0
        signal = TradingSignal.STRONG_BUY
        slipped_price = backtester._apply_slippage(price, signal)
        assert slipped_price == price * (1 + backtester.slippage)

        # Testa cálculo de slippage (venda)
        signal = TradingSignal.STRONG_SELL
        slipped_price = backtester._apply_slippage(price, signal)
        assert slipped_price == price * (1 - backtester.slippage)

        # Testa cálculo de PnL (compra)
        entry_price = 100.0
        exit_price = 110.0
        quantity = 1.0
        signal = TradingSignal.STRONG_BUY
        _, pnl = backtester._calculate_exit_price_and_pnl(signal, entry_price, exit_price + 1, exit_price -1, quantity, entry_price * 0.99, exit_price)
        expected_pnl = (exit_price - entry_price) * quantity - (exit_price + entry_price) * quantity * backtester.commission
        assert pnl == expected_pnl

        # Testa cálculo de PnL (venda)
        entry_price = 110.0
        exit_price = 100.0
        quantity = 1.0
        signal = TradingSignal.STRONG_SELL
        _, pnl = backtester._calculate_exit_price_and_pnl(signal, entry_price, exit_price + 1, exit_price - 1, quantity, entry_price * 1.01, exit_price)
        expected_pnl = (entry_price - exit_price) * quantity - (exit_price + entry_price) * quantity * backtester.commission
        assert pnl == expected_pnl

    def test_edge_cases(self, settings):
        # Teste com dados mínimos
        minimal_data = [
            [1625097600000, 30000, 30000, 30000, 30000, 1000]
        ] * 100  # 100 candles idênticos
        
        bt = Backtester(minimal_data, settings)
        bt.run()
        assert bt.metrics['total_trades'] == 0  # sem sinais