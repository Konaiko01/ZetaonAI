from repositories.group_members_repository import GroupMembersRepository
from clients.evolution_client import EvolutionClient
from utils.logger import logger


#--------------------------------------------------------------------------------------------------------------------#
class GroupAuthorizationService:
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self, mongodb_instance, group_client: EvolutionClient):
        self.group_client = group_client
        self.group_repo = GroupMembersRepository(mongodb_instance)


#--------------------------------------------------------------------------------------------------------------------#


    async def authorize_user(self, phone_number: str, group_id: str) -> bool:
        try:
            logger.info(f"[GroupMembersRepository]Autorizando {phone_number} para grupo {group_id}")
            members = await self.group_repo.get_group_members(group_id)
            if not members:
                logger.debug(f"[GroupMembersRepository]Cache vazio para {group_id}, buscando da Evolution API")
                members = await self.group_client.get_group_participants(group_id)
                if not members:
                    logger.warning(f"[GroupMembersRepository]Não foi possível buscar membros de {group_id}")
                    return False
                await self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)
            is_member = await self.group_repo.is_member_in_group(group_id, phone_number)
            if is_member:
                logger.info(f"[GroupMembersRepository]Usuário {phone_number} AUTORIZADO para grupo {group_id}")
            else:
                logger.warning(f"[GroupMembersRepository]Usuário {phone_number} NÃO autorizado para grupo {group_id}")
            return is_member

        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro na autorização: {e}")
            return False


#--------------------------------------------------------------------------------------------------------------------#


    async def refresh_group_cache(self, group_id: str) -> bool:
        try:
            logger.info(f"[GroupMembersRepository]Atualizando cache do grupo {group_id}")
            members = await self.group_client.get_group_participants(group_id)
            if not members:
                logger.warning(f"[GroupMembersRepository]Não foi possível buscar membros de {group_id}")
                return False
            await self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)
            logger.info(f"[GroupMembersRepository]Cache do grupo {group_id} atualizado com sucesso")
            return True

        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao atualizar cache: {e}")
            return False


#--------------------------------------------------------------------------------------------------------------------#


    async def get_group_members(self, group_id: str) -> list[dict]:
        try:
            members = await self.group_repo.get_group_members(group_id)
            if not members:
                members = await self.group_client.get_group_participants(group_id)
                if members:
                    await self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)
            return members

        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao buscar membros: {e}")
            return []


#--------------------------------------------------------------------------------------------------------------------#


    async def is_user_in_any_authorized_group(
        self,
        phone_number: str,
        authorized_group_ids: list[str]
    ) -> bool:
        try:
            for group_id in authorized_group_ids:
                if await self.authorize_user(phone_number, group_id):
                    return True
            logger.info(f"[GroupMembersRepository]{phone_number} não é membro de nenhum grupo autorizado")
            return False

        except Exception as e:
            logger.error(f"[GroupMembersRepository]Erro ao verificar grupos: {e}")
            return False