from typing import Any, Dict, List # Adicionado List
from datetime import datetime, timezone, timedelta
from utils.logger import logger
import logging

logger_instance: logging.Logger = logging.getLogger(__name__)

class GroupMembersRepository:
    """Repositório (Assíncrono) para gerenciar membros de grupos no MongoDB."""

    def __init__(self, mongodb_instance):
        self.db = mongodb_instance.database
        self.collection_name = "group_members"
        self.collection = self.db[self.collection_name]
        # --- MUDANÇA ---
        # Removido _create_indexes() de __init__, pois não pode ser async.
        # Chame 'await repo.create_indexes()' na inicialização da sua aplicação.
        # --- FIM DA MUDANÇA ---

    # --- MUDANÇA: 'async def' ---
    async def create_indexes(self):
        """Criar índices para melhor performance (deve ser chamado na inicialização)."""
        try:
            # --- MUDANÇA: 'await' ---
            await self.collection.create_index([("group_id", 1)])
            await self.collection.create_index([("expires_at", 1)])
            logger_instance.info("Índices de group_members (async) criados/verificados")
        except Exception as e:
            logger_instance.error(f"Erro ao criar índices (async): {e}")

    # --- MUDANÇA: 'async def' ---
    async def save_group_members(
        self,
        group_id: str,
        group_name: str,
        members: list[Dict[str, Any]],
        cache_duration_minutes: int = 60
    ) -> bool:
        """Salvar lista de membros de um grupo com expiração (Assíncrono)."""
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=cache_duration_minutes)

            # --- MUDANÇA: 'await' ---
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

            logger_instance.info(
                f"Membros do grupo {group_id} salvos/atualizados ({len(members)} membros)"
            )
            return True

        except Exception as e:
            logger_instance.error(f"Erro ao salvar membros do grupo: {e}")
            return False

    # --- MUDANÇA: 'async def' ---
    async def get_group_members(self, group_id: str) -> List[Dict[str, Any]]: # Usando List
        """Buscar membros de um grupo (se cache ainda é válido) (Assíncrono)."""
        try:
            now = datetime.now(timezone.utc)

            # --- MUDANÇA: 'await' ---
            result = await self.collection.find_one({
                "group_id": group_id,
                "expires_at": {"$gt": now}
            })

            if result:
                logger_instance.info(f"Membros do grupo {group_id} encontrados no cache")
                return result.get("members", [])

            logger_instance.debug(f"Cache expirado ou não encontrado para grupo {group_id}")
            return []

        except Exception as e:
            logger_instance.error(f"Erro ao buscar membros do grupo: {e}")
            return []

    # --- MUDANÇA: 'async def' ---
    async def is_member_in_group(self, group_id: str, auth_id: str) -> bool:
        """
        Verificar se um 'auth_id' (que pode ser um @lid ou @s.whatsapp.net) 
        é membro de um grupo, comparando IDs exatos.
        """
        try:
            # Busca os membros do grupo (do Mongo)
            members = await self.get_group_members(group_id)

            if not members:
                logger_instance.debug(f"is_member_in_group: Lista de membros vazia para {group_id}")
                return False

            # Compara o ID de autorização (auth_id) diretamente com os 'id' do banco.
            # (ex: '18945184641119@lid' == '18945184641119@lid')
            for member in members:
                member_id = member.get("id", "")
                if member_id == auth_id: 
                    logger_instance.debug(f"ID {auth_id} é membro do grupo {group_id}")
                    return True

            logger_instance.debug(f"ID {auth_id} NÃO é membro do grupo {group_id}")
            return False

        except Exception as e:
            logger_instance.error(f"Erro ao verificar membro: {e}")
            return False

    # --- MUDANÇA: 'async def' ---
    async def delete_group(self, group_id: str) -> bool:
        """Deletar registro de um grupo (Assíncrono)."""
        try:
            # --- MUDANÇA: 'await' ---
            result = await self.collection.delete_one({"group_id": group_id})
            logger_instance.info(f"Grupo {group_id} deletado ({result.deleted_count} doc)")
            return result.deleted_count > 0

        except Exception as e:
            logger_instance.error(f"Erro ao deletar grupo: {e}")
            return False

    # --- MUDANÇA: 'async def' ---
    async def get_all_groups(self) -> List[Dict[str, Any]]: # Usando List
        """Listar todos os grupos em cache (Assíncrono)."""
        try:
            now = datetime.now(timezone.utc)

            # --- MUDANÇA: 'await' e 'to_list' ---
            cursor = self.collection.find({
                "expires_at": {"$gt": now}
            }).sort("updated_at", -1)
            
            groups = await cursor.to_list(length=1000) # Limite de 1000 grupos
            # --- FIM DA MUDANÇA ---

            logger_instance.info(f"Recuperados {len(groups)} grupos em cache")
            return groups

        except Exception as e:
            logger_instance.error(f"Erro ao listar grupos: {e}")
            return []