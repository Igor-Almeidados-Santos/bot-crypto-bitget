import asyncio
import pytest
from loguru import logger
from unittest.mock import AsyncMock, MagicMock, patch
from core.api_connector import BitgetAPIConnector
import ccxt.async_support as ccxt_async

@pytest.fixture
async def api(settings):
    settings_instance = await settings
    api_instance = BitgetAPIConnector(settings_instance)
    await api_instance.settings_manager.load()
    return api_instance

@pytest.mark.asyncio
async def test_fetch_ticker_success(api):
    api_instance = await api
    with patch.object(api_instance.exchange, 'fetch_ticker', new_callable=AsyncMock) as mock_fetch_ticker: # Patch na instância da exchange
        mock_fetch_ticker.return_value = {'last': 10}
        ticker = await api_instance.fetch_ticker('BTC/USDT:USDT')
        assert ticker['last'] == 10

@pytest.mark.asyncio
async def test_fetch_ticker_network_error(api):
    api_instance = await api
    with patch.object(api_instance.exchange, 'fetch_ticker', side_effect=ccxt_async.NetworkError): # Patch na instância da exchange
        ticker = await api.fetch_ticker('BTC/USDT:USDT')
        assert ticker is None

@pytest.mark.asyncio
async def test_fetch_ticker_generic_error(api):
    api_instance = await api
    with patch.object(api_instance.exchange, 'fetch_ticker', side_effect=Exception): # Patch na instância da exchange
        ticker = await api.fetch_ticker('BTC/USDT:USDT')
        assert ticker is None

@pytest.mark.asyncio
async def test_create_order_success(api):
    api_instance = await api
    with patch.object(api_instance.exchange, 'create_order', new_callable=AsyncMock) as mock_create: # Usa create_order
        mock_create.return_value = {'id': '123'}
        order = await api_instance.create_order("BTC/USDT", "buy", 0.001) # Remove price
        assert order['id'] == '123'

@pytest.mark.asyncio
async def test_create_order_insufficient_funds(api):
    api_instance = await api
    with patch.object(api_instance.exchange, 'create_order', side_effect=ccxt_async.InsufficientFunds): # Patch na instância da exchange
        with pytest.raises(ccxt_async.InsufficientFunds):
            await api.create_order('BTC/USDT:USDT', 'buy', 1)

@pytest.mark.asyncio
async def test_create_order_generic_error(api):
    api_instance = await api
    with patch.object(api_instance.exchange, 'create_order', side_effect=Exception): # Patch na instância da exchange
        order = await api.create_order('BTC/USDT:USDT', 'buy', 1)
        assert order is None

@pytest.mark.asyncio
async def test_close_position(api):
    api_instance = await api
    position = {'side': 'buy', 'quantity': 1}
    with patch.object(api_instance.exchange, 'create_order', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = "order_details"
        result = await api_instance.close_position("BTC/USDT", position)
        mock_create.assert_called_once_with("BTC/USDT", "market", "sell", 1, params={'reduceOnly': True})
        assert result == "order_details"

@pytest.mark.asyncio
async def test_get_current_price(api):
    with patch('core.api_connector.BitgetAPIConnector.fetch_ticker', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {'last': 12345}
        price = await api.get_current_price("BTC/USDT")
        assert price == 12345

        mock_fetch.return_value = None
        price = await api.get_current_price("BTC/USDT")
        assert price is None

@pytest.mark.asyncio
async def test_format_symbol(api):
    api_instance = await api # Aguarda a fixture api
    assert api.format_symbol("BTC/USDT:USDT") == "BTCUSDTUSDT"
    assert api.format_symbol("ETH/USD") == "ETHUSD"

@pytest.mark.asyncio
async def test_websocket_on_message(api):
    api_instance = await api # Aguarda a fixture api
    mock_ws = MagicMock()
    message = '{"data":[{"tradeId":"123"}]}'
    api_instance.on_message(mock_ws, message) # Chama o método diretamente

@pytest.mark.asyncio
async def test_websocket_on_close(api, event_loop): # Adiciona event_loop
    api_instance = await api # Aguarda a fixture api
    mock_ws = MagicMock()
    with patch.object(api.connected_event, 'clear') as mock_clear:
        api.on_close(mock_ws, 1000, "Test Close")
        mock_clear.assert_called_once()

@pytest.mark.asyncio
async def test_websocket_on_error(api, event_loop): # Adiciona event_loop
    api_instance = await api # Aguarda a fixture api

    mock_ws = MagicMock()
    with patch.object(logger, 'exception') as mock_log:
        api.on_error(mock_ws, Exception("Test Error"))
        mock_log.assert_called_once()

@pytest.mark.asyncio
async def test_websocket_on_open(api, event_loop): # Adiciona event_loop
    api_instance = await api # Aguarda a fixture api
    mock_ws = MagicMock()
    with patch.object(mock_ws, 'send') as mock_send:
        api.on_open(mock_ws)
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_set_connected_event(api, event_loop): # Adiciona event_loop
    api_instance = await api # Aguarda a fixture api
    with patch.object(api.connected_event, 'set') as mock_set:
        await api.set_connected_event()
        mock_set.assert_called_once()

@pytest.mark.asyncio
async def test_connect(api, event_loop): # Adiciona event_loop
    api_instance = await api # Aguarda a fixture api
    with patch('core.api_connector.BitgetAPIConnector.start_websocket') as mock_start_ws:
        with patch.object(api.connected_event, 'wait', new_callable=AsyncMock) as mock_wait:
            await api.connect()
            mock_start_ws.assert_called_once()
            mock_wait.assert_awaited_once()

@pytest.mark.asyncio
async def test_start_websocket(api, event_loop): # Adiciona event_loop
    api_instance = await api # Aguarda a fixture api
    with patch('threading.Thread') as mock_thread:
        api.start_websocket()
        mock_thread.assert_called_once()

@pytest.mark.asyncio
async def test_run_websocket(api, event_loop): # Adiciona event_loop
    api_instance = await api # Aguarda a fixture api
    with patch('websocket.WebSocketApp') as mock_ws_app:
        with patch.object(api, 'on_open'):
            with patch.object(logger, 'error'):
                try:
                    api.run_websocket()
                except Exception:
                    pass # Expected exception due to mock setup
                mock_ws_app.assert_called_once()
