from decouple import config

# Configurações da Bitget
API_KEY = config('BITGET_API_KEY')
API_SECRET = config('BITGET_API_SECRET')
API_PASSPHRASE = config('BITGET_PASSPHRASE')

# Parâmetros de trading
SYMBOL = 'BTC/USDT:USDT'  # Par de negociação
TIMEFRAME = '5m'          # Intervalo das velas
LEVERAGE = 10             # Alavancagem
RISK_PER_TRADE = 0.01     # Risco máximo por trade (1%)

# Configurações de segurança
MAX_RETRIES = 3
RATE_LIMIT = 1000  # Limite de requisições por minuto