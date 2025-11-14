from utils.logger import logger
from interfaces.clients.chat_interface import IChat
import requests
import json
import os


class EvolutionClient(IChat):
    """Cliente para integração com Evolution API.

    Responsável por enviar mensagens via WhatsApp através da Evolution API.
    """

    def __init__(self):
        self._EVOLUTION_URL = os.getenv("EVOLUTION_URL") or os.getenv("evolution_url")
        self._EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") or os.getenv("evolution_token")
        self._EVOLUTION_SEND_PATH = os.getenv("EVOLUTION_SEND_PATH", "/messages")

    def get_message(self, data) -> str:
        """Extrair texto da mensagem do webhook."""
        try:
            return str(data.get("text", {}).get("message", ""))
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar mensagem: {e}')
            return ""

    def is_valid(self, message_data) -> bool:
        """Validar se a mensagem deve ser processada."""
        is_saida = message_data.get('fromMe', False)
        if is_saida:
            logger.debug("Mensagem de saída ignorada (Evolution).")
            return False
        return True

    def send_message(self, phone: str, output: str) -> bool:
        """Enviar mensagem via Evolution API.

        Args:
            phone: Número do telefone no formato internacional (ex: 5511999999999)
            output: Conteúdo da mensagem a enviar

        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            logger.info(f"Tentando enviar mensagem pela Evolution para {phone}.")

            url = f"{self._EVOLUTION_URL.rstrip('/')}{self._EVOLUTION_SEND_PATH}"

            headers = {
                'Content-Type': 'application/json',
                'apikey': self._EVOLUTION_API_KEY,
            }

            payload = json.dumps({
                "to": phone,
                "type": "text",
                "text": {"body": output}
            })

            response = requests.post(url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Mensagem enviada com sucesso para {phone}. Status: {response.status_code}")
            logger.debug(f"Resposta Evolution: {response.text}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f'[EvolutionClient] Erro ao enviar mensagem: {e}')
            return False
        except Exception as e:
            logger.error(f"[EvolutionClient] Erro inesperado: {e}")
            return False
