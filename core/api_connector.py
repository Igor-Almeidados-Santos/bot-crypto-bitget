import asyncio
import ccxt.async_support as ccxt_async
import json
import pandas as pd
import time
import websocket
from threading import Thread
from config.settings import SettingsManager
from loguru import logger
from tenacity import retry, wait_exponential, stop_after_attempt

class BitgetAPIConnector:
    def __init__(self):
        self.settings_manager = SettingsManager()
        asyncio.run(self.settings_manager.load())
        self.settings = self.settings_manager.settings

        self.exchange: ccxt_async.bitget = ccxt_async.bitget({
            'apiKey': self.settings.bitget_api_key,
            'secret': self.settings.bitget_api_secret,
            'password': self.settings.bitget_passphrase,
            'options': {'defaultType': 'swap'}
        })

        self.ws = None
        self.ws_thread = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.connected_event = asyncio.Event()

    async def connect(self):
        await self.exchange.load_markets()
        self.start_websocket()
        await self.connected_event.wait() # Aguarda a conexão WebSocket

    def start_websocket(self):
        self.ws_thread = Thread(target=self.run_websocket, daemon=True)
        self.ws_thread.start()

    @retry(wait=wait_exponential(multiplier=1, min=4, max=30), stop=stop_after_attempt(5)) # Repetição com backoff exponencial
    def run_websocket(self):
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
            raise  # Re-raise the exception to trigger tenacity retry

    def on_open(self, ws):
        symbol_formatted = self.format_symbol(self.settings.symbol)
        channel = f"trade.{symbol_formatted}"
        subscribe_message = {
            "op": "subscribe",
            "args": [channel]
        }
        ws.send(json.dumps(subscribe_message))
        logger.info(f"Inscrito no canal WebSocket: {channel}")
        asyncio.set_event_loop(asyncio.new_event_loop()) # Define um novo loop de eventos para a thread
        asyncio.get_event_loop().run_until_complete(self.set_connected_event()) # Define o evento como True na thread

    async def set_connected_event(self):
        self.connected_event.set()

    def on_message(self, ws, message):
        data = json.loads(message)
        if 'data' in data and data['data']:
            trade = data['data'][0]
            logger.debug(f"Trade recebido: {trade}")

    def on_error(self, ws, error):
        logger.exception(f"Erro no WebSocket:") # Captura o traceback

    def on_close(self, ws, close_status_code, close_reason):
        logger.warning(f"Conexão WebSocket fechada: {close_reason}")
        self.connected_event.clear() # Limpa o evento de conexão

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3)) # Repetição com backoff exponencial
    async def fetch_ticker(self, symbol):
        """Obtém o ticker do símbolo especificado."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except ccxt_async.NetworkError as e: # Corrected exception type
            logger.error(f"Erro de rede ao buscar ticker: {e}")
            return None
        except Exception as e:
            logger.exception("Erro ao buscar ticker:")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=1, max=5), stop=stop_after_attempt(2))
    async def create_order(self, symbol, side, amount, order_type='market', params={}):
        """Cria uma ordem."""
    async def create_order(self, symbol, side, amount, order_type='market', params={}):
        try:
            if order_type == 'market':
                order = await self.exchange.create_order(symbol, order_type, side, amount, params)
            elif order_type == 'limit':
                if 'price' not in params:
                    raise ValueError("Price is required for limit orders")
                if side == 'buy':
                    order = await self.exchange.create_limit_buy_order(symbol, amount, params['price'], params) # Usa create_limit_buy_order
                else:
                    order = await self.exchange.create_limit_sell_order(symbol, amount, params['price'], params) # Usa create_limit_sell_order
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            logger.info(f"Ordem criada: {order}")
            return order
        except ccxt_async.InsufficientFunds as e: # Corrected exception type
            logger.error(f"Saldo insuficiente para criar ordem: {e}")
            raise  # Re-raise InsufficientFunds
        except Exception as e:
            logger.exception("Erro ao criar ordem:")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=1, max=5), stop=stop_after_attempt(2)) # Repetição com backoff exponencial
    async def close_position(self, symbol, position):
        """Fecha uma posição."""
        try:
            amount = position['quantity']
            side = 'buy' if position['side'] == 'sell' else 'sell'
            order = await self.create_order(
                symbol, side, amount, params={'reduceOnly': True}
            )
            logger.info(f"Posição fechada: {order}")
            return order
        except Exception as e:
            logger.exception("Erro ao fechar posição:")
            return None # Return None after logging the exception


    async def get_current_price(self, symbol):
        ticker = await self.fetch_ticker(symbol)
        if ticker:
            return ticker['last']
        return None

    def format_symbol(self, symbol):
        return symbol.replace('/', '').replace(':', '').upper()


        return symbol.replace('/', '').replace(':', '').upper()