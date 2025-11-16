from utils.logger import logger
from interfaces.clients.chat_interface import IChat
import httpx
from typing import Any
import os

#--------------------------------------------------------------------------------------------------------------------#
class EvolutionClient(IChat):
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self):
        self._EVOLUTION_URL = os.getenv("EVOLUTION_URL") or os.getenv("evolution_url")
        self._EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") or os.getenv("evolution_token")
        self._EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "default")
        self._EVOLUTION_SEND_PATH = (f"{self._EVOLUTION_URL}/message/sendText/{self._EVOLUTION_INSTANCE}")
        if not self._EVOLUTION_URL or not self._EVOLUTION_API_KEY:
            logger.error("[EvolutionClient] EVOLUTION_URL ou EVOLUTION_API_KEY não definidos.")
            raise ValueError("Configuração da Evolution API incompleta.")
        self.http_client = httpx.AsyncClient(
            base_url=self._EVOLUTION_URL.rstrip('/'),
            headers={
                'Content-Type': 'application/json',
                'apikey': self._EVOLUTION_API_KEY,
            },
            timeout=10.0
        )
        logger.info("[EvolutionClient] Cliente HTTP (httpx) inicializado.")


#--------------------------------------------------------------------------------------------------------------------#

    def get_phone_number(self, data: Any) -> str:
        try:
            jid = data.get("key", {}).get("remoteJid", "")
            if not jid:
                jid = data.get("remoteJid", "")
            return jid.split('@')[0]
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar phone_number (remoteJid): {e}')
            return ""

#--------------------------------------------------------------------------------------------------------------------#

    def get_chat_id(self, data: Any) -> str:
        try:
            chat_id = data.get("key", {}).get("remoteJid", "")
            if not chat_id:
                chat_id = data.get("remoteJid", "")
            return chat_id
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar chat_id (remoteJid): {e}')
            return ""

#--------------------------------------------------------------------------------------------------------------------#

    def get_message(self, data) -> str:
        try:
            return str(data.get("text", {}).get("message", ""))
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar mensagem: {e}')
            return ""

#--------------------------------------------------------------------------------------------------------------------#

    def is_valid(self, message_data) -> bool:
        is_saida = message_data.get('fromMe', False)
        if is_saida:
            logger.debug("[EvolutionClient] Mensagem de saída ignorada (Evolution).")
            return False
        return True


#--------------------------------------------------------------------------------------------------------------------#


    async def send_message(self, phone: str, output: str) -> bool:
        try:
            logger.info(f"[EvolutionClient] Tentando enviar mensagem pela Evolution para {phone}.")
            url = self._EVOLUTION_SEND_PATH 
            payload = {
                "number": phone,
                "text": output
            }
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"[EvolutionClient] Mensagem enviada com sucesso para {phone}. Status: {response.status_code}")
            return True

        except httpx.RequestError as e:
            logger.error(f'[EvolutionClient] Erro ao enviar mensagem: {e}')
            return False
        except Exception as e:
            logger.error(f"[EvolutionClient] Erro inesperado: {e}")
            return False
        

#--------------------------------------------------------------------------------------------------------------------#


    async def get_group_participants(self, group_jid: str) -> list[dict]: 
        try:
            logger.info(f"[EvolutionClient] Buscando participantes do grupo {group_jid} na instância {self._EVOLUTION_INSTANCE}")
            url = f"/group/participants/{self._EVOLUTION_INSTANCE}" 
            params = {'groupJid': group_jid}
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            participants = data.get('participants', [])
            logger.info(f"[EvolutionClient] Encontrados {len(participants)} participantes no grupo {group_jid}")
            return participants

        except httpx.RequestError as e:
            logger.error(f'[EvolutionClient] Erro ao buscar participantes: {e}')
            return []
        except Exception as e:
            logger.error(f"[EvolutionClient] Erro inesperado: {e}", exc_info=True)
            return []


#--------------------------------------------------------------------------------------------------------------------#


    async def get_all_groups(self) -> list[dict]: 
        try:
            logger.info(f"[EvolutionClient] Buscando todos os grupos da instância {self._EVOLUTION_INSTANCE}")
            url = f"/group/fetchAllGroups/{self._EVOLUTION_INSTANCE}" 
            params = {'getParticipants': 'true'}
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            groups = response.json()
            logger.info(f"[EvolutionClient] Encontrados {len(groups)} grupos")
            return groups

        except httpx.RequestError as e:
            logger.error(f'[EvolutionClient] Erro ao buscar grupos: {e}')
            return []
        except Exception as e:
            logger.error(f"[EvolutionClient] Erro inesperado: {e}", exc_info=True)
            return []