import ccxt
from decouple import config
from loguru import logger
import websocket
import json
import pandas as pd
from threading import Thread
import time

class BitgetAPIConnector:
    def __init__(self):
        # Configuração REST API
        self.exchange = ccxt.bitget({
            'apiKey': config('BITGET_API_KEY'),
            'secret': config('BITGET_API_SECRET'),
            'password': config('BITGET_PASSPHRASE'),
            'options': {'defaultType': 'swap'}
        })
        self.exchange.load_markets()
        self.trades = []
        self.symbol = config('SYMBOL')  # Obtém símbolo do .env
        self.ws = None
        self.reconnect_attempts = 0  # Inicializa contador de reconexão
        
        # Inicia WebSocket em thread separada
        self.start_websocket()

    def start_websocket(self):
        """Reconecta WebSocket automaticamente."""
        def run_ws():
            while self.reconnect_attempts < 5:  # Limita tentativas
                try:
                    self.ws = websocket.WebSocketApp(
                        "wss://ws.bitget.com/mix/v1/stream",
                        on_message=self.on_message,
                        on_error=self.on_error,
                        on_close=self.on_close
                    )
                    self.ws.on_open = self.on_open
                    self.ws.run_forever()
                except Exception as e:
                    logger.error(f"Erro na conexão WebSocket: {e}")
                    self.reconnect_attempts += 1
                    time.sleep(5 * self.reconnect_attempts)  # Atraso crescente
            logger.error("Falha na conexão WebSocket após 5 tentativas")
        
        Thread(target=run_ws, daemon=True).start()

    def on_open(self, ws):
        """Assina canal de trades com símbolo formatado."""
        channel = f"trade.{self.symbol.replace('/', '').replace(':USDT', '')}"
        subscribe_msg = {
            "op": "subscribe",
            "args": [channel]
        }
        ws.send(json.dumps(subscribe_msg))
        logger.info(f"Inscrito no canal WebSocket: {channel}")

    def on_message(self, ws, message):
        """Processa trades recebidos."""
        data = json.loads(message)
        if 'data' in data and data['data']:
            trade = data['data'][0]
            self.trades.append({
                'timestamp': pd.Timestamp.now(),
                'side': trade['side'],
                'price': float(trade['price']),
                'amount': float(trade['size'])
            })
            logger.debug(f"Trade recebido: {trade}")

    def on_error(self, ws, error):
        """Trata erros do WebSocket."""
        logger.error(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_reason):
        """Reconecta após fechar conexão."""
        logger.warning(f"Conexão WebSocket fechada: {close_reason}")
        self.reconnect_attempts += 1
        time.sleep(5)
        self.start_websocket()

    def fetch_ticker(self, symbol):
        """Obtém ticker via REST API."""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Erro no fetch_ticker: {e}")
            return None

    def create_order(self, symbol, side, amount, order_type='market'):
        """Cria ordem via REST API."""
        try:
            order = self.exchange.create_order(
                symbol,
                order_type,
                side,
                amount,
                params={'positionType': 'cross'}
            )
            self.trades.append({
                'timestamp': pd.Timestamp.now(),
                'side': side,
                'price': order['price'],
                'amount': order['amount']
            })
            return order
        except Exception as e:
            logger.error(f"Erro ao criar ordem: {e}")
            return None