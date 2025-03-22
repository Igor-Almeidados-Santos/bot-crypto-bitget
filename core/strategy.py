import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from loguru import logger
from config.settings import SettingsManager  # Importa configurações dinâmicas

class TradingStrategy:
    def __init__(self, ohlcv, settings):
        self.settings = settings
        self.data = pd.DataFrame(
            ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'], unit='ms')
        self.rsi = self.calculate_rsi()
        self.macd_line, self.signal_line, self.macd_histogram = self.calculate_macd()
        
        # Gera sinal após calcular indicadores
        self.signal = self.generate_signal()

    def calculate_rsi(self, period=14):
        """Calcula RSI manualmente."""
        delta = self.data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, fast=12, slow=26, signal=9):
        """Calcula MACD manualmente."""
        fast_ema = self.data['close'].ewm(span=fast, adjust=False).mean()
        slow_ema = self.data['close'].ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def generate_signal(self):
        """Gera sinal de trade."""
        if len(self.data) < 30:
            return 'hold'
        
        rsi_buy = self.rsi.iloc[-1] < self.settings.rsi_buy_threshold
        rsi_sell = self.rsi.iloc[-1] > self.settings.rsi_sell_threshold

        macd_cross_up = (
            self.macd_line.iloc[-2] < self.signal_line.iloc[-2] and
            self.macd_line.iloc[-1] > self.signal_line.iloc[-1]
        )
        macd_cross_down = (
            self.macd_line.iloc[-2] > self.signal_line.iloc[-2] and
            self.macd_line.iloc[-1] < self.signal_line.iloc[-1]
        )

        if rsi_buy and macd_cross_up:
            return 'strong_buy'
        elif rsi_sell and macd_cross_down:
            return 'strong_sell'
        else:
            return 'hold'