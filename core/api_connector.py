import ccxt
from loguru import logger
from config.settings import API_KEY, API_SECRET, API_PASSPHRASE

class BitgetAPIConnector:
    def __init__(self):
        self.exchange = ccxt.bitget({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'password': API_PASSPHRASE,
            'options': {
                'defaultType': 'swap',  # Operar futuros/perpétuos
            },
        })
        self.exchange.load_markets()  # Carregar mercados disponíveis

    def fetch_ticker(self, symbol):
        """Obtém informações do ticker para um par específico."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            logger.info(f"Ticker obtido para {symbol}: {ticker}")
            return ticker
        except Exception as e:
            logger.error(f"Erro ao obter ticker: {e}")
            return None

    def create_order(self, symbol, side, amount, order_type='market'):
        """Cria ordem com parâmetros específicos da Bitget."""
        try:
            order = self.exchange.create_order(
                symbol,
                order_type,
                side,
                amount,
                params={'positionType': 'cross'}  # Parâmetro necessário para futuros
            )
            logger.info(f"Ordem criada: {order}")
            return order
        except Exception as e:
            logger.error(f"Erro ao criar ordem: {e}")
            return None

    def fetch_balance(self):
        """Obtém o saldo da conta."""
        try:
            balance = self.exchange.fetch_balance()
            logger.info(f"Saldo obtido: {balance}")
            return balance
        except Exception as e:
            logger.error(f"Erro ao obter saldo: {e}")
            return None