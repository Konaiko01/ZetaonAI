from motor.motor_asyncio import AsyncIOMotorClient
import logging
from typing import Any, Dict
from datetime import datetime, timezone
from config import settings

logger: logging.Logger = logging.getLogger(__name__)


class MongoDB:
    def __init__(self) -> None:
        self.client: Any = None
        self.db = None
        self.conversations = None
        self.is_healthy = False

    async def initialize_connection(self) -> None:
        """Inicializa a conexão com o MongoDB e verifica saúde"""
        from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

        try:
            self.client = AsyncIOMotorClient(
                settings.mongodb_uri, serverSelectionTimeoutMS=5000
            )
            # Testa a conexão imediatamente
            await self.client.admin.command("ping")
            self.db = self.client[settings.mongodb_db_name]
            self.conversations = self.db["conversations"]
            self.is_healthy = True

            # Cria índices apenas se a conexão estiver saudável
            await self._create_indexes()
            logger.info("Conexão com MongoDB estabelecida com sucesso")

        except (ServerSelectionTimeoutError, ConnectionFailure, Exception) as e:
            self.is_healthy = False
            logger.error(f"Falha na conexão com MongoDB: {str(e)}")
            # Mantém as referências para evitar erros, mas marca como não saudável
            if self.client:
                self.db = self.client[settings.mongodb_db_name]
                self.conversations = self.db["conversations"]

    async def check_health(self) -> bool:
        """Verifica se o MongoDB está respondendo"""
        if not self.is_healthy or self.client is None:
            return False

        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            self.is_healthy = False
            return False

    async def _create_indexes(self) -> None:
        """Cria índice para melhor performance nas consultas de expiração"""
        if not self.is_healthy or self.conversations is None:
            raise ConnectionError("MongoDB não está disponível")

        try:
            # Índice para expiração de conversas
            await self.conversations.create_index(
                [("phone_number", 1), ("expires_at", 1)]
            )

            # Índice para busca por telefone
            await self.conversations.create_index([("phone_number", 1)])

            logger.info("Índice do MongoDB criados/verificados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao criar índices: {str(e)}")

    async def save(
        self,
        phone_number: str,
        message_data: Dict[str, Any],
        role: str,
    ) -> None:
        """Salva uma mensagem no histórico da conversa.

        Garante que o documento contenha:
         - phone_number
         - messages: lista de objetos com type_message, message, created_at (por mensagem)
         - created_at (document-level, apenas na criação)
         - update_at (document-level, atualizado a cada save)
        """
        if not self.is_healthy or self.conversations is None:
            raise ConnectionError("MongoDB não está disponível")

        db = self.conversations
        try:
            now = datetime.now(timezone.utc)

            message_entry: Dict[str, Any] = {
                "role": role,
                "message": message_data,
            }

            await db.update_one(
                {"phone_number": phone_number},
                {
                    "$push": {
                        "messages": {
                            "$each": [message_entry],
                            "$slice": -80,  # Mantém as últimas 80 mensagens
                        }
                    },
                    "$setOnInsert": {
                        "created_at": now,
                    },
                    "$set": {
                        "update_at": now,
                    },
                },
                upsert=True,
            )
            logger.info(f"Conversa salva para {phone_number}")
        except Exception as e:
            logger.error(f"Erro ao salvar conversa: %s", e)
            raise e

    async def get_history(
        self,
        phone_number: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recupera o histórico de conversa, filtrando mensagens expiradas"""
        if not self.is_healthy or self.conversations is None:
            raise ConnectionError("MongoDB não está disponível")

        db = self.conversations
        try:
            # Busca a conversa do telefone
            result = await db.find_one(
                {"phone_number": phone_number},
                {
                    "messages": {"$slice": -limit},
                    "created_at": 1,
                },  # Pega as últimas 'limit' mensagens
            )

            if not result:
                return []

            messages = [msg for msg in result.get("messages", [])]

            logger.info(f"Recuperadas {len(messages)} mensagens para {phone_number}")
            return messages

        except Exception as e:
            logger.error(f"Erro ao recuperar histórico: {str(e)}")
            raise e

    async def close_connection(self) -> None:
        """Fecha a conexão com o MongoDB"""
        if self.client:
            self.client.close()
            self.is_healthy = False
            logger.info("Conexão com MongoDB fechada")
