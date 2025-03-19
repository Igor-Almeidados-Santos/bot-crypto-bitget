import pytest
from core.api_connector import BitgetAPIConnector
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_exchange():
    """Mock da exchange Bitget."""
    with patch('core.api_connector.ccxt.bitget') as mock:
        yield mock

def test_fetch_ticker_success(mock_exchange):
    """Testa obtenção de ticker com sucesso."""
    mock_exchange.return_value.fetch_ticker.return_value = {
        'last': 60000,
        'high': 61000,
        'low': 59000,
        'symbol': 'BTC/USDT:USDT'
    }
    
    api = BitgetAPIConnector()  # Cria após o mock
    ticker = api.fetch_ticker('BTC/USDT:USDT')
    
    assert ticker['last'] == 60000
    mock_exchange.return_value.fetch_ticker.assert_called_once_with('BTC/USDT:USDT')

def test_fetch_ticker_failure(mock_exchange):
    """Testa falha na obtenção de ticker."""
    mock_exchange.return_value.fetch_ticker.side_effect = Exception("Erro de API")
    
    api = BitgetAPIConnector()
    ticker = api.fetch_ticker('BTC/USDT:USDT')
    
    assert ticker is None

def test_create_order_success(mock_exchange):
    """Testa criação de ordem com sucesso."""
    mock_exchange.return_value.create_order.return_value = {
        'id': '12345',
        'symbol': 'BTC/USDT:USDT',
        'side': 'buy',
        'amount': 0.001,
        'status': 'open'
    }
    
    api = BitgetAPIConnector()
    order = api.create_order('BTC/USDT:USDT', 'buy', 0.001)
    
    assert order['id'] == '12345'
    mock_exchange.return_value.create_order.assert_called_once_with(
        'BTC/USDT:USDT', 'market', 'buy', 0.001, 
        params={'positionType': 'cross'}  # Parâmetro obrigatório da Bitget
    )

def test_create_order_failure(mock_exchange):
    """Testa falha na criação de ordem."""
    mock_exchange.return_value.create_order.side_effect = Exception("Saldo insuficiente")
    
    api = BitgetAPIConnector()
    order = api.create_order('BTC/USDT:USDT', 'buy', 0.001)
    
    assert order is None