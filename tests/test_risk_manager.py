import pytest
from core.risk_manager import RiskManager

def test_position_size_calculation():
    """Testa cálculo de tamanho de posição com valores conhecidos."""
    risk_manager = RiskManager(balance=10000, symbol='BTC/USDT:USDT')
    
    # Valores de entrada
    entry_price = 60000
    stop_loss_price = 58800  # 2% abaixo
    
    # Cálculo esperado:
    # Risco por trade: 10000 * 1% = 100
    # Delta: 60000 - 58800 = 1200
    # Quantidade: (100 / 1200) * 10 (alavancagem) = 0.83333
    quantity, risk = risk_manager.calculate_position_size(entry_price, stop_loss_price)
    
    assert pytest.approx(quantity, 0.0001) == 0.83333
    assert risk == 100

def test_stop_loss_validation_valid():
    """Testa validação de stop-loss dentro do limite."""
    risk_manager = RiskManager(balance=10000, symbol='BTC/USDT:USDT')
    assert risk_manager.validate_stop_loss(60000, 59400)  # 1% de distância

def test_stop_loss_validation_invalid():
    """Testa validação de stop-loss fora do limite (>=10%)."""
    risk_manager = RiskManager(balance=10000, symbol='BTC/USDT:USDT')
    # 54000 é exatamente 10% abaixo de 60000 → inválido
    assert not risk_manager.validate_stop_loss(60000, 54000)


def test_zero_risk_handling():
    """Testa cálculo com risco zero (saldo insuficiente)."""
    risk_manager = RiskManager(balance=0, symbol='BTC/USDT:USDT')
    quantity, risk = risk_manager.calculate_position_size(60000, 58800)
    assert quantity == 0
    assert risk == 0

def test_negative_prices():
    """Testa tratamento de preços negativos (inválidos)."""
    risk_manager = RiskManager(balance=10000, symbol='BTC/USDT:USDT')
    # Agora deve retornar False em vez de lançar exceção
    assert not risk_manager.validate_stop_loss(-60000, 58800)
    
def test_negative_prices_in_position():
    """Testa cálculo de posição com preços negativos."""
    risk_manager = RiskManager(balance=10000, symbol='BTC/USDT:USDT')
    quantity, risk = risk_manager.calculate_position_size(-60000, 58800)
    assert quantity == 0
    assert risk == 0    