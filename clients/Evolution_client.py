from utils.logger import logger
from interfaces.clients.chat_interface import IChat
import httpx # <-- Trocado de 'requests' para 'httpx'
from typing import Any
import json
import os

class EvolutionClient(IChat):
    """
    Cliente para integração com Evolution API. (ASSÍNCRONO)
    Responsável por enviar mensagens via WhatsApp através da Evolution API.
    """

    def __init__(self):
        self._EVOLUTION_URL = os.getenv("EVOLUTION_URL") or os.getenv("evolution_url")
        self._EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") or os.getenv("evolution_token")
        self._EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "default")
        self._EVOLUTION_SEND_PATH = os.getenv("EVOLUTION_SEND_PATH", "/messages")

        if not self._EVOLUTION_URL or not self._EVOLUTION_API_KEY:
            logger.error("[EvolutionClient] EVOLUTION_URL ou EVOLUTION_API_KEY não definidos.")
            raise ValueError("Configuração da Evolution API incompleta.")

        # --- MUDANÇA ---
        # Inicializa um cliente HTTP assíncrono para reuso de conexão
        self.http_client = httpx.AsyncClient(
            base_url=self._EVOLUTION_URL.rstrip('/'),
            headers={
                'Content-Type': 'application/json',
                'apikey': self._EVOLUTION_API_KEY,
            },
            timeout=10.0
        )
        logger.info("[EvolutionClient] Cliente HTTP (httpx) inicializado.")
        # --- FIM DA MUDANÇA ---

    def get_phone_number(self, data: Any) -> str:
        """Extrai o JID do usuário (número) do webhook."""
        try:
            # Pega o 'remoteJid' que identifica o chat/usuário
            jid = data.get("key", {}).get("remoteJid", "")
            if not jid:
                # Fallback para outro local comum
                jid = data.get("remoteJid", "")
            
            # Remove o sufixo '@s.whatsapp.net' ou '@g.us'
            return jid.split('@')[0]
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar phone_number (remoteJid): {e}')
            return ""

    def get_chat_id(self, data: Any) -> str:
        """Extrai o ID do chat (JID) do webhook."""
        try:
            # Para a Evolution, o remoteJid é o ID do chat
            chat_id = data.get("key", {}).get("remoteJid", "")
            if not chat_id:
                chat_id = data.get("remoteJid", "")
            return chat_id
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar chat_id (remoteJid): {e}')
            return ""
        
    def get_message(self, data) -> str:
        # (Este método não faz I/O, permanece síncrono)
        try:
            return str(data.get("text", {}).get("message", ""))
        except Exception as e:
            logger.error(f'[EvolutionClient] Erro ao captar mensagem: {e}')
            return ""

    def is_valid(self, message_data) -> bool:
        # (Este método não faz I/O, permanece síncrono)
        is_saida = message_data.get('fromMe', False)
        if is_saida:
            logger.debug("Mensagem de saída ignorada (Evolution).")
            return False
        return True

    # --- MUDANÇA: 'async def' ---
    async def send_message(self, phone: str, output: str) -> bool:
        """Enviar mensagem via Evolution API (Assíncrono)."""
        try:
            logger.info(f"Tentando enviar mensagem pela Evolution para {phone}.")
            
            # O base_url já está no self.http_client
            url = self._EVOLUTION_SEND_PATH 

            payload = {
                "to": phone,
                "type": "text",
                "text": {"body": output}
            }

            # --- MUDANÇA: 'await' e 'httpx' ---
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()

            logger.info(f"Mensagem enviada com sucesso para {phone}. Status: {response.status_code}")
            return True

        # --- MUDANÇA: 'httpx.RequestError' ---
        except httpx.RequestError as e:
            logger.error(f'[EvolutionClient] Erro ao enviar mensagem: {e}')
            return False
        except Exception as e:
            logger.error(f"[EvolutionClient] Erro inesperado: {e}")
            return False
        
    async def get_group_participants(self, group_jid: str) -> list[dict]: # Removido o argumento 'instance'
        """Buscar lista de participantes de um grupo (Assíncrono)."""
        try:
            logger.info(f"Buscando participantes do grupo {group_jid} na instância {self._EVOLUTION_INSTANCE}")
            
            # --- INÍCIO DA CORREÇÃO ---
            url = f"/group/participants/{self._EVOLUTION_INSTANCE}" # <-- Usa a instância do .env
            # --- FIM DA CORREÇÃO ---
            
            params = {'groupJid': group_jid}

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            participants = data.get('participants', [])

            logger.info(f"Encontrados {len(participants)} participantes no grupo {group_jid}")
            return participants

        except httpx.RequestError as e:
            logger.error(f'[GroupClient] Erro ao buscar participantes: {e}')
            return []
        except Exception as e:
            logger.error(f"[GroupClient] Erro inesperado: {e}", exc_info=True)
            return []

    async def get_all_groups(self) -> list[dict]: # Removido o argumento 'instance'
        """Buscar lista de todos os grupos (Assíncrono)."""
        try:
            logger.info(f"Buscando todos os grupos da instância {self._EVOLUTION_INSTANCE}")

            # --- INÍCIO DA CORREÇÃO ---
            url = f"/group/fetchAllGroups/{self._EVOLUTION_INSTANCE}" # <-- Usa a instância do .env
            # --- FIM DA CORREÇÃO ---
            
            params = {'getParticipants': 'true'}

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            groups = response.json()
            logger.info(f"Encontrados {len(groups)} grupos")
            return groups

        except httpx.RequestError as e:
            logger.error(f'[GroupClient] Erro ao buscar grupos: {e}')
            return []
        except Exception as e:
            logger.error(f"[GroupClient] Erro inesperado: {e}", exc_info=True)
            return []