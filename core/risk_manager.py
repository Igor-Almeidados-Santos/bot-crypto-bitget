from loguru import logger
from config.settings import RISK_PER_TRADE, LEVERAGE

class RiskManager:
    def __init__(self, balance, symbol):
        """
        Args:
            balance (float): Saldo disponível na conta (ex.: USDT)
            symbol (str): Par de negociação (ex.: 'BTC/USDT:USDT')
        """
        self.balance = balance
        self.symbol = symbol

    def calculate_position_size(self, entry_price, stop_loss_price):
        """Calcula tamanho de posição com tratamento para preços iguais."""
        try:
            if entry_price <= stop_loss_price:
                logger.error("Preço de entrada não pode ser <= stop-loss")
                return 0, 0
            
            risk_amount = self.balance * RISK_PER_TRADE
            delta_price = entry_price - stop_loss_price
            quantity = (risk_amount / delta_price) * LEVERAGE
            
            return quantity, risk_amount
        except ZeroDivisionError:
            logger.error("Stop-loss igual ao preço de entrada (divisão por zero)")
            return 0, 0
        except Exception as e:
            logger.error(f"Erro no cálculo de risco: {e}")
            return 0, 0

    def validate_stop_loss(self, current_price, stop_loss_price):
        """Valida se o stop-loss está dentro de parâmetros seguros."""
        try:
            if current_price <= 0 or stop_loss_price <= 0:
                logger.error("Preços não podem ser negativos ou zero")
                return False
            
            price_diff = abs(current_price - stop_loss_price)
            if (price_diff / current_price) >= 0.10:  # Corrigido para >= 10%
                logger.warning("Stop-loss muito distante (>=10% do preço atual)")
                return False
            return True
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return False