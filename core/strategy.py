import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from loguru import logger

class TradingStrategy:
    def __init__(self, historical_data):
        self.data = pd.DataFrame(
            historical_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        self.data['close'] = self.data['close'].astype(float)

    def calculate_rsi(self, period=14):
        rsi_indicator = RSIIndicator(self.data['close'], window=period)
        self.data['rsi'] = rsi_indicator.rsi()
        latest_rsi = self.data['rsi'].iloc[-1]
        logger.debug(f"RSI Calculado: {latest_rsi:.2f}")
        return latest_rsi

    def calculate_macd(self, fast=12, slow=26, signal=9):
        macd_indicator = MACD(
            self.data['close'],
            window_slow=slow,
            window_fast=fast,
            window_sign=signal
        )
        self.data['macd'] = macd_indicator.macd()
        self.data['signal'] = macd_indicator.macd_signal()
        latest_macd = self.data['macd'].iloc[-1]
        latest_signal = self.data['signal'].iloc[-1]
        logger.debug(f"MACD: {latest_macd:.2f} | Signal: {latest_signal:.2f}")
        return {'macd': latest_macd, 'signal': latest_signal}

    def generate_signal(self):
        """Gera sinais com critérios ajustados para maior sensibilidade."""
        try:
            latest_rsi = self.calculate_rsi()
            macd_values = self.calculate_macd()

            # Lógica de RSI (ajustada para 40-60)
            rsi_signal = 'buy' if latest_rsi < 40 else 'sell' if latest_rsi > 60 else 'hold'

            # Lógica de MACD (crossover simplificado)
            macd_crossover = macd_values['macd'] > macd_values['signal']
            macd_signal = 'buy' if macd_crossover else 'sell'

            # Combina sinais usando OR ao invés de AND
            if rsi_signal == 'buy' or macd_signal == 'buy':
                return 'strong_buy'
            elif rsi_signal == 'sell' or macd_signal == 'sell':
                return 'strong_sell'
            else:
                return 'hold'

        except Exception as e:
            logger.error(f"Erro ao gerar sinal: {e}")
            return 'hold'