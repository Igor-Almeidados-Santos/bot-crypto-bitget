import streamlit as st
from decouple import config, UndefinedValueError
import pandas as pd
import time
from core.api_connector import BitgetAPIConnector
from core.strategy import TradingStrategy
from core.risk_manager import RiskManager

# Configuração do .env
try:
    DASHBOARD_USER = config('DASHBOARD_USER')
    DASHBOARD_PASSWORD = config('DASHBOARD_PASSWORD')
except UndefinedValueError:
    st.error("Arquivo .env não encontrado ou variáveis ausentes")
    st.stop()

# Login
def check_login():
    username = st.sidebar.text_input("Usuário", key="user")
    password = st.sidebar.text_input("Senha", type="password", key="pass")
    
    if st.sidebar.button("Login"):
        if username == DASHBOARD_USER and password == DASHBOARD_PASSWORD:
            st.session_state.logged_in = True
            st.success("Login bem-sucedido! Carregando dashboard...")
            time.sleep(1)
            st.rerun()  # Método correto
        else:
            st.error("Usuário/Senha incorretos")
            st.session_state.logged_in = False

# Página de login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    check_login()
    st.stop()
else:
    # Inicializa componentes APENAS após login
    api = BitgetAPIConnector()
    strategy = TradingStrategy([])
    risk_manager = RiskManager(balance=10000, symbol='BTC/USDT:USDT')
    st.set_page_config(page_title="Bitget Bot Monitor", layout="wide")

# Dashboard principal
st.title("📊 Monitoramento em Tempo Real")

# Dark mode
dark_mode = st.sidebar.checkbox("🌙 Modo Escuro")
if dark_mode:
    st.config.set_option('theme.primaryColor', '#000000')
    st.config.set_option('theme.backgroundColor', '#0e1117')

# Gráfico de velas
ohlcv = api.exchange.fetch_ohlcv('BTC/USDT:USDT', timeframe='1m', limit=100)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

st.title("🕯️ Gráfico de Velas (Candlestick)")
st.write(f"Últimos {len(df)} candles")
st.bar_chart(df.set_index('datetime')[['open', 'high', 'low', 'close']])

# Métricas em tempo real
def update_metrics():
    ohlcv = api.exchange.fetch_ohlcv('BTC/USDT:USDT', timeframe='1m', limit=100)
    strategy.data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    signal = strategy.generate_signal()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Último Sinal", signal)
    col2.metric("RSI", strategy.data['rsi'].iloc[-1] if 'rsi' in strategy.data.columns else 0)
    col3.metric("MACD", strategy.data['macd'].iloc[-1] if 'macd' in strategy.data.columns else 0)

placeholder = st.empty()
while True:
    with placeholder.container():
        update_metrics()
    time.sleep(10)

# Histórico de backtest
st.title("📜 Histórico de Backtest")
try:
    backtest_df = pd.read_csv('backtest_results.csv')
    st.dataframe(backtest_df)
    
    total_trades = len(backtest_df)
    win_rate = (backtest_df['signal'].str.contains('buy').sum() / total_trades) * 100
    col1, col2 = st.columns(2)
    col1.metric("Total de Trades", total_trades)
    col2.metric("Taxa de Acerto", f"{win_rate:.2f}%")
except FileNotFoundError:
    st.warning("Execute o backtest primeiro: `python main.py --backtest`")