import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from loguru import logger

class TradingStrategy:
    def __init__(self, historical_data):
        """
        Args:
            historical_data (list): Dados históricos no formato OHLCV (Open, High, Low, Close, Volume)
        """
        self.data = pd.DataFrame(historical_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.data['close'] = self.data['close'].astype(float)

    def calculate_rsi(self, period=14):
        """Calcula o RSI (Relative Strength Index)."""
        rsi_indicator = RSIIndicator(self.data['close'], window=period)
        self.data['rsi'] = rsi_indicator.rsi()
        return self.data['rsi'].iloc[-1]  # Retorna o último valor do RSI

    def calculate_macd(self, fast=12, slow=26, signal=9):
        """Calcula o MACD (Moving Average Convergence Divergence)."""
        macd_indicator = MACD(self.data['close'], window_slow=slow, window_fast=fast, window_sign=signal)
        self.data['macd'] = macd_indicator.macd()
        self.data['signal'] = macd_indicator.macd_signal()
        return self.data[['macd', 'signal']].iloc[-1]

    def generate_signal(self):
        """Gera sinais com tratamento adequado para MACD neutro."""
        try:
            latest_rsi = self.calculate_rsi()
            macd_values = self.calculate_macd()
            
            # Logs detalhados
            logger.debug(
                f"RSI: {latest_rsi:.2f} | MACD: {macd_values['macd']:.2f} | "
                f"Signal Line: {macd_values['signal']:.2f} | "
                f"Preço: {self.data['close'].iloc[-1]:.2f}"
            )
            
            # Lógica de RSI (zona neutra reduzida)
            rsi_signal = 'buy' if latest_rsi < 35 else 'sell' if latest_rsi > 65 else 'hold'
            
            # Lógica de MACD (corrigida para tratar igualdade)
            if macd_values['macd'] > macd_values['signal']:
                macd_signal = 'buy'
            elif macd_values['macd'] < macd_values['signal']:
                macd_signal = 'sell'
            else:
                macd_signal = 'hold'  # Trata MACD == Signal Line

            # Combina sinais com prioridade para RSI
            if rsi_signal == 'buy' or macd_signal == 'buy':
                return 'strong_buy'
            elif rsi_signal == 'sell' or macd_signal == 'sell':
                return 'strong_sell'
            else:
                return 'hold'

        except Exception as e:
            logger.error(f"Erro ao gerar sinal: {e}")
            return 'hold'