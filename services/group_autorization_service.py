from utils.logger import logger
from clients.evolution_client import EvolutionClient
from repositories.group_members_repository import GroupMembersRepository
import logging

logger_instance: logging.Logger = logging.getLogger(__name__)

class GroupAuthorizationService:
    """
    Serviço (Assíncrono) para autorizar usuários baseado em membros de grupo.
    """

    def __init__(self, mongodb_instance, group_client: EvolutionClient):
        # (O group_client agora é o EvolutionClient assíncrono)
        self.group_client = group_client
        self.group_repo = GroupMembersRepository(mongodb_instance)

    # --- MUDANÇA: 'async def' ---
    async def authorize_user(self, phone_number: str, group_id: str) -> bool:
        """Autorizar um usuário verificando se é membro do grupo (Assíncrono)."""
        try:
            logger_instance.info(f"Autorizando {phone_number} para grupo {group_id}")

            # --- MUDANÇA: 'await' ---
            members = await self.group_repo.get_group_members(group_id)

            if not members:
                logger_instance.debug(f"Cache vazio para {group_id}, buscando da Evolution API")
                # --- MUDANÇA: 'await' ---
                members = await self.group_client.get_group_participants(group_id)

                if not members:
                    logger_instance.warning(f"Não foi possível buscar membros de {group_id}")
                    return False

                # --- MUDANÇA: 'await' ---
                await self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)

            # --- MUDANÇA: 'await' ---
            is_member = await self.group_repo.is_member_in_group(group_id, phone_number)

            if is_member:
                logger_instance.info(f"Usuário {phone_number} AUTORIZADO para grupo {group_id}")
            else:
                logger_instance.warning(f"Usuário {phone_number} NÃO autorizado para grupo {group_id}")

            return is_member

        except Exception as e:
            logger_instance.error(f"Erro na autorização: {e}")
            return False

    # --- MUDANÇA: 'async def' ---
    async def refresh_group_cache(self, group_id: str) -> bool:
        """Forçar atualização do cache de um grupo (Assíncrono)."""
        try:
            logger_instance.info(f"Atualizando cache do grupo {group_id}")

            # --- MUDANÇA: 'await' ---
            members = await self.group_client.get_group_participants(group_id)

            if not members:
                logger_instance.warning(f"Não foi possível buscar membros de {group_id}")
                return False

            # --- MUDANÇA: 'await' ---
            await self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)

            logger_instance.info(f"Cache do grupo {group_id} atualizado com sucesso")
            return True

        except Exception as e:
            logger_instance.error(f"Erro ao atualizar cache: {e}")
            return False

    # --- MUDANÇA: 'async def' ---
    async def get_group_members(self, group_id: str) -> list[dict]:
        """Obter lista de membros de um grupo (Assíncrono)."""
        try:
            # --- MUDANÇA: 'await' ---
            members = await self.group_repo.get_group_members(group_id)

            if not members:
                # --- MUDANÇA: 'await' ---
                members = await self.group_client.get_group_participants(group_id)
                if members:
                    # --- MUDANÇA: 'await' ---
                    await self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)

            return members

        except Exception as e:
            logger_instance.error(f"Erro ao buscar membros: {e}")
            return []

    # --- MUDANÇA: 'async def' ---
    async def is_user_in_any_authorized_group(
        self,
        phone_number: str,
        authorized_group_ids: list[str]
    ) -> bool:
        """Verificar se usuário é membro de ALGUM grupo autorizado (Assíncrono)."""
        try:
            for group_id in authorized_group_ids:
                # --- MUDANÇA: 'await' ---
                if await self.authorize_user(phone_number, group_id):
                    return True

            logger_instance.info(f"{phone_number} não é membro de nenhum grupo autorizado")
            return False

        except Exception as e:
            logger_instance.error(f"Erro ao verificar grupos: {e}")
            return False