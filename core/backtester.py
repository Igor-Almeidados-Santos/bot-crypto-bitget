import pandas as pd
import numpy as np
from loguru import logger
from config.settings import SettingsManager
from core.strategy import TradingStrategy, TradingSignal
import mplfinance as mpf
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Union, Tuple
class Backtester:
    def __init__(
        self,
        historical_data: List[List[Union[int, float]]],
        settings_manager: 'SettingsManager',
        initial_balance: float = 10000,
        slippage: float = 0.001,
        commission: float = 0.0005
    ):
        self.data = pd.DataFrame(
            historical_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        self.data['datetime'] = pd.to_datetime(self.data['timestamp'], unit='ms')
        self.data.set_index('datetime', inplace=True) # Define datetime como índice
        
        # Valida dados históricos
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in historical_data[0] for col in required_columns):
            raise ValueError("Dados históricos incompletos")
        
        self.data = pd.DataFrame(
            historical_data,
            columns=required_columns
        )
        self.data['datetime'] = pd.to_datetime(self.data['timestamp'], unit='ms')
        self.settings_manager = settings_manager
        asyncio.run(self.settings_manager.load())
        self.settings = self.settings_manager.settings
        self.initial_balance = initial_balance
        self.slippage = slippage
        self.commission = commission
        self.results: List[Dict[str, Any]] = [] # Type hint
        self.metrics: Dict[str, Any] = {} # Type hint

    def run(self, strategy_class=TradingStrategy): # Aceita a classe da estratégia como parâmetro
        """Executa backtest completo com logs detalhados."""
        logger.info(" Iniciando backtest ".center(60, '-'))

        # Mostra amostra dos dados
        logger.debug(f"Dados carregados: {len(self.data)} candles")
        logger.debug(f"Primeiro candle: {self.data.iloc[0].to_dict()}")

        balance = self.initial_balance
        for i in range(30, len(self.data)): # Inicia após os primeiros 30 candles para indicadores
            current_data = self.data.iloc[:i+1].values.tolist() # Converte para lista para compatibilidade com TradingStrategy
            strategy = strategy_class(current_data, self.settings) # Usa a classe de estratégia fornecida

            if strategy.signal != TradingSignal.HOLD: # Usa TradingSignal.HOLD
                entry_price = self._apply_slippage(self.data['open'].iloc[i], strategy.signal) # Passa o sinal para aplicar slippage corretamente
                risk_amount = balance * self.settings.risk_per_trade
                quantity = self.settings.order_size # Utiliza order_size das configurações

                if strategy.signal == TradingSignal.STRONG_BUY:
                    stop_loss_price = strategy.calculate_stop_loss_price()
                    take_profit_price = self.data['close'].iloc[i] * (1 + self.settings.take_profit_percent / 100)
                elif strategy.signal == TradingSignal.STRONG_SELL:
                    stop_loss_price = strategy.calculate_stop_loss_price()
                    take_profit_price = self.data['close'].iloc[i] * (1 - self.settings.take_profit_percent / 100)
                else:
                    continue # Pula para o próximo candle se o sinal não for de compra ou venda forte

                exit_price, pnl = self._calculate_exit_price_and_pnl(
                    signal=strategy.signal,
                    entry=entry_price,
                    high=self.data['high'].iloc[i],
                    low=self.data['low'].iloc[i],
                    quantity=quantity,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price
                )

                balance += pnl # Atualiza o saldo

                self.results.append({
                    'datetime': self.data.index[i], # Usa o índice datetime
                    'signal': strategy.signal,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'balance': balance
                })

        return self.analyze_results()

    def analyze_results(self):
        """Calcula métricas de desempenho realistas."""
        if not self.results:
            logger.warning("Nenhum trade válido encontrado")
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'net_profit': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0 # Inicializa profit_factor como 0.0
            }

        df = pd.DataFrame(self.results)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] < 0])
        total_trades = len(df)

        net_profit = df['pnl'].sum()
        max_drawdown = (df['balance'].cummax() - df['balance']).max() # Calcula drawdown com base no saldo
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0 # Evita divisão por zero
        profit_factor = (df[df['pnl'] > 0]['pnl'].sum() / abs(df[df['pnl'] < 0]['pnl'].sum())) if losing_trades > 0 else float('inf') # Calcula profit factor

        self.metrics = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'net_profit': net_profit,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor
        }

        logger.info(f"Resultados do Backtest:")
        for metric, value in self.metrics.items():
            logger.info(f"- {metric}: {value}")

        return self.metrics


    def plot_results(self):
        """Plota os resultados do backtest."""

        if not self.results:
            logger.warning("Nenhum resultado para plotar.")
            return

        df_results = pd.DataFrame(self.results)
        df_results.set_index('datetime', inplace=True)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        # Plota o gráfico de velas
        mpf.plot(self.data, type='candle', style='yahoo', ax=ax1, volume=True)

        # Plota os sinais de compra e venda
        buy_signals = df_results[df_results['signal'] == TradingSignal.STRONG_BUY]
        sell_signals = df_results[df_results['signal'] == TradingSignal.STRONG_SELL]

        ax1.scatter(buy_signals.index, buy_signals['entry_price'], marker='^', color='green', s=100, label='Compra')
        ax1.scatter(sell_signals.index, sell_signals['entry_price'], marker='v', color='red', s=100, label='Venda')

        ax1.set_title('Backtest - Sinais de Trade')
        ax1.legend()

        # Plota a curva de equity
        ax2.plot(df_results['balance'], label='Equity', color='blue')
        ax2.set_title('Curva de Equity')
        ax2.legend()

        plt.show()


    def _apply_slippage(self, price: float, signal: TradingSignal) -> float:
        """Aplica slippage ao preço de entrada."""
        slippage_percentage = self.settings.slippage

        if signal == TradingSignal.STRONG_BUY:
            return price * (1 + slippage_percentage)
        elif signal == TradingSignal.STRONG_SELL:
            return price * (1 - slippage_percentage)
        else:
            return price

    def _calculate_exit_price_and_pnl(self, signal: TradingSignal, entry: float, high: float, low: float, quantity: float, stop_loss_price: float, take_profit_price: float) -> Tuple[float, float]:
        """Calcula o preço de saída e o PnL com base nos sinais de stop loss e take profit."""

        if signal == TradingSignal.STRONG_BUY:
            exit_price = take_profit_price if high >= take_profit_price else (stop_loss_price if low <= stop_loss_price else self.data['close'].iloc[-1])
            pnl = (exit_price - entry) * quantity - (exit_price + entry) * quantity * self.commission # Calcula o pnl com comissão

        elif signal == TradingSignal.STRONG_SELL:
            exit_price = take_profit_price if low <= take_profit_price else (stop_loss_price if high >= stop_loss_price else self.data['close'].iloc[-1])
            pnl = (entry - exit_price) * quantity - (exit_price + entry) * quantity * self.commission # Calcula o pnl com comissão

        else:
            exit_price = 0.0
            pnl = 0.0

        return exit_price, pnl