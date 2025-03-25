import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from main import main
from config.settings import Settings, SettingsManager
from utils.notifier import Notifier
from core.api_connector import BitgetAPIConnector
from core.strategy import TradingStrategy

# Mocks
@pytest.fixture
def mock_settings():
    settings_manager = SettingsManager()
    settings_manager.settings = Settings()
    return settings_manager

@pytest.fixture
def mock_notifier():
    notifier = AsyncMock(Notifier)
    notifier.bot_running = True
    notifier.lock = asyncio.Lock()
    return notifier

@pytest.fixture
def mock_api_connector():
    api = AsyncMock(BitgetAPIConnector)
    api.exchange = MagicMock()
    api.exchange.fetch_ohlcv = AsyncMock(return_value=[[1, 2, 3, 4, 5, 6]] * 100)
    return api

@pytest.fixture
def mock_position_manager():
    position_manager = AsyncMock(PositionManager)
    position_manager.risk_manager = MagicMock()
    position_manager.risk_manager.calculate_position_size = MagicMock(return_value=(1, 1))
    return position_manager

@pytest.fixture
def mock_strategy():
    strategy = MagicMock(TradingStrategy)
    strategy.signal = "strong_buy"
    strategy.stop_loss_price = 1
    return strategy

# Testes
@pytest.mark.asyncio
async def test_main_dry_run(
    mock_settings, mock_notifier, mock_api_connector, mock_position_manager, mock_strategy, monkeypatch
):
    with patch('core.strategy.TradingStrategy', return_value=mock_strategy), \
        patch('utils.logger.PositionManager', return_value=mock_position_manager), \
        patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:

        mock_sleep.side_effect = KeyboardInterrupt  # Simula interrupção do teclado
        with pytest.raises(KeyboardInterrupt):
            await main(dry_run=True)

        mock_api_connector.create_order.assert_not_called() # Verifica se create_order não foi chamado em modo dry_run
        mock_notifier.send_telegram.assert_awaited() # Verifica se send_telegram foi chamado
        mock_position_manager.open_position.assert_awaited() # Verifica se open_position foi chamado
        mock_position_manager.manage_positions.assert_awaited() # Verifica se manage_positions foi chamado

@pytest.mark.asyncio
async def test_main_live(
    mock_settings, mock_notifier, mock_api_connector, mock_position_manager, mock_strategy, monkeypatch
):
    with patch('core.strategy.TradingStrategy', return_value=mock_strategy), \
        patch('utils.logger.PositionManager', return_value=mock_position_manager), \
        patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:

        mock_sleep.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            await main(dry_run=False)

        mock_api_connector.create_order.assert_not_called() # create_order não deve ser chamado diretamente no main
        mock_notifier.send_telegram.assert_awaited()
        mock_position_manager.open_position.assert_awaited()
        mock_position_manager.manage_positions.assert_awaited()