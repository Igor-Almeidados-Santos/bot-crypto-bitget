import asyncio

from loguru import logger
from config.settings import SettingsManager

class RiskManager:
    def __init__(self, settings_manager: SettingsManager, balance, symbol):  # Recebe settings_manager
        """
        Args:
            balance (float): Saldo disponível na conta (ex.: USDT)
            symbol (str): Par de negociação (ex.: 'BTC/USDT:USDT')
        """
        self.balance = balance
        self.symbol = symbol
        self.settings_manager = settings_manager
        self.settings = self.settings_manager.settings
        
    def calculate_position_size(self, entry_price, stop_loss_price):
        """Calcula tamanho de posição com parâmetros dinâmicos."""
        risk_amount = self.balance * self.settings.risk_per_trade  # Usa settings
        delta_price = abs(entry_price - stop_loss_price)
        quantity = (risk_amount / delta_price) * self.settings.leverage  # Usa settings
        return quantity, risk_amount

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