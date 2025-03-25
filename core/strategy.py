import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from loguru import logger
from config.settings import SettingsManager  # Importa configurações dinâmicas
from typing import Dict, List, Tuple, Union
from enum import Enum


class TradingSignal(Enum):
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"
    HOLD = "hold"

class TradingStrategy:
    def __init__(self, ohlcv: List[List[Union[int, float]]], settings: 'Settings'):
        self.settings = settings
        self.data = pd.DataFrame(
            ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'], unit='ms')
        self.data.set_index('timestamp', inplace=True) # Define timestamp como índice
        self.rsi = self.calculate_rsi()
        self.macd_line, self.signal_line, self.macd_histogram = self.calculate_macd()
        self.signal: TradingSignal = self.generate_signal() # Adiciona type hint
        self.stop_loss_price: float = self.calculate_stop_loss_price() # Calcula o preço de stop loss

    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """Calcula RSI manualmente."""
        delta = self.data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD manualmente."""
        fast_ema = self.data['close'].ewm(span=fast, adjust=False).mean()
        slow_ema = self.data['close'].ewm(span=slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram


    def generate_signal(self) -> TradingSignal:
        """Gera sinal de trade."""
        if len(self.data) < 30:
            return TradingSignal.HOLD
        
        rsi_buy = self.rsi.iloc[-1] < self.settings.rsi_buy
        rsi_sell = self.rsi.iloc[-1] > self.settings.rsi_sell

        macd_cross_up = (
            self.macd_line.iloc[-2] < self.signal_line.iloc[-2] and
            self.macd_line.iloc[-1] > self.signal_line.iloc[-1]
        )
        macd_cross_down = (
            self.macd_line.iloc[-2] > self.signal_line.iloc[-2] and
            self.macd_line.iloc[-1] < self.signal_line.iloc[-1]
        )

        if rsi_buy and macd_cross_up:
            return TradingSignal.STRONG_BUY
        elif rsi_sell and macd_cross_down:
            return TradingSignal.STRONG_SELL
        else:
            return TradingSignal.HOLD

    def calculate_stop_loss_price(self) -> float:
        if self.signal == TradingSignal.STRONG_BUY:
            return self.data['close'].iloc[-1] * (1 - self.settings.stop_loss_percent / 100)
        elif self.signal == TradingSignal.STRONG_SELL:
            return self.data['close'].iloc[-1] * (1 + self.settings.stop_loss_percent / 100)
        else:
            return 0.0