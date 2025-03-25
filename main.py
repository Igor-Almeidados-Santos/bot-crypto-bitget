import asyncio
import sys
from core.api_connector import BitgetAPIConnector
from core.strategy import TradingStrategy
from utils.logger import PositionManager
from utils.notifier import Notifier
from config.settings import SettingsManager
from loguru import logger

async def main(dry_run=False):
    """Função principal do bot."""

    # Carrega as configurações primeiro
    settings_manager = await SettingsManager()
    await settings_manager.load()
    settings = settings_manager.settings

    # Inicializa componentes principais
    api = BitgetAPIConnector(settings_manager)
    await api.connect()  # Aguarda a conexão com a API e WebSocket

    notifier = Notifier(settings_manager, dry_run) # Passa dry_run para o Notifier
    await notifier.start()

    initial_balance = notifier.initial_balance # Obtém o saldo inicial do Notifier
    risk_manager = RiskManager(settings_manager=settings_manager, balance=initial_balance, symbol=settings.symbol)

    # Notificação de inicialização
    start_message = f"🤖 Bot iniciado em modo {('SIMULAÇÃO' if dry_run else 'REAL')} para {settings.symbol} em {settings.timeframe}"
    logger.info(f"Iniciando o bot com as configurações: {settings}") # Usa settings diretamente

    position_manager = PositionManager(api, settings_manager)

    # Loop principal com controle de concorrência
    while True:
        async with notifier.lock:  # Garante acesso exclusivo
            if notifier.bot_running:
                try:
                    # Obtém dados OHLCV com validação
                    ohlcv = await api.exchange.fetch_ohlcv(
                    symbol=settings.symbol,
                    timeframe=settings.timeframe,
                    limit=100
                )

                    if settings.telegram_bot_token: # Verifica se as configurações do Telegram estão presentes
                        await notifier.send_telegram(start_message) # Envia a mensagem de inicialização

                    if len(ohlcv) < 100:
                        raise ValueError("Dados insuficientes para análise")

                    # Atualiza estratégia e preço
                    strategy = TradingStrategy(ohlcv, settings)
                    notifier.latest_ohlcv = ohlcv
                    notifier.latest_strategy = strategy
                    notifier.latest_price = strategy.data['close'].iloc[-1]

                    # Verifica sinal de trading, calcula tamanho da posição e abre posição
                    if strategy.signal in ["strong_buy", "strong_sell"]:
                        try:
                            quantity = position_manager.risk_manager.calculate_position_size(
                                entry_price=notifier.latest_price,
                                stop_loss_price=strategy.stop_loss_price
                            )[0]

                            await position_manager.open_position(
                                symbol=settings.symbol,
                                side=strategy.signal.split('_')[1],
                                quantity=quantity,
                                entry_price=notifier.latest_price
                            )
                        except Exception as e:
                            logger.error(f"Erro ao abrir posição: {e}")
                            await notifier.send_telegram(f"⚠️ Erro ao abrir posição: {str(e)}")

                    # Gerencia posições e aguarda o próximo ciclo
                    await position_manager.manage_positions()
                    await asyncio.sleep(settings.trade_frequency)

                except Exception as e:
                    logger.exception(f"Erro no ciclo de trading:") # Captura o traceback completo
                    if settings.telegram_bot_token: # Verifica se as configurações do Telegram estão presentes
                        await notifier.send_telegram(f"⚠️ Falha no ciclo de trading: {str(e)}")
                    await asyncio.sleep(settings.error_sleep_time)
            else:
                await asyncio.sleep(5)  # Verificação periódica quando bot está parado

if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv
    try:
        asyncio.run(main(dry_run=dry_run))
    except KeyboardInterrupt:
        logger.info("🛑 Bot encerrado pelo usuário")
    except Exception as e:
        logger.exception("🔥 Falha fatal:") # Usa logger.exception para capturar o traceback
        sys.exit(1)