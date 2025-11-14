from typing import Any, Dict
from datetime import datetime, timezone, timedelta
from utils.logger import logger
import logging

logger_instance: logging.Logger = logging.getLogger(__name__)


class GroupMembersRepository:
    """Repositório para gerenciar membros de grupos no MongoDB."""

    def __init__(self, mongodb_instance):
        self.db = mongodb_instance.db
        self.collection_name = "group_members"
        self.collection = self.db[self.collection_name]
        self._create_indexes()

    def _create_indexes(self):
        """Criar índices para melhor performance."""
        try:
            self.collection.create_index([("group_id", 1)])
            self.collection.create_index([("expires_at", 1)])
            logger_instance.info("Índices de group_members criados/verificados")
        except Exception as e:
            logger_instance.error(f"Erro ao criar índices: {e}")

    def save_group_members(
        self,
        group_id: str,
        group_name: str,
        members: list[Dict[str, Any]],
        cache_duration_minutes: int = 60
    ) -> bool:
        """Salvar lista de membros de um grupo com expiração.

        Args:
            group_id: JID do grupo (ex: 120363295648424210@g.us)
            group_name: Nome do grupo
            members: Lista de membros [{"id": "...", "admin": "..."}]
            cache_duration_minutes: Minutos até expiração do cache

        Returns:
            True se salvo com sucesso, False caso contrário
        """
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=cache_duration_minutes)

            result = self.collection.update_one(
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

    def get_group_members(self, group_id: str) -> list[Dict[str, Any]]:
        """Buscar membros de um grupo (se cache ainda é válido).

        Args:
            group_id: JID do grupo

        Returns:
            Lista de membros ou lista vazia se cache expirou/não existe
        """
        try:
            now = datetime.now(timezone.utc)

            result = self.collection.find_one({
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

    def is_member_in_group(self, group_id: str, phone_number: str) -> bool:
        """Verificar se um phone_number é membro de um grupo.

        Args:
            group_id: JID do grupo
            phone_number: Número do telefone (com ou sem @s.whatsapp.net)

        Returns:
            True se é membro, False caso contrário
        """
        try:
            members = self.get_group_members(group_id)

            # Normalizar phone_number para comparação
            phone_with_domain = f"{phone_number}@s.whatsapp.net"
            phone_only = phone_number.replace("@s.whatsapp.net", "")

            for member in members:
                member_id = member.get("id", "")
                if member_id in [phone_with_domain, phone_only, phone_number]:
                    logger_instance.debug(f"Telefone {phone_number} é membro do grupo {group_id}")
                    return True

            logger_instance.debug(f"Telefone {phone_number} NÃO é membro do grupo {group_id}")
            return False

        except Exception as e:
            logger_instance.error(f"Erro ao verificar membro: {e}")
            return False

    def delete_group(self, group_id: str) -> bool:
        """Deletar registro de um grupo (para testes ou limpeza).

        Args:
            group_id: JID do grupo

        Returns:
            True se deletado, False caso contrário
        """
        try:
            result = self.collection.delete_one({"group_id": group_id})
            logger_instance.info(f"Grupo {group_id} deletado ({result.deleted_count} doc)")
            return result.deleted_count > 0

        except Exception as e:
            logger_instance.error(f"Erro ao deletar grupo: {e}")
            return False

    def get_all_groups(self) -> list[Dict[str, Any]]:
        """Listar todos os grupos em cache.

        Returns:
            Lista de grupos
        """
        try:
            now = datetime.now(timezone.utc)

            results = self.collection.find({
                "expires_at": {"$gt": now}
            }).sort("updated_at", -1)

            groups = list(results)
            logger_instance.info(f"Recuperados {len(groups)} grupos em cache")
            return groups

        except Exception as e:
            logger_instance.error(f"Erro ao listar grupos: {e}")
            return []
