from interfaces.repositories.comunity_repository_interface import ICommunityRepository
from clients.mongo_client import MongoDBClient
from typing import Dict, Any, Optional
from utils.logger import logger

#--------------------------------------------------------------------------------------------------------------------#
class CommunityRepository(ICommunityRepository):
#--------------------------------------------------------------------------------------------------------------------#
   
    _COLLECTION_NAME = "community_members"
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, db_client: MongoDBClient):
        self.db = db_client
        logger.info("[CommunityRepository] Inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    async def get_member(self, phone: str) -> Optional[Dict[str, Any]]:
        logger.info(f"[CommunityRepository] Buscando membro {phone}...")
        filter = {"phone": phone}
        member_data = await self.db.find_one(self._COLLECTION_NAME, filter)
        
        if member_data:
            member_data.pop("_id", None)
            return member_data
        return None

#--------------------------------------------------------------------------------------------------------------------#

    async def add_member(self, member_data: Dict[str, Any]):
        """Adiciona um novo membro."""
        phone = member_data.get("phone")
        if not phone:
            logger.error("[CommunityRepository] Tentativa de adicionar membro sem 'phone'.")
            return

        if await self.get_member(phone):
            logger.warning(f"[CommunityRepository] Membro {phone} já existe.")
            return
        logger.info(f"[CommunityRepository] Adicionando novo membro {phone}...")
        await self.db.insert_one(self._COLLECTION_NAME, member_data)