import os
import json
import redis.asyncio as redis
from interfaces.clients.queue_interface import IQueue
from utils.logger import logger
from typing import List, Any, Optional

class RedisClient(IQueue):

    def __init__(self):
        host = os.getenv("rHost")
        port = os.getenv("rPort")
        password = os.getenv("rPass")
        
        if not all([host, port, password]):
            logger.error("[RedisClient] Variáveis de ambiente rHost, rPort ou rPass não definidas.")
            raise ValueError("Configurações do Redis incompletas.")

        # Usa o cliente Assíncrono
        self.app = redis.Redis(
            host=host, 
            port=port, 
            password=password, 
            decode_responses=True 
        )
        logger.info("[RedisClient] Cliente (assíncrono) inicializado.")

    async def push_to_queue(self, queue_key: str, message: Any):
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
                
            await self.app.lpush(queue_key, message)
            logger.info(f"[RedisClient] Mensagem adicionada à fila '{queue_key}'.")
        except Exception as e:
            logger.error(f"[RedisClient] Erro ao adicionar à fila '{queue_key}': {e}", exc_info=True)

    async def pop_from_queue(self, queue_key: str) -> Optional[str]:
        try:
            # RPOP remove e retorna o último elemento (comportamento de fila com LPUSH)
            message = await self.app.rpop(queue_key)
            if message:
                logger.info(f"[RedisClient] Mensagem lida da fila '{queue_key}'.")
                return message
            return None
        except Exception as e:
            logger.error(f"[RedisClient] Erro ao ler da fila '{queue_key}': {e}", exc_info=True)
            return None
            
    async def get_queue_fragments(self, queue_key: str) -> List[str]:
        try:
            # LRANGE 0 -1 pega todos os elementos da lista
            fragments = await self.app.lrange(queue_key, 0, -1)
            return fragments
        except Exception as e:
            logger.error(f"[RedisClient] Erro ao ler fragmentos da fila '{queue_key}': {e}", exc_info=True)
            return []

    async def delete_queue(self, queue_key: str):
        try:
            await self.app.delete(queue_key)
            logger.info(f"[RedisClient] Fila '{queue_key}' deletada.")
        except Exception as e:
            logger.error(f"[RedisClient] Erro ao deletar fila '{queue_key}': {e}", exc_info=True)
            
    async def close(self):
        await self.app.aclose()