from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from decouple import config
from loguru import logger
from config.settings import SettingsManager
import asyncio
import sys
import matplotlib.pyplot as plt
import mplfinance as mpf
import tempfile
import os

class Notifier:
    def __init__(self, dry_run=False):
        self.telegram_token = config('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = config('TELEGRAM_CHAT_ID')
        self.settings = SettingsManager()
        self.application = None
        self.trades_history = []
        self.bot_running = False
        self.lock = asyncio.Lock()
        self.sent_messages = []
        self.initial_balance = 10000  # Saldo fixo para simulação
        self.latest_ohlcv = None  # Armazena dados OHLCV mais recentes
        self.latest_strategy = None  # Armazena estratégia
        self.latest_price = 0  # Armazena último preço conhecido
        self.dry_run = dry_run  # Adiciona flag de simulação
    
    async def generate_chart(self):
        """Gera gráfico com velas, RSI e MACD."""
        if self.latest_ohlcv is None or self.latest_strategy is None:
            return "⚠️ Dados não disponíveis ainda."

        # Prepara dados
        df = pd.DataFrame(self.latest_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Calcula indicadores
        rsi = self.latest_strategy.rsi
        macd_line, signal_line, _ = self.latest_strategy.macd

        # Cria subplots
        fig = plt.figure(figsize=(12, 8))
        ax1 = plt.subplot2grid((4, 1), (0, 0), rowspan=2)
        ax2 = plt.subplot2grid((4, 1), (2, 0), rowspan=1)
        ax3 = plt.subplot2grid((4, 1), (3, 0), rowspan=1)

        # Plot velas
        mpf.plot(df, type='candle', style='yahoo', ax=ax1, volume=False)
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
        ax3.bar(macd_line.index, self.latest_strategy.macd_histogram, label='Histogram', color='gray')
        ax3.set_title("MACD")
        ax3.legend()

        # Salva gráfico temporário
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, bbox_inches='tight')
            tmp.close()
            return tmp.name
        
        # Calcula indicadores manualmente
        rsi = self.latest_strategy.rsi
        macd_line = self.latest_strategy.macd_line
        signal_line = self.latest_strategy.signal_line
        macd_histogram = self.latest_strategy.macd_histogram
    
    async def start(self):
        """Inicia o bot SEM handler de mensagens (apenas botões)."""
        try:
            self.application = ApplicationBuilder().token(self.telegram_token).build()
            
            # Handlers
            self.application.add_handler(CommandHandler('start', self.handle_start))
            self.application.add_handler(CallbackQueryHandler(self.handle_button))
            # Removido: MessageHandler (não é mais necessário)
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            if '--dry-run' in sys.argv:
                self.bot_running = True
                await self.send_telegram("🤖 Modo simulação: Bot iniciado automaticamente.")
            
            logger.info("Telegram bot iniciado com sucesso")
        
        except Exception as e:
            logger.error(f"Falha ao iniciar Telegram bot: {e}")
            await self.send_telegram(f"⚠️ Erro crítico: {str(e)}")
            raise
        
    async def send_telegram(self, message):
        """Envia mensagem com escape completo de caracteres do MarkdownV2."""
        try:
            # Escapa TODOS os caracteres reservados do Telegram
            escaped_message = message.translate(str.maketrans({
                '_': '\\_',
                '*': '\\*',
                '[': '\\[',
                ']': '\\]',
                '(': '\\(',
                ')': '\\)',
                '~': '\\~',
                '`': '\\`',
                '>': '\\>',
                '#': '\\#',
                '+': '\\+',
                '-': '\\-',  # Adicionado escape para '-'
                '=': '\\=',
                '|': '\\|',
                '{': '\\{',
                '}': '\\}',
                '.': '\\.',
                '!': '\\!',
                '/': '\\/'
            }))
            
            await self.application.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=escaped_message,
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            logger.error(f"Falha no Telegram: {e}")
            await self.application.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=f"⚠️ Erro ao enviar mensagem: {str(e)}"
            )

    async def handle_start(self, update, context):
        """Menu principal com botão de gráfico."""
        keyboard = [
            [InlineKeyboardButton("ativos", callback_data='ativos'),
             InlineKeyboardButton("gráfico", callback_data='grafico')],  # Novo botão
            [InlineKeyboardButton("iniciar bot", callback_data='iniciar'),
             InlineKeyboardButton("parar bot", callback_data='parar')],
            [InlineKeyboardButton("últimos trades", callback_data='trades'),
             InlineKeyboardButton("ganho/perda hoje", callback_data='pnl')],
            [InlineKeyboardButton("limpar histórico", callback_data='limpar')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🤖 *Menu Principal*", reply_markup=reply_markup, parse_mode='MarkdownV2')
        """Menu principal simplificado SEM ajustes de parâmetros."""
        keyboard = [
            [InlineKeyboardButton("ativos", callback_data='ativos'),
             InlineKeyboardButton("status", callback_data='status')],
            [InlineKeyboardButton("iniciar bot", callback_data='iniciar'),
             InlineKeyboardButton("parar bot", callback_data='parar')],
            [InlineKeyboardButton("últimos trades", callback_data='trades'),
             InlineKeyboardButton("ganho/perda hoje", callback_data='pnl')],
            [InlineKeyboardButton("limpar histórico", callback_data='limpar')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🤖 *Menu Principal*", reply_markup=reply_markup, parse_mode='MarkdownV2')

    async def handle_button(self, update, context):
        """Processa cliques nos botões com novas funcionalidades."""
        query = update.callback_query
        await query.answer()
        message = "⚠️ Erro ao processar solicitação."  # Mensagem padrão
        
        if query.data == 'ativos':
            # Envia mensagem com ativo atual
            await self.send_telegram(f"ativos: {config('SYMBOL')}")
            
        elif query.data == 'status':
            # Envia mensagem de status formatada
            status = self.get_formatted_status()
            await self.send_telegram(status)

        elif query.data == 'limpar':
            # Limpa histórico de mensagens do bot
            async with self.lock:
                for message_id in self.sent_messages:
                    try:
                        await self.application.bot.delete_message(
                            chat_id=self.telegram_chat_id,
                            message_id=message_id
                        )
                    except Exception as e:
                        logger.error(f"Falha ao limpar mensagem {message_id}: {e}")
                self.sent_messages = []
                await self.send_telegram("🗑️ Histórico limpo!")   

        if query.data == 'iniciar':
            async with self.lock:
                self.bot_running = True
                await query.edit_message_text("✅ Bot iniciado. Monitorando sinais...")

        elif query.data == 'parar':
            async with self.lock:
                self.bot_running = False
                await query.edit_message_text("🛑 Bot parado. Nenhum trade será executado.")

        if query.data == 'trades':
            async with self.lock:
                if not self.trades_history:
                    message = "⚠️ Nenhum trade registrado ainda."
                else:
                    message = "📜 *Últimos 5 Trades*\n\n"
                    for trade in self.trades_history[-5:]:
                        message += (
                            f"`{trade['timestamp']}`\n"
                            f"{trade['side']} {trade['amount']:.5f} à ${trade['price']:.2f}\n"
                            f"{'-'*10}\n"
                        )
            await self.send_telegram(message)

        elif query.data == 'pnl':
            async with self.lock:
                if not self.trades_history:
                    message = "⚠️ Nenhum trade para calcular PnL."
                else:
                    latest_price = self.latest_price if self.latest_price else 65000
                    total_pnl = 0

                    for trade in self.trades_history:
                        if trade['side'] == 'strong_buy':
                            pnl = (latest_price - trade['price']) * trade['amount']
                        else:
                            pnl = (trade['price'] - latest_price) * trade['amount']
                        total_pnl += pnl

                    pnl_percent = (total_pnl / self.initial_balance) * 100
                    message = (
                        f"📈 *PnL Diário*: {pnl_percent:+.2f}%\n"
                        f"Saldo inicial: ${self.initial_balance:.2f}\n"
                        f"Saldo atual: ${self.initial_balance + total_pnl:.2f}"
                    )
            await self.send_telegram(message)  # Agora sempre definido
        
        elif query.data == 'grafico':
            chart_path = await self.generate_chart()
            if os.path.exists(chart_path):
                with open(chart_path, 'rb') as chart:
                    await self.application.bot.send_photo(
                        chat_id=self.telegram_chat_id,
                        photo=chart,
                        caption="📊 *Gráfico Atualizado*",
                        parse_mode='MarkdownV2'
                    )
                os.remove(chart_path)  # Apaga arquivo temporário
            else:
                await self.send_telegram("⚠️ Dados insuficientes para gerar gráfico.")        
                
        elif query.data in ['iniciar', 'parar']:
            async with self.lock:
                self.bot_running = query.data == 'iniciar'
                state = "ativo" if self.bot_running else "parado"
                message = f"봇 estado: {state}"
                await query.edit_message_text(
                    text=self._escape_message(message),
                    reply_markup=query.message.reply_markup  # Mantém os botões
                )

    def _escape_message(self, message):
        """Escapa caracteres reservados do MarkdownV2."""
        return message.translate(str.maketrans({
            '_': '\\_',
            '*': '\\*',
            '[': '\\[',
            ']': '\\]',
            '(': '\\(',
            ')': '\\)',
            '~': '\\~',
            '`': '\\`',
            '>': '\\>',
            '#': '\\#',
            '+': '\\+',
            '-': '\\-',
            '=': '\\=',
            '|': '\\|',
            '{': '\\{',
            '}': '\\}',
            '.': '\\.',
            '!': '\\!',
            '/': '\\/'
        }))
        
    async def send_telegram(self, message):
        """Envia mensagem e armazena ID para limpeza."""
        escaped_message = self._escape_message(message)
        sent_msg = await self.application.bot.send_message(
            chat_id=self.telegram_chat_id,
            text=escaped_message,
            parse_mode='MarkdownV2'
        )
        self.sent_messages.append(sent_msg.message_id)  # Armazena ID    
    
    async def error_handler(self, update, context):
        """Ignora CancelledError e trata outros erros."""
        if isinstance(context.error, asyncio.CancelledError):
            logger.info("Updater parado corretamente.")
            return
        
        logger.error(f"Erro no Telegram: {context.error}")
        await context.bot.send_message(
            chat_id=self.telegram_chat_id,
            text=f"⚠️ Erro detectado: {str(context.error)}"
        )

    async def add_trade(self, trade):
        """Adiciona trade ao histórico com limite de 50 entradas."""
        async with self.lock:
            self.trades_history.append(trade)
            if len(self.trades_history) > 50:
                self.trades_history.pop(0)  # Mantém histórico recente

    def get_formatted_status(self):
        """Retorna status formatado com MarkdownV2."""
        return (
            f"📊 *Configurações Atuais*\n"
            f"RSI: Buy <{self.settings.rsi_buy_threshold}, Sell >{self.settings.rsi_sell_threshold}\n"
            f"MACD: {self.settings.macd_fast}/{self.settings.macd_slow}/{self.settings.macd_signal}\n"
            f"Risco: {self.settings.risk_per_trade*100:.0f}%\n"
            f"Alavancagem: {self.settings.leverage}x\n"
            f"Modo: {'SIMULAÇÃO' if '--dry-run' in sys.argv else 'REAL'}"
        )