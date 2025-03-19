import streamlit as st
from decouple import Config, RepositoryEnv, UndefinedValueError
import pandas as pd
import plotly.graph_objects as go
from core.api_connector import BitgetAPIConnector

# Carrega configurações do .env
try:
    env = Config(RepositoryEnv('.env'))
    DASHBOARD_USER = env('DASHBOARD_USER')
    DASHBOARD_PASSWORD = env('DASHBOARD_PASSWORD')
except UndefinedValueError as e:
    st.error(f"Erro na configuração: {e}")
    st.stop()

# Login
def check_login():
    username = st.sidebar.text_input("Usuário", key="user")
    password = st.sidebar.text_input("Senha", type="password", key="pass")
    
    if st.sidebar.button("Login"):
        if username == DASHBOARD_USER and password == DASHBOARD_PASSWORD:
            st.session_state.logged_in = True
            st.success("Login bem-sucedido! Carregando dashboard...")
            st.rerun()
        else:
            st.error("Usuário/Senha incorretos")
            st.session_state.logged_in = False

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    check_login()
    st.stop()
else:
    api = BitgetAPIConnector()
    st.set_page_config(page_title="Bitget Bot Monitor", layout="wide")

# Dashboard principal
st.title(f"📊 Monitoramento - {api.symbol}")  # Usa símbolo da API

# Dark mode
dark_mode = st.sidebar.checkbox("🌙 Modo Escuro")
if dark_mode:
    st.config.set_option('theme.primaryColor', '#000000')
    st.config.set_option('theme.backgroundColor', '#0e1117')

# Gráfico de velas (WebSocket)
st.title("🕯️ Gráfico de Velas (WebSocket)")

if hasattr(api, 'trades') and api.trades:
    df = pd.DataFrame(api.trades)
    df['datetime'] = pd.to_datetime(df['timestamp'])
    
    # Resample para OHLC (1 minuto)
    df_ohlc = df.set_index('datetime')['price'].resample('1T').ohlc()
    df_ohlc.columns = ['open', 'high', 'low', 'close']
    df_ohlc = df_ohlc.reset_index()

    fig = go.Figure(data=[go.Candlestick(
        x=df_ohlc['datetime'],
        open=df_ohlc['open'],
        high=df_ohlc['high'],
        low=df_ohlc['low'],
        close=df_ohlc['close']
    )])
    fig.update_layout(
        title=f"{api.symbol} (1m)",
        template='plotly_dark' if dark_mode else 'plotly_white'
    )
    st.plotly_chart(fig)
else:
    st.warning("Aguardando dados do WebSocket...")

# Histórico de trades
st.title("📋 Histórico de Trades em Tempo Real")
if hasattr(api, 'trades') and api.trades:
    trades_df = pd.DataFrame(api.trades)
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
    st.dataframe(trades_df.style.applymap(lambda x: 'color: green' if x == 'buy' else 'color: red' if x == 'sell' else ''))
else:
    st.warning("Nenhum trade registrado ainda.")

# Backtest
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