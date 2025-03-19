import requests
from decouple import config
from loguru import logger

class Notifier:
    def __init__(self):
        self.telegram_token = config('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = config('TELEGRAM_CHAT_ID')
        
        # Valida chat ID
        if not self.telegram_chat_id.lstrip('-').isdigit():
            logger.error("Chat ID inválido. Deve ser um número inteiro.")
            self.telegram_chat_id = None

    def send_telegram(self, message):
        """Envia mensagem com escape completo de caracteres."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("Credenciais do Telegram não configuradas")
            return
        
        # Escape de TODOS os caracteres reservados do MarkdownV2
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
            '-': '\\-',
            '=': '\\=',
            '|': '\\|',
            '{': '\\{',
            '}': '\\}',
            '.': '\\.',  # Escape do ponto
            '!': '\\!',
            '/': '\\/',  # Escape da barra
            ':': '\\:'  # Escape do dois-pontos
        }))
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': escaped_message,
            'parse_mode': 'MarkdownV2'
        }
        
        try:
            response = requests.post(url, json=payload)
            logger.debug(f"Resposta do Telegram: {response.status_code} - {response.text}")
            
            if response.status_code == 400:
                # Fallback para texto simples
                payload['parse_mode'] = None
                response = requests.post(url, json=payload)
                logger.debug(f"Tentativa sem formatação: {response.status_code}")
                
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP: {e}")
        except Exception as e:
            logger.error(f"Erro desconhecido: {e}")