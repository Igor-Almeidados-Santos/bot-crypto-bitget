import asyncio
from loguru import logger
from core.risk_manager import RiskManager

class PositionManager:
    def __init__(self, api, settings):
        self.api = api
        self.settings = settings
        self.open_positions: Dict[str, Dict[str, Union[str, float]]] = {} # Type hint
        self.balance_task = asyncio.create_task(self.api.exchange.fetch_balance()) # Agenda a tarefa para obter o saldo
        self.risk_manager = RiskManager(settings_manager=settings, balance=0, symbol=settings.symbol) # Initialize RiskManager com saldo 0

    def get_balance(self):
        try:
            balance = asyncio.run(self.api.exchange.fetch_balance())
            return balance['total']['USDT']
        except Exception as e:
            logger.error(f"Erro ao obter saldo: {e}")
            return 0.0
        
    async def open_position(self, symbol, side, quantity, entry_price):
        try:
            order = await self.api.create_order(symbol, side, quantity) # Remove stopLossPrice
            self.open_positions[symbol] = {
                "side": side,
                "entry_price": entry_price,
                "quantity": quantity,
                "order_id": order['id'],
                "take_profit_price": self.calculate_take_profit(side, entry_price), # Add take-profit
                "stop_loss_price": self.calculate_stop_loss(side, entry_price) # Add stop-loss
            }
            logger.info(f"Posição aberta: {self.open_positions[symbol]}")
            return order
        except Exception as e:
            logger.error(f"Erro ao abrir posição: {e}")
            return None

    async def manage_positions(self):
        await self.update_risk_management() # Update balance before managing positions

        for symbol, position in list(self.open_positions.items()): # Iterate over a copy to allow modification
            try:
                current_price = await self.api.get_current_price(symbol) # await current price
                if current_price is None:
                    logger.error(f"Erro ao obter o preço atual para {symbol}")
                    continue

                if position['side'] == 'buy':
                    if current_price >= position['take_profit_price']:
                        logger.info(f"Take profit atingido para {symbol} em {current_price}. Fechando posição.")
                        await self.close_position(symbol, position)
                    elif current_price <= position['stop_loss_price']:
                        logger.info(f"Stop loss atingido para {symbol} em {current_price}. Fechando posição.")
                        await self.close_position(symbol, position)

                elif position['side'] == 'sell': # Corrected side check
                    if current_price <= position['take_profit_price']:
                        logger.info(f"Take profit atingido para {symbol} em {current_price}. Fechando posição.")
                        await self.close_position(symbol, position)
                    elif current_price >= position['stop_loss_price']:
                        logger.info(f"Stop loss atingido para {symbol} em {current_price}. Fechando posição.")
                        await self.close_position(symbol, position)
            except Exception as e:
                logger.exception(f"Erro ao gerenciar posição para {symbol}:") # Captura o traceback

    async def update_risk_management(self):
        """Updates the risk manager with the current balance."""
        self.risk_manager.balance = self.get_balance()

    def calculate_take_profit(self, side: str, entry_price: float) -> float:
        """Calculates the take-profit price based on the entry price and settings."""
        if side == 'buy':
            return entry_price * (1 + self.settings.take_profit_percent / 100)
        else:
            return entry_price * (1 - self.settings.take_profit_percent / 100)

    def calculate_stop_loss(self, side: str, entry_price: float) -> float:
        """Calculates the stop-loss price based on the entry price and settings."""
        if side == 'buy':
            return entry_price * (1 - self.settings.stop_loss_percent / 100)
        else:
            return entry_price * (1 + self.settings.stop_loss_percent / 100)
    
    async def close_position(self, symbol, position):
        try:
            order = await self.api.close_position(symbol, position)
            del self.open_positions[symbol] # Remove the position after closing
            logger.info(f"Posição fechada: {position}")
            return order
        except Exception as e:
            logger.exception("Erro ao fechar posição:") # Captura o traceback
            return None

