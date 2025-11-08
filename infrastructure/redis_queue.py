from redis import Redis
import logging
import json
from typing import Any, Optional, Dict, List
import os
from dotenv import load_dotenv
from utils.helpers import validator_health

load_dotenv()

logger: logging.Logger = logging.getLogger(__name__)


class RedisQueue:
    def __init__(self):
        self.redis: Redis = Redis.from_url(  # type: ignore[arg-type]
            url=os.getenv("REDIS_URL", ""),
            socket_connect_timeout=5,  # 5 segundos timeout
            socket_timeout=5,
            retry_on_timeout=True,
            max_connections=10,
        )
        self.expire: Optional[int] = None
        self.check_health()

    # Nota: o decorator `validator_health` é definido no nível do módulo
    # (fora da classe) e usado aqui como `@validator_health` nos métodos.

    def check_health(self) -> bool:
        """Verifica se o Redis está respondendo"""
        try:
            # Testa a conexão
            self.redis.ping()  # type: ignore
            self.is_healthy = True
            logger.info("Conexão com Redis estabelecida com sucesso")
        except (ConnectionError, TimeoutError, Exception) as e:
            self.is_healthy = False
            logger.error(f"Falha na conexão com Redis: {str(e)}")
        finally:
            return self.is_healthy

    @validator_health
    def add_message(
        self,
        id: str,
        payload_data: Dict[str, Any],
        expire: int = 60 * 60 * 24,  # Significa o 1 dia em segundos
    ) -> None:
        """Adiciona mensagem à fila do Redis com verificação de saúde"""
        key = f"whatsapp:{id}"
        self.expire = expire
        try:
            message_json = json.dumps(payload_data, ensure_ascii=False)
            self.redis.rpush(key, message_json)

            # Define expiração para a fila de mensagens
            self.redis.expire(key, self.expire)

            logger.info(f"Mensagem adicionada à fila para chave: {key}")
            logger.debug(f"Conteúdo da mensagem: {payload_data}")
        except Exception as e:
            logger.error(
                f"Erro ao adicionar mensagem ao Redis: {str(e)}", exc_info=True
            )
            raise e

    def add_message_unit(
        self,
        id: str,
        payload_data: Dict[str, Any],
        expire: int = 60 * 60 * 24,  # Significa o 1 dia em segundos
    ) -> bool:
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        self.expire = expire
        try:
            if self.redis.exists(id) == 1:
                logger.info(f"Mensagem já existe para {id}")
                return False
            self.redis.hset(id, mapping=payload_data)  # type: ignore

            # Define expiração para a fila de mensagens
            self.redis.expire(id, self.expire)

            logger.info(f"Mensagem do tipo unica foi adicionada à fila para {id}")
            logger.debug(f"Conteúdo da mensagem: {payload_data}")
            return True
        except Exception as e:
            logger.error(
                f"Erro ao adicionar mensagem do tipo unica ao Redis: {str(e)}",
                exc_info=True,
            )
            raise e

    def get_pending_messages(
        self, id: str, key_delete: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Recupera todas as mensagens pendentes e limpa a fila com verificação de saúde"""
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        key = f"whatsapp:{id}"
        if key_delete is None:
            key_delete = key

        try:
            logger.info(f"Buscando mensagens com chave: {key}")

            # Verifica se a chave existe
            if not self.redis.exists(key):
                logger.debug(f"Chave {key} não encontrada no Redis")
                return []

            redis_messages: List[bytes] = self.redis.lrange(key, 0, -1)  # type: ignore
            logger.info(f"Encontradas {len(redis_messages)} mensagens no Redis")

            self.redis.delete(key_delete)

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

    # Wrappers para uso externo (evitam o acesso direto a `self.redis`)
    def keys(self, pattern: str) -> List[bytes]:
        try:
            return self.redis.keys(pattern)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Erro ao listar chaves no Redis: {e}", exc_info=True)
            raise e

    def get(self, key: bytes | str) -> Optional[bytes]:
        try:
            return self.redis.get(key)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Erro ao obter chave {key} do Redis: {e}", exc_info=True)
            raise e

    def delete(self, key: bytes | str) -> int:
        try:
            return self.redis.delete(key)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Erro ao deletar chave {key} do Redis: {e}", exc_info=True)
            raise e

    def set(self, key: str, value: str, nx: bool = False) -> bool:
        try:
            # redis-py retorna True/False para set quando decode_responses=False
            return self.redis.set(key, value, nx=nx)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Erro ao setar chave {key} no Redis: {e}", exc_info=True)
            raise e

    def expireat(self, key: str, when: int) -> bool:
        try:
            return self.redis.expireat(key, when)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Erro ao setar expireat para {key}: {e}", exc_info=True)
            raise e

    def llen(self, key: str) -> int:
        try:
            return self.redis.llen(key)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Erro ao obter tamanho da lista {key}: {e}", exc_info=True)
            raise e

    def exists(self, key: str) -> int:
        try:
            return self.redis.exists(key)  # type: ignore[return-value]
        except Exception as e:
            logger.error(
                f"Erro ao checar existência da chave {key}: {e}", exc_info=True
            )
            raise e
