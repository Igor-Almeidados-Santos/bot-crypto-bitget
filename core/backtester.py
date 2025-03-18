import pandas as pd
import matplotlib.pyplot as plt
from loguru import logger
from core.strategy import TradingStrategy

class Backtester:
    def __init__(self, historical_data):
        self.data = pd.DataFrame(
            historical_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        self.data['datetime'] = pd.to_datetime(self.data['timestamp'], unit='ms')
        self.strategy = TradingStrategy(historical_data.copy())
        self.results = []

    def run(self):
        logger.info(" Iniciando backtest ".center(60, '-'))
        
        for i in range(100, len(self.data)):
            current_data = self.data.iloc[:i].copy()
            self.strategy.data = current_data
            signal = self.strategy.generate_signal()
            
            logger.debug(f"[{self.data.iloc[i]['datetime']}] Sinal gerado: {signal}")
            
            if signal != 'hold':
                entry_price = self.data.iloc[i]['close']
                stop_loss = entry_price * 0.95  # Ajustado para 5% de stop
                take_profit = entry_price * 1.10  # Ajustado para 10% de take-profit
                self.results.append({
                    'datetime': self.data.iloc[i]['datetime'],
                    'signal': signal,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                })
        
        return self.analyze_results()

    def analyze_results(self):
        if not self.results:
            logger.warning("Nenhum trade válido encontrado no backtest")
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'results': pd.DataFrame()
            }
        
        df = pd.DataFrame(self.results)
        required_columns = ['signal', 'entry_price', 'take_profit']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Coluna '{col}' não encontrada")
                return {'total_trades': 0, 'win_rate': 0.0, 'results': df}
        
        winning_trades = len(df[
            (df['signal'].str.contains('buy') & (df['take_profit'] > df['entry_price'])) |
            (df['signal'].str.contains('sell') & (df['take_profit'] < df['entry_price']))
        ])
        total_trades = len(df)
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        logger.info(f"Total de trades: {total_trades}")
        logger.info(f"Taxa de acerto: {win_rate:.2f}%")
        return {'total_trades': total_trades, 'win_rate': win_rate, 'results': df}

    def plot_results(self):
        df = pd.DataFrame(self.results)
        if df.empty:
            logger.warning("Nenhum dado para plotar")
            return
        
        plt.figure(figsize=(14, 7))
        plt.plot(self.data['datetime'], self.data['close'], label='Preço', alpha=0.5)
        
        if 'strong_buy' in df['signal'].values:
            plt.scatter(
                df[df['signal'] == 'strong_buy']['datetime'],
                df[df['signal'] == 'strong_buy']['entry_price'],
                label='Compra Forte',
                marker='^',
                color='green',
                s=100
            )
        
        if 'strong_sell' in df['signal'].values:
            plt.scatter(
                df[df['signal'] == 'strong_sell']['datetime'],
                df[df['signal'] == 'strong_sell']['entry_price'],
                label='Venda Forte',
                marker='v',
                color='red',
                s=100
            )
        
        plt.title('Backtest - Sinais de Trade')
        plt.xlabel('Data')
        plt.ylabel('Preço')
        plt.legend()
        plt.grid(True)
        plt.show()