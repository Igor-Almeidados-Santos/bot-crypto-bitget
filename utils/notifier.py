import requests
from decouple import config
from loguru import logger

class Notifier:
    def __init__(self):
        self.telegram_token = config('TELEGRAM_BOT_TOKEN', default=None)
        self.telegram_chat_id = config('TELEGRAM_CHAT_ID', default=None)
        logger.debug(f"Telegram Token: {self.telegram_token}")
        logger.debug(f"Telegram Chat ID: {self.telegram_chat_id}")

    def send_telegram(self, message):
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("Credenciais do Telegram não configuradas")
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        try:
            response = requests.post(url, json=payload)
            logger.debug(f"Resposta do Telegram: {response.status_code} - {response.text}")
            if response.status_code == 400:
                logger.error("Erro 400: Chat não encontrado. Verifique o chat_id e permissões do bot.")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Falha no Telegram: {e}")

    # Novo método para substituir notify_all()
    def notify(self, message):
        """Envia notificação apenas para Telegram."""
        self.send_telegram(message)