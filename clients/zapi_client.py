from ..utils.logger import logger
from ..interfaces.chat_interface import IChat
import requests
import json
import os

class ZAPICliet(IChat):
    
    def __init__(self):
        self._Z_URL = os.getenv("zURL")
        self._Z_INSTANCIA = os.getenv("zIns")
        self._Z_TOKEN = os.getenv("zToken")
        self._S_Z_TOKEN = os.getenv("segzToken")

    def get_message(self, data) -> str:
        try:
            return str(data["text"]["message"])
        except:
            logger.error('[ZAPIClient]Erro ao captar mensagem enviada')

    def is_valid(self, message_data):
        is_saida = message_data.get('fromMe', False)
        if is_saida:
            logger.debug(f"Mensagem de saída ignorada.")
            return None
        
    def send_message(self, phone: str, output: str) -> bool:
        
        if (self.is_valid):
            try:
                logger.info("Tentando enviar via Z-API.")
                url = f"{self._Z_URL}/instances/{self._Z_INSTANCIA}/token/{self._Z_TOKEN}/send-text/" 
                headers = {
                    'Content-Type': 'application/json', 
                    'Client-Token': self._S_Z_TOKEN,
                }  
                payload = json.dumps({"phone": phone, "message": output})
                response = requests.post(url, headers=headers, data=payload, timeout=10)
                body_message = response.text 
                response.raise_for_status() 
                logger.info(f"Resposta enviada com sucesso pela Z-API para {phone}. Status: {response.status_code}")
                logger.info(f"CORPO DA RESPOSTA Z-API: {body_message}")  
                return True           
            except requests.exceptions.RequestException as e:
                logger.error(f'[ZAPIClient] Erro ao enviar mensagem')
                return False             
            except Exception as e:
                logger.error(f"Erro inesperado na Z-API: {e}")
                return False
