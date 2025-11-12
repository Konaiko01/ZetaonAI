from redis.asyncio import Redis
import logging
import json
import threading
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from utils.validators import validator_health
from config import settings

load_dotenv()

logger: logging.Logger = logging.getLogger(__name__)


class RedisQueue:
    def __init__(self):
        self._local = threading.local()
        self._redis_url = settings.redis_url
        self.is_healthy = False
        self.batch_timeout = settings.debounce_delay

    @property
    def _redis(self):
        """Obtém a conexão Redis para a thread atual"""
        if not hasattr(self._local, "redis"):
            self._local.redis = Redis.from_url(  # type: ignore[arg-type]
                url=self._redis_url,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=10,
                decode_responses=True,
            )
        return self._local.redis

    async def check_health(self) -> bool:
        """Verifica se o Redis está respondendo (assíncrono)"""
        try:
            await self._redis.ping()  # type: ignore[attr-defined]
            self.is_healthy = True
            logger.info("Conexão com Redis estabelecida com sucesso")
        except Exception as e:
            self.is_healthy = False
            logger.error(f"Falha na conexão com Redis: {str(e)}")
        return self.is_healthy

    @validator_health
    async def add_message(
        self,
        id: str,
        payload_data: Dict[str, Any],
        expire: int = 60 * 60 * 24,  # 1 dia em segundos
    ) -> None:
        """Adiciona mensagem à fila do Redis com verificação de saúde"""
        key = f"whatsapp:{id}"
        try:
            message_json = json.dumps(payload_data, ensure_ascii=False)
            await self._redis.rpush(key, message_json)  # type: ignore[attr-defined]

            # Define expiração para a fila de mensagens
            await self._redis.expire(key, expire)

            # Agenda o processamento desta chave
            await self._save_debounce(id)

            logger.info(f"Mensagem adicionada à fila para chave: {key}")
            logger.debug(f"Conteúdo da mensagem: {payload_data}")
        except Exception as e:
            logger.error(
                f"Erro ao adicionar mensagem ao Redis: {str(e)}", exc_info=True
            )
            raise e

    async def _save_debounce(self, id: str) -> None:
        """Agenda o processamento do batch para este id"""
        import time

        try:
            # Define um timestamp de expiração no Redis
            processing_key = f"debounce:{id}"
            expiry_time = time.time() + self.batch_timeout

            logger.info(
                f"AGENDANDO: {processing_key} -> expira em {self.batch_timeout}"
            )

            await self._redis.set(processing_key, str(expiry_time))
            await self._redis.expireat(processing_key, int(expiry_time + 60))

            logger.info(f"Lote agendado para {processing_key} em {self.batch_timeout}s")

        except Exception as e:
            logger.error(f"Erro ao agendar batch para {id}: {e}")

    @validator_health
    async def get_pending_messages(self, id: str) -> List[Dict[str, Any]]:
        """Recupera todas as mensagens pendentes e limpa a fila com verificação de saúde"""
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        key = f"whatsapp:{id}"

        try:
            logger.info(f"Buscando mensagens com chave: {key}")

            # Verifica se a chave existe
            if not await self._redis.exists(key):
                logger.debug(f"Chave {key} não encontrada no Redis")
                return []

            redis_messages: List[bytes] = await self._redis.lrange(key, 0, -1)  # type: ignore[attr-defined]
            logger.info(f"Encontradas {len(redis_messages)} mensagens no Redis")  # type: ignore

            await self._redis.delete(key)

            result: List[Dict[str, Any]] = []
            for msg_bytes in redis_messages:  # type: ignore
                try:
                    message_dict: Dict[str, Any] = json.loads(msg_bytes)  # type: ignore
                    result.append(message_dict)
                    logger.debug(f"Mensagem decodificada: {message_dict}")
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Erro ao decodificar mensagem do Redis: {e}")
                    continue
            return result
        except Exception as e:
            logger.error(
                f"Erro ao recuperar mensagens do Redis: {str(e)}", exc_info=True
            )
            raise e

    @validator_health
    async def get_messages_batches(self) -> List[str]:
        """Recupera lotes de mensagens prontos para processamento"""
        import time

        try:
            batch_keys: list[str] = await self._redis.keys("debounce:*")  # type: ignore[attr-defined]
            phones_numbers: List[str] = []

            if batch_keys:
                logger.debug(f"Monitor: encontradas {len(batch_keys)} chaves de batch")

            for key in batch_keys:
                try:
                    # Verifica se o lote expirou
                    expiry_str: Optional[bytes] = await self._redis.get(key)

                    if expiry_str and float(expiry_str) <= time.time():
                        phones_numbers.append(key.split(":")[1])
                except Exception as e:
                    logger.error(f"Erro ao processar batch key {key}: {e}")
                    continue

            return phones_numbers
        except Exception as e:
            logger.error(f"Erro ao buscar batches: {e}")
            return []

    async def delete(self, key: str) -> int:
        """Deleta uma chave do Redis"""
        try:
            return await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Erro ao deletar chave {key} do Redis: {e}", exc_info=True)
            raise e

    async def close(self):
        """Fecha a conexão com Redis"""
        await self._redis.close()
