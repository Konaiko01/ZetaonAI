from redis import Redis
import logging
import json
from typing import Any, Dict, List
from dotenv import load_dotenv
from utils.validators import validator_health
from config import settings

load_dotenv()

logger: logging.Logger = logging.getLogger(__name__)


class RedisQueue:
    def __init__(self):
        self._redis: Redis = Redis.from_url(  # type: ignore[arg-type]
            url=settings.redis_url,
            socket_connect_timeout=5,  # 5 segundos timeout
            socket_timeout=5,
            retry_on_timeout=True,
            max_connections=10,
        )
        self.batch_timeout = settings.batch_processing_delay
        self.check_health()

    def check_health(self) -> bool:
        """Verifica se o Redis está respondendo"""
        try:
            # Testa a conexão
            self._redis.ping()  # type: ignore
            self.is_healthy = True
            logger.info("Conexão com Redis estabelecida com sucesso")
        except (ConnectionError, TimeoutError, Exception) as e:
            self.is_healthy = False
            logger.error(f"Falha na conexão com Redis: {str(e)}")
        finally:
            return self.is_healthy

    @validator_health
    async def add_message(
        self,
        key: str,
        payload_data: Dict[str, Any],
        expire: int = 60 * 60 * 24,  # Significa o 1 dia em segundos
    ) -> None:
        """Adiciona mensagem à fila do Redis com verificação de saúde"""
        try:
            message_json = json.dumps(payload_data, ensure_ascii=False)
            self._redis.rpush(key, message_json)

            # Define expiração para a fila de mensagens
            self._redis.expire(key, expire)

            # Agenda o processamento desta chave
            await self._save_batch_processing(key)

            logger.info(f"Mensagem adicionada à fila para chave: {key}")
            logger.debug(f"Conteúdo da mensagem: {payload_data}")
        except Exception as e:
            logger.error(
                f"Erro ao adicionar mensagem ao Redis: {str(e)}", exc_info=True
            )
            raise e

    async def _save_batch_processing(
        self,
        id: str,
    ):
        """Agenda o processamento do batch para este id"""
        import time

        try:
            # Define um timestamp de expiração no Redis
            processing_key = f"batch_processing:{id}"
            expiry_time = time.time() + self.batch_timeout

            logger.info(f"AGENDANDO: {id} -> expira em {self.batch_timeout}")

            self._redis.set(processing_key, str(expiry_time))

            self._redis.expireat(processing_key, int(expiry_time + 60))

            logger.info(f"Lote agendado para {id} em {self.batch_timeout}s")

        except Exception as e:
            logger.error(f"Erro ao agendar batch para {id}: {e}")

    @validator_health
    def get_pending_messages(self, id: str) -> List[Dict[str, Any]]:
        """Recupera todas as mensagens pendentes e limpa a fila com verificação de saúde"""
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        key = f"whatsapp:{id}"

        try:
            logger.info(f"Buscando mensagens com chave: {key}")

            # Verifica se a chave existe
            if not self._redis.exists(key):
                logger.debug(f"Chave {key} não encontrada no Redis")
                return []

            redis_messages: List[bytes] = self._redis.lrange(key, 0, -1)  # type: ignore
            logger.info(f"Encontradas {len(redis_messages)} mensagens no Redis")

            self._redis.delete(key)

            result: List[Dict[str, Any]] = []
            for msg_bytes in redis_messages:
                try:
                    msg_str = msg_bytes.decode("utf-8")
                    message_dict: Dict[str, Any] = json.loads(msg_str)
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
        import time

        batch_keys: List[bytes] = (self._redis.keys("batch_processing:*"),)  # type: ignore
        phones_numbers: List[str] = []

        if batch_keys:
            logger.debug(f"Monitor: encontradas {len(batch_keys)} chaves de batch")

        for key in batch_keys:
            try:
                # Verifica se o lote expirou
                expiry_str: Any = self._redis.get(key)

                if expiry_str and float(expiry_str) <= time.time():
                    phones_numbers.append(key.decode().split(":")[1])
            except Exception as e:
                logger.error(f"Erro ao processar batch key {key}: {e}")
                continue

        return phones_numbers

    def delete(self, key: bytes | str) -> int:
        try:
            return self._redis.delete(key)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Erro ao deletar chave {key} do Redis: {e}", exc_info=True)
            raise e
