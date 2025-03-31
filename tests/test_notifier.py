import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Bot
from telegram.ext import ApplicationBuilder

from config.settings import Settings, SettingsManager
from utils.notifier import Notifier

@pytest.fixture
async def notifier(): # Fixture assíncrona
    settings_manager = await SettingsManager() # Usa await
    settings_manager.settings = Settings(telegram_bot_token="TEST_TOKEN", telegram_chat_id="TEST_CHAT_ID")
    return Notifier(settings_manager) # Retorna o notifier

@pytest.mark.asyncio
async def test_start_with_telegram(event_loop, notifier): # Adiciona event_loop
    notifier_instance = await notifier # Aguarda a fixture notifier
    """Testa a inicialização do notificador com Telegram."""
    with patch('utils.notifier.ApplicationBuilder') as MockAppBuilder:
        mock_app = AsyncMock()
        MockAppBuilder.return_value.token.return_value.build.return_value = mock_app

        await notifier.start()

        MockAppBuilder.assert_called_once_with()
        mock_app.add_handler.assert_called()
        mock_app.initialize.assert_awaited_once()
        mock_app.start.assert_awaited_once()
        mock_app.updater.start_polling.assert_awaited_once()

@pytest.mark.asyncio
async def test_start_without_telegram(notifier):
    """Testa inicialização sem token/chat_id."""
    notifier.telegram_token = None
    notifier.telegram_chat_id = None
    with patch('utils.notifier.logger.warning') as mock_warning:
        await notifier.start()
        mock_warning.assert_called_once()

@pytest.mark.asyncio
async def test_send_telegram_with_photo(notifier):
    with patch('utils.notifier.ApplicationBuilder') as MockAppBuilder:
        mock_app = AsyncMock()
        MockAppBuilder.return_value.token.return_value.build.return_value = mock_app
        await notifier.start()

    with patch.object(mock_app.bot, 'send_photo', new_callable=AsyncMock) as mock_send_photo:
        await notifier.send_telegram("Test message", photo_path="path/to/photo.png")
        mock_send_photo.assert_awaited_once()

@pytest.mark.asyncio
async def test_send_telegram_without_photo(notifier):
    with patch('utils.notifier.ApplicationBuilder') as MockAppBuilder:
        mock_app = AsyncMock()
        MockAppBuilder.return_value.token.return_value.build.return_value = mock_app
        await notifier.start()

    with patch.object(mock_app.bot, 'send_message', new_callable=AsyncMock) as mock_send_message:
        await notifier.send_telegram("Test message")
        mock_send_message.assert_awaited_once()

@pytest.mark.asyncio
async def test_send_telegram_no_application(notifier):
    """Testa send_telegram sem aplicação inicializada."""
    notifier.application = None
    await notifier.send_telegram("Test message") # Não deve gerar erro

@pytest.mark.asyncio
async def test_handle_start(notifier):
    """Testa o comando /start."""
    update = MagicMock()
    context = MagicMock()
    with patch.object(update.message, 'reply_text', new_callable=AsyncMock) as mock_reply:
        await notifier.handle_start(update, context)
        mock_reply.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_button(notifier):
    """Testa o callback dos botões."""
    update = MagicMock()
    context = MagicMock()
    query = MagicMock()
    query.data = 'iniciar'
    update.callback_query = query

    with patch.object(query, 'answer', new_callable=AsyncMock), \
            patch.object(query, 'edit_message_text', new_callable=AsyncMock) as mock_edit:
        await notifier.handle_button(update, context)
        mock_edit.assert_awaited_once_with("✅ Bot iniciado. Monitorando sinais...")

@pytest.mark.asyncio
async def test_add_trade(notifier):
    trade = {'timestamp': '2024-07-24 10:00:00', 'side': 'buy', 'price': 100, 'amount': 1}
    await notifier.add_trade(trade)
    assert notifier.trades_history == [trade]

@pytest.mark.asyncio
async def test_notify_trade(notifier):
    trade = {'timestamp': '2024-07-24 10:00:00', 'side': 'buy', 'price': 100, 'amount': 1}
    with patch.object(notifier, 'send_telegram', new_callable=AsyncMock) as mock_send:
        await notifier.notify_trade(trade)
        mock_send.assert_awaited_once()