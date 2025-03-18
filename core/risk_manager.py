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
        """
        Calcula o tamanho da posição com base no risco máximo por trade.
        
        Args:
            entry_price (float): Preço de entrada
            stop_loss_price (float): Preço do stop-loss
        
        Returns:
            tuple: (quantidade_crypto, valor_risco)
        """
        try:
            # Cálculo do risco em valor absoluto
            risk_amount = self.balance * RISK_PER_TRADE
            
            # Cálculo da quantidade de crypto com alavancagem
            delta_price = entry_price - stop_loss_price
            quantity = (risk_amount / delta_price) * LEVERAGE
            
            logger.info(f"Risco calculado: ${risk_amount:.2f} | Quantidade: {quantity:.5f} {self.symbol.split('/')[0]}")
            return quantity, risk_amount
        
        except Exception as e:
            logger.error(f"Erro no cálculo de risco: {e}")
            return 0, 0

    def validate_stop_loss(self, current_price, stop_loss_price):
        """Valida se o stop-loss está dentro de parâmetros seguros."""
        if abs(current_price - stop_loss_price) / current_price > 0.10:
            logger.warning("Stop-loss muito distante (>10% do preço atual)")
            return False
        return True