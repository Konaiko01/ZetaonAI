from datetime import datetime, timezone, timedelta
from utils.logger import logger
from typing import Any

#--------------------------------------------------------------------------------------------------------------------#
class GroupMembersRepository:
#--------------------------------------------------------------------------------------------------------------------#
    
    
    def __init__(self, mongodb_instance):
        self.db = mongodb_instance.database
        self.collection_name = "group_members"
        self.collection = self.db[self.collection_name]


#--------------------------------------------------------------------------------------------------------------------#


    async def create_indexes(self):
        try:
            await self.collection.create_index([("group_id", 1)])
            await self.collection.create_index([("expires_at", 1)])
            logger.info("[GroupMembersRepository]Índices de group_members (async) criados/verificados")
        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao criar índices (async): {e}")


#--------------------------------------------------------------------------------------------------------------------#


    async def save_group_members(
        self,
        group_id: str,
        group_name: str,
        members: list[dict[str, Any]],
        cache_duration_minutes: int = 60
    ) -> bool:
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=cache_duration_minutes)
            await self.collection.update_one(
                {"group_id": group_id},
                {
                    "$set": {
                        "group_id": group_id,
                        "group_name": group_name,
                        "members": members,
                        "member_count": len(members),
                        "cached_at": now,
                        "expires_at": expires_at,
                        "updated_at": now,
                    }
                },
                upsert=True
            )

            logger.info(
                f"[GroupMembersRepository]Membros do grupo {group_id} salvos/atualizados ({len(members)} membros)"
            )
            return True

        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao salvar membros do grupo: {e}")
            return False


#--------------------------------------------------------------------------------------------------------------------#


    async def get_group_members(self, group_id: str) -> list[dict[str, Any]]:
        try:
            now = datetime.now(timezone.utc)
            result = await self.collection.find_one({
                "group_id": group_id,
                "expires_at": {"$gt": now}
            })
            if result:
                logger.info(f"[GroupMembersRepository]Membros do grupo {group_id} encontrados no cache")
                return result.get("members", [])
            logger.debug(f"[GroupMembersRepository]Cache expirado ou não encontrado para grupo {group_id}")
            return []

        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao buscar membros do grupo: {e}")
            return []


#--------------------------------------------------------------------------------------------------------------------#


    async def is_member_in_group(self, group_id: str, auth_id: str) -> bool:
        try:
            members = await self.get_group_members(group_id)

            if not members:
                logger.debug(f"is_member_in_group: Lista de membros vazia para {group_id}")
                return False

            for member in members:
                member_jid = member.get("id", "")  
                member_lid = member.get("lid", "") 
                
                if auth_id in [member_jid, member_lid]:
                    logger.debug(f"ID {auth_id} é membro (JID/LID) do grupo {group_id}")
                    return True

            logger.debug(f"ID {auth_id} NÃO é membro (JID/LID) do grupo {group_id}")
            return False

        except Exception as e:
            logger.error(f"Erro ao verificar membro: {e}")
            return False

#--------------------------------------------------------------------------------------------------------------------#


    async def delete_group(self, group_id: str) -> bool:
        try:
            result = await self.collection.delete_one({"group_id": group_id})
            logger.info(f"[GroupMembersRepository]Grupo {group_id} deletado ({result.deleted_count} doc)")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao deletar grupo: {e}")
            return False
        

#--------------------------------------------------------------------------------------------------------------------#


    async def get_all_groups(self) -> list[dict[str, Any]]:
        try:
            now = datetime.now(timezone.utc)
            cursor = self.collection.find({"expires_at": {"$gt": now}}).sort("updated_at", -1)
            groups = await cursor.to_list(length=1000)
            logger.info(f"[GroupMembersRepository]Recuperados {len(groups)} grupos em cache")
            return groups
        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao listar grupos: {e}")
            return []