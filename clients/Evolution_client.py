import httpx  # <--- MUDANÇA
import asyncio # <--- MUDANÇA
import os
import re
import random
import base64
from utils.logger import logger
from interfaces.clients.chat_interface import IChat


class EvolutionAPIClient(IChat):
    def __init__(self):
        self._base_url = os.getenv("EVOLUTION_BASE_URL")
        self._instance_name = os.getenv("EVOLUTION_INSTANCE_NAME")
        self._headers = {
            "Content-Type": "application/json",
            "apikey": os.getenv("EVOLUTION_INSTANCE_KEY"),
        }
        # Cria um cliente assíncrono
        self.client = httpx.AsyncClient(timeout=30.0) # <--- MUDANÇA

    # ... (métodos __is_valid_request, __validate_message, etc. permanecem iguais) ...
    # ... (__validate_cell_number, _resolve_phone, __resolve_message, set_instance) ...
    # ... (is_valid_message, is_audio_message, is_image, is_file, get_message, get_phone) ...
    # ... (_get_audio_url) ...
    async def get_chat_id():
        pass
    async def get_phone_number():
        pass
    async def get_message():
        pass
    async def is_valid():
        pass
    async def get_audio_bytes(self, **kwargs) -> str: # <--- MUDANÇA (async def)
        endpoint = (
            f"{self._base_url}/chat/getBase64FromMediaMessage/{self._instance_name}"
        )
        payload = {
            "message": {"key": {"id": kwargs["data"]["key"]["id"]}},
            "convertToMp4": False,
        }

        try:
            # Usa o cliente async com 'await'
            response = await self.client.post(url=endpoint, json=payload, headers=self._headers) # <--- MUDANÇA
            response.raise_for_status()

            logger.info(
                f"[EVOLUTION] Recuperando audio da mensagem {kwargs['data']['key']['id']}"
            )
            return base64.b64decode(response.json().get("base64"))
        except Exception as e:
            logger.exception(
                f"[EVOLUTION] ❌ Falha ao obter audio: \n{to_json_dump(e)}"
            )
            raise e

    # ... (get_image_url, get_image_caption, get_file_url, get_file_caption, _resolve_url) ...

    async def send_message(self, phone: str, message: str) -> bool: # <--- MUDANÇA (async def)
        if not self.__validate_message(message) or not self.__validate_cell_number(
            phone
        ):
            return False

        url: str = self._resolve_url()
        payload: dict = {"number": self._resolve_phone(phone), "delay": 3000}

        try:
            messages: str = self.__resolve_message(message)

            for message in messages:
                if not message:
                    continue

                payload["text"] = message
                # Usa o cliente async com 'await'
                response = await self.client.post(url, json=payload, headers=self._headers) # <--- MUDANÇA

                logger.info(
                    f"[EVOLUTION] Enviando mensagem para o número {phone}: {message!r}"
                )
                response.raise_for_status()

                pause = random.randint(2, 3)
                await asyncio.sleep(pause) # <--- MUDANÇA (substitui time.sleep)

            return True
        except Exception as e:
            logger.exception(
                f"[EVOLUTION] ❌ Falha ao enviar mensagem: \n{to_json_dump(e)}"
            )
            raise e
            
    # Adicione um método para fechar o cliente http
    async def close(self):
        await self.client.aclose()