from interfaces.repositories.context_repository_interface import IContextRepository
from clients.mongo_client import MongoDBClient
from utils.logger import logger
from typing import Any, Optional

#--------------------------------------------------------------------------------------------------------------------#
class ContextRepository(IContextRepository):
#--------------------------------------------------------------------------------------------------------------------#

    _COLLECTION_NAME = "user_contexts"

#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, db_client: MongoDBClient):
        self.db = db_client
        logger.info("[ContextRepository] Inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    async def get_context(self, phone: str) -> Optional[dict[str, Any]]:
        logger.info(f"[ContextRepository] Buscando contexto para {phone}...")
        filter = {"phone": phone}
        context_data = await self.db.find_one(self._COLLECTION_NAME, filter)
        if context_data:
            context_data.pop("_id", None)
            return context_data
        return None

#--------------------------------------------------------------------------------------------------------------------#

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