from interfaces.repositories.context_repository_interface import IContextRepository
from clients.mongo_client import MongoDBClient
from utils.logger import logger
from typing import Any, Optional

class ContextRepository(IContextRepository):
    
    _COLLECTION_NAME = "user_contexts"
    _HISTORY_LIMIT = 10 

    def __init__(self, db_client: MongoDBClient):
        self.db = db_client
        logger.info("[ContextRepository] Inicializado.")

    async def get_context(self, phone: str) -> Optional[dict[str, Any]]:
        logger.info(f"[ContextRepository] Buscando contexto para {phone} (limit: {self._HISTORY_LIMIT})...")
        filter = {"phone": phone}
        projection = {
            "phone": 1, 
            "history": {"$slice": -self._HISTORY_LIMIT} 
        }
        context_data = await self.db.find_one(
            self._COLLECTION_NAME, 
            filter,
            projection=projection
        )
        if context_data:
            context_data.pop("_id", None)
            history = context_data.get("history", [])
            if history:
                first_valid_index = 0
                for i, msg in enumerate(history):
                    if msg.get("role") != "tool":
                        first_valid_index = i
                        break
                    else:
                        if i == 0:
                            first_valid_index = -1 
                if first_valid_index > 0:
                    logger.warning(f"Contexto para {phone} continha 'tool' messages órfãs. Removendo as {first_valid_index} primeiras mensagens.")
                    context_data["history"] = history[first_valid_index:]
                elif first_valid_index == -1:
                     logger.warning(f"Contexto para {phone} continha apenas 'tool' messages. Retornando histórico vazio.")
                     context_data["history"] = []

            return context_data
        return None

    async def save_context(self, phone: str, context: dict[str, Any]):
        logger.info(f"[ContextRepository] Salvando contexto para {phone}...")
        filter = {"phone": phone}
        context_data_to_save = context.copy()
        context_data_to_save["phone"] = phone 
        
        await self.db.update_one(
            self._COLLECTION_NAME, 
            filter, 
            context_data_to_save, 
            upsert=True
        )