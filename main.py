import sys
import asyncio
import pandas as pd
from loguru import logger
from decouple import config
from core.api_connector import BitgetAPIConnector
from core.strategy import TradingStrategy
from core.risk_manager import RiskManager
from utils.notifier import Notifier
from config.settings import SettingsManager

async def main(dry_run=False):
    api = BitgetAPIConnector()
    notifier = Notifier(dry_run=dry_run)
    settings = SettingsManager()
    
    # Inicia Telegram bot
    await notifier.start()
    
    # Notificação de inicialização
    start_message = "🤖 Bot iniciado em modo " + ("SIMULAÇÃO" if dry_run else "REAL")
    logger.info(start_message)
    await notifier.send_telegram(start_message)

    # Loop principal
    while notifier.bot_running:  # Agora depende do estado do bot
        try:
            ohlcv = api.exchange.fetch_ohlcv(config('SYMBOL'), timeframe=config('TIMEFRAME'), limit=100)
            strategy = TradingStrategy(ohlcv, settings)
            notifier.latest_price = strategy.data['close'].iloc[-1]  # Atualiza preço

            if strategy.signal in ["strong_buy", "strong_sell"]:
                risk_manager = RiskManager(
                    balance=10000 if dry_run else api.exchange.fetch_balance()['total']['USDT'],
                    symbol=config('SYMBOL')
                )
                quantity, risk = risk_manager.calculate_position_size(
                    entry_price=notifier.latest_price,
                    stop_loss_price=notifier.latest_price * 0.98
                )
                
                trade = {
                    'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'side': strategy.signal,
                    'price': notifier.latest_price,
                    'amount': quantity
                }
                await notifier.add_trade(trade)
                
                if dry_run:
                    logger.info(f"DRY RUN: Ordem simulada - {strategy.signal} {quantity} {config('SYMBOL')}")
                else:
                    order = api.create_order(
                        symbol=config('SYMBOL'),
                        side=strategy.signal.split('_')[1],
                        amount=quantity
                    )
                    logger.info(f"Ordem executada: {order}")

            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"Erro crítico: {e}")
            await notifier.send_telegram(f"⚠️ Erro no bot: {str(e)}")

if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv
    asyncio.run(main(dry_run=dry_run))