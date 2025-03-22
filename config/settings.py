import json
import os
from loguru import logger
from decouple import config
from threading import Lock as ThreadLock  # Lock para __new__
from asyncio import Lock as AsyncLock

SYMBOL = config('SYMBOL', default='BTC/USDT:USDT')
TIMEFRAME = config('TIMEFRAME', default='1m')
RISK_PER_TRADE = config('RISK_PER_TRADE', cast=float, default=0.01)  # 1% de risco
LEVERAGE = config('LEVERAGE', cast=int, default=10)  # Alavancagem padrão

class SettingsManager:
    _instance = None
    _lock = ThreadLock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    # Inicializa atributos mínimos antes do __init__
                    cls._instance.file_path = 'settings.json'  # Define file_path primeiro
                    cls._instance.lock = AsyncLock()
        return cls._instance

    def __init__(self):
        # Garante que os atributos só sejam inicializados uma vez
        if not hasattr(self, 'initialized'):
            self.rsi_buy_threshold = 35
            self.rsi_sell_threshold = 65
            self.macd_fast = 12
            self.macd_slow = 26
            self.macd_signal = 9
            self.risk_per_trade = 0.01
            self.leverage = 10
            self.initialized = True
            self.lock = AsyncLock()

    async def load(self):
        """Carrega configurações com lock assíncrono."""
        async with self.lock:
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    self.rsi_buy_threshold = data.get('rsi_buy', 35)
                    self.rsi_sell_threshold = data.get('rsi_sell', 65)
                    self.macd_fast = data.get('macd_fast', 12)
                    self.macd_slow = data.get('macd_slow', 26)
                    self.macd_signal = data.get('macd_signal', 9)
                    self.risk_per_trade = data.get('risk_per_trade', 0.01)
                    self.leverage = data.get('leverage', 10)
            except Exception as e:
                logger.error(f"Erro ao carregar configurações: {e}")

    async def save(self):
        """Salva configurações com lock assíncrono."""
        async with self.lock:
            data = {
                'rsi_buy': self.rsi_buy_threshold,
                'rsi_sell': self.rsi_sell_threshold,
                'macd_fast': self.macd_fast,
                'macd_slow': self.macd_slow,
                'macd_signal': self.macd_signal,
                'risk_per_trade': self.risk_per_trade,
                'leverage': self.leverage
            }
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)