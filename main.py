import time
import argparse
from loguru import logger
from core.api_connector import BitgetAPIConnector
from core.strategy import TradingStrategy
from core.risk_manager import RiskManager
from core.backtester import Backtester
from utils.notifier import Notifier
from config.settings import SYMBOL, TIMEFRAME, LEVERAGE, RISK_PER_TRADE
from decouple import Config, RepositoryEnv

# Configuração de logs
logger.add("bot.log", rotation="500 MB", level="INFO")

config = Config(RepositoryEnv('.env'))

def main(dry_run=False):
    api = BitgetAPIConnector()
    notifier = Notifier()
    
    # Notificação de inicialização
    notifier.send_telegram("🤖 Bot iniciado em modo " + ("SIMULAÇÃO" if dry_run else "REAL"))
    
    # Define saldo fictício para simulação
    if dry_run:
        balance = 10000  # $10.000 para testes
        logger.info(" Modo simulação: Usando saldo fictício de $10.000 ".center(60, '-'))
    else:
        balance = api.fetch_balance()['total']['USDT']
        logger.info(f" Modo real: Usando saldo de ${balance:.2f} ".center(60, '-'))
    
    risk_manager = RiskManager(balance=balance, symbol=SYMBOL)
    
    while True:
        try:
            # 1. Obter dados históricos
            ohlcv = api.exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=100)
            strategy = TradingStrategy(ohlcv)
            signal = strategy.generate_signal()
            
            # 2. Gerar sinais e executar trades
            if signal != 'hold':
                ticker = api.fetch_ticker(SYMBOL)
                current_price = ticker['last']
                
                # 3. Calcular stop-loss e take-profit
                stop_loss_price = current_price * 0.98  # 2% abaixo
                take_profit_price = current_price * 1.05  # 5% acima
                
                # 4. Validar risco
                quantity, risk_amount = risk_manager.calculate_position_size(current_price, stop_loss_price)
                if risk_manager.validate_stop_loss(current_price, stop_loss_price):
                    # 5. Executar ordem (simulação ou real)
                    if not dry_run:
                        order = api.create_order(
                            SYMBOL,
                            side=signal.split('_')[0],
                            amount=quantity,
                            order_type='market'
                        )
                        notifier.send_telegram(
    f"🚀 TRADE EXECUTADO\n"
    f"Sinal: {signal}\n"
    f"Quantidade: {quantity:.5f} {SYMBOL.split('/')[0]}\n"  # Remove '/USDT:USDT'
    f"Preço: ${current_price:.2f}\n"
    f"Stop-Loss: ${stop_loss_price:.2f}\n"
    f"Take-Profit: ${take_profit_price:.2f}"
)
                        logger.success(f"Ordem executada: {order}")
                    else:
                        notifier.send_telegram(
    f"🚀 TRADE EXECUTADO\n"
    f"Sinal: {signal}\n"
    f"Quantidade: {quantity:.5f} {SYMBOL.split('/')[0]}\n"  # Remove '/USDT:USDT'
    f"Preço: ${current_price:.2f}\n"
    f"Stop-Loss: ${stop_loss_price:.2f}\n"
    f"Take-Profit: ${take_profit_price:.2f}"
)
                        logger.info(f"DRY RUN: Ordem simulada - {signal} {quantity} {SYMBOL}")
                else:
                    logger.warning("Trade ignorado: Stop-loss inválido")
                    notifier.send_telegram(f"⚠️ Trade Ignorado: Stop-loss inválido para {SYMBOL}")

            # Aguardar próximo ciclo
            time.sleep(60)  # 1 minuto (ajuste conforme timeframe)

        except Exception as e:
            error_msg = f"🚨 ERRO CRÍTICO: {str(e)}"
            logger.error(error_msg)
            notifier.send_telegram(error_msg)
            time.sleep(10)  # Reinicia após falha

def backtest_strategy(symbol, timeframe):
    """Executa backtest com tratamento de erros."""
    try:
        api = BitgetAPIConnector()
        historical_data = api.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=5000)
        
        if not historical_data:
            logger.error("Nenhum dado histórico retornado pela exchange")
            return
        
        backtester = Backtester(historical_data)
        results = backtester.run()
        
        if results['total_trades'] == 0:
            logger.warning("Nenhum trade foi executado no backtest")
            return
        
        backtester.plot_results()
        return results
    
    except Exception as e:
        logger.error(f"Falha no backtest: {str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help="Simular trades")
    parser.add_argument('--backtest', action='store_true', help="Executar backtest")
    args = parser.parse_args()

    if args.backtest:
        logger.info(" Executando backtest ".center(60, '='))
        backtest_results = backtest_strategy(SYMBOL, TIMEFRAME)
        if backtest_results:
            logger.info(f"Resultados do backtest: {backtest_results}")
    else:
        main(dry_run=args.dry_run)
    
    if backtest_results:
        backtest_results['results'].to_csv('backtest_results.csv', index=False)  # Salva CSV
        logger.info("Resultados salvos em backtest_results.csv")    

def test_env():
    try:
        print("BITGET_API_KEY:", config('BITGET_API_KEY'))
        print("BITGET_API_SECRET:", config('BITGET_API_SECRET'))
        print("BITGET_PASSPHRASE:", config('BITGET_PASSPHRASE'))
    except Exception as e:
        print("Erro ao carregar variáveis de ambiente:", e)

if __name__ == "__main__":
    test_env()        