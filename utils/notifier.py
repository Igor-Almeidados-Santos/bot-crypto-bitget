from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config.settings import SettingsManager
from loguru import logger
import asyncio
import sys
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import tempfile
import os

class Notifier:
    def __init__(self, settings_manager: SettingsManager, dry_run=False):
        if not isinstance(settings_manager, SettingsManager):
            raise TypeError("settings_manager must be an instance of SettingsManager")
        self.settings_manager = settings_manager
        asyncio.run(self.settings_manager.load())
        self.settings = self.settings_manager.settings

        self.telegram_token = self.settings.telegram_bot_token
        self.telegram_chat_id = self.settings.telegram_chat_id
        self.application = None
        self.trades_history = []
        self.bot_running = False
        self.lock = asyncio.Lock()
        self.sent_messages = []
        self.initial_balance = 10000
        self.latest_ohlcv = None
        self.latest_strategy = None
        self.latest_price = 0
        self.dry_run = dry_run
        
        # Carrega as configurações aqui no construtor
        asyncio.run(self._load_settings()) # Executa _load_settings de forma assíncrona

    async def _load_settings(self): # Método assíncrono para carregar as configurações
        await self.settings_manager.load()
        self.settings = self.settings_manager.settings
        
    async def generate_chart(self):
        """Gera gráfico com velas, RSI e MACD (corrigido)"""
        if self.latest_ohlcv is None or self.latest_strategy is None:
            return "⚠️ Dados insuficientes para gerar gráfico."

        # Prepara dados
        df = pd.DataFrame(self.latest_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Calcula indicadores
        rsi = self.latest_strategy.rsi
        macd_line = self.latest_strategy.macd_line
        signal_line = self.latest_strategy.signal_line
        macd_histogram = self.latest_strategy.macd_histogram

        # Cria subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Plot velas
        mpf.plot(df, type='candle', style='yahoo', ax=ax1)
        ax1.set_title(f"{config('SYMBOL')} - Últimas 100 Velas")
        
        # Plot RSI
        ax2.plot(rsi, label='RSI', color='purple')
        ax2.axhline(self.settings.rsi_buy_threshold, linestyle='--', color='green')
        ax2.axhline(self.settings.rsi_sell_threshold, linestyle='--', color='red')
        ax2.set_title("RSI")
        ax2.legend()
        
        # Plot MACD
        ax3.plot(macd_line, label='MACD', color='blue')
        ax3.plot(signal_line, label='Signal', color='orange')
        ax3.bar(df.index, macd_histogram, label='Histogram', color='gray', alpha=0.5)
        ax3.set_title("MACD")
        ax3.legend()

        # Salva gráfico temporário
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, bbox_inches='tight')
            plt.close(fig)
            return tmp.name

    async def start(self):
        if self.telegram_token is None or self.telegram_chat_id is None:
            logger.warning("Notificações do Telegram desativadas. Token ou ID de chat não configurados.")
            return

        try:
            self.application = ApplicationBuilder().token(self.telegram_token).build()
            self.application.add_handler(CommandHandler('start', self.handle_start))
            self.application.add_handler(CallbackQueryHandler(self.handle_button))
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            if self.dry_run:
                self.bot_running = True
                await self.send_telegram("🤖 Modo simulação: Bot iniciado automaticamente.")
            logger.info("Telegram bot iniciado com sucesso")
        except Exception as e:
            logger.exception("Falha ao iniciar Telegram bot:") # Captura o traceback
            raise

    async def send_telegram(self, message, photo_path=None): # Aceita um caminho de foto opcional
        if self.application is None:
            return # Não envia se o bot não estiver inicializado

        try:
            escaped_message = self._escape_message(message)

            if photo_path: # Envia foto se o caminho for fornecido
                with open(photo_path, 'rb') as photo_file:
                    await self.application.bot.send_photo(
                        chat_id=self.telegram_chat_id,
                        photo=photo_file,
                        caption=escaped_message,
                        parse_mode='MarkdownV2'
                    )
            else:
                sent_msg = await self.application.bot.send_message(
                    chat_id=self.telegram_chat_id,
                    text=escaped_message,
                    parse_mode='MarkdownV2'
                )
                self.sent_messages.append(sent_msg.message_id)

        except Exception as e:
            logger.exception("Erro no Telegram:") # Captura o traceback

    async def handle_start(self, update, context):
        """Menu principal unificado"""
        keyboard = [
            [InlineKeyboardButton("ativos", callback_data='ativos'),
             InlineKeyboardButton("gráfico", callback_data='grafico')],
            [InlineKeyboardButton("iniciar bot", callback_data='iniciar'),
             InlineKeyboardButton("parar bot", callback_data='parar')],
            [InlineKeyboardButton("últimos trades", callback_data='trades'),
             InlineKeyboardButton("ganho/perda hoje", callback_data='pnl')],
            [InlineKeyboardButton("limpar histórico", callback_data='limpar')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🤖 *Menu Principal*",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )

    async def handle_button(self, update, context):
        query = update.callback_query
        await query.answer()

        if query.data == 'grafico':
            chart_path = await self.generate_chart()
            if chart_path and os.path.exists(chart_path): # Verifica se o gráfico foi gerado
                await self.send_telegram(
                    message="📊 *Gráfico Atualizado*",
                    photo_path=chart_path
                )
                os.remove(chart_path)
            else:
                await self.send_telegram("⚠️ Falha ao gerar gráfico.")
            return

        async with self.lock:
            if query.data == 'iniciar':
                self.bot_running = True
                await query.edit_message_text("✅ Bot iniciado. Monitorando sinais...")
            elif query.data == 'parar':
                self.bot_running = False
                await query.edit_message_text("🛑 Bot parado. Nenhuma operação será realizada.")
            elif query.data == 'limpar':
                for message_id in self.sent_messages[:]:
                    try:
                        await self.application.bot.delete_message(self.telegram_chat_id, message_id)
                        self.sent_messages.remove(message_id)
                    except Exception as e:
                        logger.error(f"Falha ao limpar mensagem {message_id}: {e}")
                await self.send_telegram("🗑️ Histórico limpo!")
            elif query.data == 'pnl':
                if not self.trades_history:
                    await self.send_telegram("⚠️ Nenhum trade registrado.")
                else:
                    total_pnl = 0
                    for trade in self.trades_history:
                        if trade['side'] == 'strong_buy':
                            pnl = (self.latest_price - trade['price']) * trade['amount']
                        else:
                            pnl = (trade['price'] - self.latest_price) * trade['amount']
                        total_pnl += pnl
                    if self.initial_balance == 0:  # Evita divisão por zero se o saldo inicial for zero
                        message = "⚠️ Saldo inicial é zero. Não é possível calcular PnL."
                    else:
                        pnl_percent = (total_pnl / self.initial_balance) * 100
                        message = (
                            f"📈 *PnL Diário*: {pnl_percent:+.2f}%\n"
                            f"Saldo inicial: ${self.initial_balance:.2f}\n"
                            f"Saldo atual: ${self.initial_balance + total_pnl:.2f}"
                        )
                    await self.send_telegram(message)
                    
            elif query.data == 'trades':
                if not self.trades_history:
                    await self.send_telegram("⚠️ Nenhum trade registrado.")
                else:
                    message = "📜 *Últimos 5 Trades*\n"
                    for trade in self.trades_history[-5:]:
                        message += (
                            f"`{trade['timestamp']}`\n"
                            f"{trade['side']} {trade['amount']:.5f} à ${trade['price']:.2f}\n"
                            f"{'-'*10}\n"
                        )
                    await self.send_telegram(message)

    def _escape_message(self, message):
        """Escapa caracteres especiais do Telegram"""
        escape_chars = '_*[]()~`>#+-=|{}.!/'
        return ''.join(['\\' + c if c in escape_chars else c for c in message])

    async def add_trade(self, trade):
        """Adiciona trade ao histórico com controle de concorrência"""
        async with self.lock:
            self.trades_history.append(trade)
            if len(self.trades_history) > 50:
                self.trades_history.pop(0)
                
    async def notify_trade(self, trade):
        """Adiciona trade ao histórico com controle de concorrência
        e notifica via Telegram."""
        async with self.lock:
            self.trades_history.append(trade)
            if len(self.trades_history) > 50:
                self.trades_history.pop(0)

        message = (
            f"🚀 Novo Trade Executado:\n"
            f"Side: {trade['side']}\n"
            f"Quantidade: {trade['amount']:.5f}\n"
            f"Preço: {trade['price']:.2f}\n"
            f"Timestamp: {trade['timestamp']}"
        )
        try:
            await self.send_telegram(message)
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de trade: {e}")

async def start_notifier(message_queue: asyncio.Queue):
    settings_manager = await SettingsManager()
    notifier = Notifier(settings_manager) # Passa settings_manager para o construtor