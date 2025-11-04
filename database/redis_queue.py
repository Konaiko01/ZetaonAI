from redis import Redis
import logging
import json
from typing import Any, Optional, Dict, List
import os
from dotenv import load_dotenv

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

    def add_message(
        self,
        key: str,
        message_data: Dict[str, Any],
        expire: int = 60 * 60 * 24,  # Significa o 1 dia em segundos
    ) -> None:
        """Adiciona mensagem à fila do Redis com verificação de saúde"""
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        self.expire = expire
        try:
            message_json = json.dumps(message_data, ensure_ascii=False)

            self.redis.rpush(key, message_json)

            # Define expiração para a fila de mensagens
            self.redis.expire(key, self.expire)

            logger.info(f"Mensagem adicionada à fila para {id}, chave: {key}")
            logger.debug(f"Conteúdo da mensagem: {message_data}")
        except Exception as e:
            logger.error(
                f"Erro ao adicionar mensagem ao Redis: {str(e)}", exc_info=True
            )
            raise e

    def get_pending_messages(self, key: str) -> List[Dict[str, Any]]:
        """Recupera todas as mensagens pendentes e limpa a fila com verificação de saúde"""
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        try:
            logger.info(f"Buscando mensagens com chave: {key}")

            # Verifica se a chave existe
            if not self.redis.exists(key):
                logger.info(f"Chave {key} não encontrada no Redis")
                return []

            redis_messages: list[bytes] = self.redis.lrange(key, 0, -1)  # type: ignore
            logger.info(f"Encontradas {len(redis_messages)} mensagens no Redis")

            self.redis.delete(key)

            result: list[dict[str, Any]] = []
            for msg_bytes in redis_messages:
                try:
                    msg_str = msg_bytes.decode("utf-8")
                    message_dict: dict[str, Any] = json.loads(msg_str)
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

    def _group_messages_by_key(
        self, key: str, message: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        return []
