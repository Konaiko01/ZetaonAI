from interfaces.repositories.message_fragment_repository_interface import IMessageFragmentRepository
from clients.redis_client import RedisClient
from utils.logger import logger
from typing import Any
import json

#--------------------------------------------------------------------------------------------------------------------#
class MessageFragmentRepository(IMessageFragmentRepository):
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, cache_client: RedisClient):
        self.cache = cache_client
        logger.info("[MessageFragmentRepository] Inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    async def add_fragment(self, key: str, fragment: Any):
        logger.info(f"[MessageFragmentRepository] Adicionando fragmento à chave {key}...")
        await self.cache.push_to_queue(key, fragment)

#--------------------------------------------------------------------------------------------------------------------#

    async def get_and_clear_fragments(self, key: str) -> list[Any]:
        logger.info(f"[MessageFragmentRepository] Buscando e limpando fragmentos da chave {key}...")
        fragments_str = await self.cache.get_queue_fragments(key)
        if not fragments_str:
            return []
        await self.cache.delete_queue(key)
        fragments_str.reverse()
        fragments_deserialized = []
        for frag in fragments_str:
            try:
                fragments_deserialized.append(json.loads(frag))
            except json.JSONDecodeError:
                fragments_deserialized.append(frag) 
        logger.info(f"[MessageFragmentRepository] {len(fragments_deserialized)} fragmentos processados para {key}.")
        return fragments_deserialized

#--------------------------------------------------------------------------------------------------------------------#

    async def delete_queue(self, key: str):
        logger.info(f"[MessageFragmentRepository] Deletando fila {key}...")
        await self.cache.delete_queue(key)