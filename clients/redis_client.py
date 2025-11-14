from interfaces.repositories.message_fragment_repository_interface import IMessageFragmentRepository
from interfaces.clients.queue_interface import IQueue
from typing import Any, Optional
from utils.logger import logger
import redis.asyncio as redis
import json
import os


#--------------------------------------------------------------------------------------------------------------------#
class RedisClient(IQueue, IMessageFragmentRepository):
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self):
        host = os.getenv("rHost")
        port = os.getenv("rPort")
        password = os.getenv("rPass")
        if not all([host, port, password]):
            logger.error("[RedisClient] Variáveis de ambiente rHost, rPort ou rPass não definidas.")
            raise ValueError("Configurações do Redis incompletas.")
        self.app = redis.Redis(
            host=host, 
            port=port, 
            password=password, 
            decode_responses=True 
        )
        logger.info("[RedisClient] Cliente (assíncrono) inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    async def push_to_queue(self, queue_key: str, message: Any):
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            await self.app.lpush(queue_key, message)
            logger.info(f"[RedisClient] Mensagem adicionada à fila '{queue_key}'.")

        except Exception as e:
            logger.error(f"[RedisClient] Erro ao adicionar à fila '{queue_key}': {e}", exc_info=True)

#--------------------------------------------------------------------------------------------------------------------#

    async def pop_from_queue(self, queue_key: str) -> Optional[str]:
        try:
            message = await self.app.rpop(queue_key)
            if message:
                logger.info(f"[RedisClient] Mensagem lida da fila '{queue_key}'.")
                return message
            return None
        
        except Exception as e:
            logger.error(f"[RedisClient] Erro ao ler da fila '{queue_key}': {e}", exc_info=True)
            return None

#--------------------------------------------------------------------------------------------------------------------#

    async def get_queue_fragments(self, queue_key: str) -> list[str]:
        try:
            fragments = await self.app.lrange(queue_key, 0, -1)
            return fragments
        
        except Exception as e:
            logger.error(f"[RedisClient] Erro ao ler fragmentos da fila '{queue_key}': {e}", exc_info=True)
            return []

#--------------------------------------------------------------------------------------------------------------------#

    async def delete_queue(self, queue_key: str):
        try:
            await self.app.delete(queue_key)
            logger.info(f"[RedisClient] Fila '{queue_key}' deletada.")

        except Exception as e:
            logger.error(f"[RedisClient] Erro ao deletar fila '{queue_key}': {e}", exc_info=True)

#--------------------------------------------------------------------------------------------------------------------#
            
    async def close(self):
        await self.app.aclose()

#--------------------------------------------------------------------------------------------------------------------#
    async def add_fragment(self, key: str, fragment: Any):
        logger.debug(f"[RedisClient] add_fragment (interface) -> push_to_queue")
        return await self.push_to_queue(queue_key=key, message=fragment)

#--------------------------------------------------------------------------------------------------------------------#

    async def get_and_clear_fragments(self, key: str) -> list[str]:
        logger.debug(f"[RedisClient] get_and_clear_fragments (interface) -> get_queue_fragments + delete_queue")
        try:
            fragments = await self.get_queue_fragments(key)
            if fragments:
                await self.delete_queue(key)
            return fragments
        except Exception as e:
            logger.error(f"[RedisClient] Erro em get_and_clear_fragments: {e}", exc_info=True)
            return []