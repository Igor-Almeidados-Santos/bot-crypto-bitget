import pytest
import pandas as pd
import numpy as np
import asyncio
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
async def settings(): # Fixture assíncrona
    settings_manager = await SettingsManager() # Usa await
    settings_manager.settings = Settings(order_size=1, slippage=0.001, commission=0.0005, take_profit_percent=1.0, stop_loss_percent=1.0)
    return settings_manager # Retorna o settings_manager

@pytest.fixture
async def backtester(sample_ohlcv, settings): # Fixture assíncrona
    settings_instance = await settings # Aguarda a fixture settings
    return Backtester(sample_ohlcv, settings_instance)

class TestBacktester:
    @pytest.mark.asyncio
    async def test_initialization(self, sample_ohlcv, settings):
        settings_instance = await settings
        bt = Backtester(sample_ohlcv, settings_instance) # Usa settings_instance
        assert len(bt.data) == 3
        assert 'datetime' in bt.data.columns
            
        # Teste com dados inválidos (faltando coluna)
        invalid_data = [[1625097600000, 30000, 31000, 29500, 30500, 1000]] * 3 # Dados com a estrutura correta
        invalid_data[0].pop() # Remove o volume do primeiro candle
        with pytest.raises(ValueError):
            Backtester(invalid_data, settings_instance)

    @pytest.mark.asyncio
    async def test_run(self, backtester, settings): # Adiciona settings como argumento
        settings_instance = await settings
        with patch('backtester.TradingStrategy') as MockStrategy:
            # Configura mock de sinais
            mock_strategy = MagicMock()
            mock_strategy.signal = 'strong_buy'
            MockStrategy.return_value = mock_strategy
            
            results = backtester.run(strategy_class=MockStrategy) # Passa MockStrategy para run
            
            # Verifica se os trades foram registrados
            # Verifica se backtester.run() retorna as métricas
            assert isinstance(results, dict)
            assert "total_trades" in results

    @pytest.mark.asyncio
    async def test_analyze_results(self, backtester, settings): # Adiciona settings como argumento
        settings_instance = await settings
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

    @pytest.mark.asyncio
    async def test_plot_results(self, backtester, settings): # Adiciona settings como argumento
        settings_instance = await settings
        with patch('backtester.mpf.plot') as mock_plot:
            backtester.results = [{'datetime': pd.Timestamp.now(), 'pnl': 100}]
            backtester.plot_results()
            mock_plot.assert_called_once()

    @pytest.mark.asyncio
    async def test_helper_methods(self, backtester, settings): # Adiciona settings como argumento
        settings_instance = await settings
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

    @pytest.mark.asyncio
    async def test_edge_cases(self, settings):
        settings_instance = await settings
        # Teste com dados mínimos
        minimal_data = [
            [1625097600000, 30000, 30000, 30000, 30000, 1000]
        ] * 100  # 100 candles idênticos

        bt = Backtester(minimal_data, settings_instance) # Usa settings_instance
        bt.run()
        assert bt.metrics['total_trades'] == 0  # sem sinais