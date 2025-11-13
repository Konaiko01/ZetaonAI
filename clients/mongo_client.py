import os
from interfaces.clients.db_interface import IDB
from utils.logger import logger
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, Optional

class MongoDBClient(IDB):

    def __init__(self):
        connection = os.getenv("mUri")
        if not connection:
            logger.error("[MongoDBClient] Variável de ambiente 'mUri' não definida.")
            raise ValueError("Conexão com MongoDB 'mUri' não foi configurada.")
            
        self.app: AsyncIOMotorClient = AsyncIOMotorClient(connection)
        self.database = self.app["client_context"]
        logger.info("[MongoDBClient] Cliente (assíncrono) inicializado.")

    async def find_one(self, collection_key: str, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Busca um documento específico por um filtro."""
        try:
            collect = self.database[collection_key]
            document = await collect.find_one(filter)
            return document
        except Exception as e:
            logger.error(f"[MongoDBClient] Erro ao buscar em '{collection_key}': {e}", exc_info=True)
            return None

    async def insert_one(self, collection_key: str, data: Dict[str, Any]):
        """Insere um novo documento."""
        try:
            collect = self.database[collection_key]
            result = await collect.insert_one(data)
            logger.info(f"[MongoDBClient] Documento inserido em '{collection_key}' com id: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"[MongoDBClient] Erro ao inserir em '{collection_key}': {e}", exc_info=True)
            return None

    async def update_one(self, collection_key: str, filter: Dict[str, Any], data: Dict[str, Any], upsert: bool = False):
        """Atualiza um documento ou o insere (upsert)."""
        try:
            collect = self.database[collection_key]
            # Usa $set para não sobrescrever o documento, apenas atualizar os campos
            update_data = {"$set": data}
            result = await collect.update_one(filter, update_data, upsert=upsert)
            
            if result.matched_count > 0:
                logger.info(f"[MongoDBClient] Documento atualizado em '{collection_key}'.")
            elif result.upserted_id:
                logger.info(f"[MongoDBClient] Documento inserido (upsert) em '{collection_key}'.")
            
            return result
        except Exception as e:
            logger.error(f"[MongoDBClient] Erro ao atualizar/upsert em '{collection_key}': {e}", exc_info=True)
            return None
        
    