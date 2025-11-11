from utils.logger import logger
from interfaces.clients.chat_interface import IChat
import requests
import json
import os


class EvolutionClient(IChat):
    """Cliente esqueleto para a Evolution API.

    Observações:
    - Preencha os endpoints e formato de payload conforme a documentação da Evolution API.
    - Mantive a mesma assinatura usada pelo `ZAPICliet` para facilitar a troca sem precisar alterar
      quem chama `send_message(phone, output)`.
    """

    def __init__(self):
        
        self._EVOLUTION_URL = os.getenv("EVOLUTION_URL") or os.getenv("evolution_url")
        self._EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") or os.getenv("evolution_token")
        self._EVOLUTION_SEND_PATH = os.getenv("EVOLUTION_SEND_PATH", "/messages")

    def get_message(self, data) -> str:
        try:

            return str(data.get("text", {}).get("message", ""))
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar mensagem: {e}')

    def get_chat_id(self) -> str:
        return ""

    def get_phone_number(self) -> str:
        return ""

    def get_message(self) -> str:

        return ""

    def is_valid(self) -> bool:

        return True

    def send_message(self) -> bool:

        raise NotImplementedError("Use send_message(phone, output) com parâmetros")

    def is_valid(self, message_data):

        is_saida = message_data.get('fromMe', False)
        if is_saida:
            logger.debug("Mensagem de saída ignorada (Evolution).")
            return None

    def send_message(self, phone: str, output: str) -> bool:
        """Enviar mensagem via Evolution API.

        Este método é um esqueleto — substitua 'endpoint' e o formato do payload/headers
        de acordo com a documentação real da Evolution.
        """
        try:
            logger.info("Tentando enviar via Evolution API.")


            url = f"{self._EVOLUTION_URL.rstrip('/')}{self._EVOLUTION_SEND_PATH}"

            headers = {
                'Content-Type': 'application/json',
                'apikey': f"{self._EVOLUTION_API_KEY}",
            }

            payload = json.dumps({
                "to": phone,
                "type": "text",
                "text": {"body": output}
            })

            response = requests.post(url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Resposta enviada com sucesso pela Evolution para {phone}. Status: {response.status_code}")
            logger.debug(f"CORPO DA RESPOSTA Evolution: {response.text}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f'[EvolutionClient] Erro ao enviar mensagem: {e}')
            return False
        except Exception as e:
            logger.error(f"Erro inesperado na Evolution API: {e}")
            return False
