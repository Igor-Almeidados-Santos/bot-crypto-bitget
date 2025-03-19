# Bitget Bot Documentation

## Visão Geral
Bot automatizado para negociação de criptomoedas na Bitget com:
- Estratégia RSI + MACD
- Gerenciamento de risco
- Backtesting
- Notificações via Telegram

## Instalação
```bash
git clone https://github.com/seu-usuario/bitget-bot
cd bitget-bot
pip install -r requirements.txt

Configuração

Crie um arquivo .env com:
BITGET_API_KEY=...
BITGET_API_SECRET=...
BITGET_PASSPHRASE=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

Ajuste parâmetros em config/settings.py:

SYMBOL = 'BTC/USDT:USDT'
TIMEFRAME = '1m'
RISK_PER_TRADE = 0.01

Execução

# Modo real
python main.py

# Modo simulação
python main.py --dry-run

# Backtest
python main.py --backtest

Customização de Estratégias
Modifique core/strategy.py para:

Adicionar novos indicadores (ex.: Bollinger Bands)
Ajustar parâmetros de RSI/MACD

