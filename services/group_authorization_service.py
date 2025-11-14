from utils.logger import logger
from clients.group_client import GroupClient
from infrastructure.group_members_repository import GroupMembersRepository
import logging

logger_instance: logging.Logger = logging.getLogger(__name__)


class GroupAuthorizationService:
    """Serviço para autorizar usuários baseado em membros de grupo.

    Valida se um phone_number é membro de um grupo autorizado.
    Usa cache no MongoDB com expiração configurável.
    """

    def __init__(self, mongodb_instance, group_client: GroupClient = None):
        self.group_client = group_client or GroupClient()
        self.group_repo = GroupMembersRepository(mongodb_instance)

    def authorize_user(self, phone_number: str, group_id: str) -> bool:
        """Autorizar um usuário verificando se é membro do grupo.

        Fluxo:
        1. Tenta buscar membros do cache (se não expirou)
        2. Se cache vazio/expirado, busca da Evolution API
        3. Salva no cache
        4. Verifica se phone_number está na lista

        Args:
            phone_number: Número do telefone do usuário
            group_id: JID do grupo (ex: 120363295648424210@g.us)

        Returns:
            True se autorizado, False caso contrário
        """
        try:
            logger_instance.info(f"Autorizando {phone_number} para grupo {group_id}")

            # Tenta buscar do cache
            members = self.group_repo.get_group_members(group_id)

            # Se cache vazio, busca da Evolution
            if not members:
                logger_instance.debug(f"Cache vazio para {group_id}, buscando da Evolution API")
                members = self.group_client.get_group_participants(group_id)

                if not members:
                    logger_instance.warning(f"Não foi possível buscar membros de {group_id}")
                    return False

                # Salva no cache
                self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)

            # Verifica se phone_number está na lista
            is_member = self.group_repo.is_member_in_group(group_id, phone_number)

            if is_member:
                logger_instance.info(f"Usuário {phone_number} AUTORIZADO para grupo {group_id}")
            else:
                logger_instance.warning(f"Usuário {phone_number} NÃO autorizado para grupo {group_id}")

            return is_member

        except Exception as e:
            logger_instance.error(f"Erro na autorização: {e}")
            return False

    def refresh_group_cache(self, group_id: str) -> bool:
        """Forçar atualização do cache de um grupo.

        Útil quando há mudanças de membros no grupo.

        Args:
            group_id: JID do grupo

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            logger_instance.info(f"Atualizando cache do grupo {group_id}")

            members = self.group_client.get_group_participants(group_id)

            if not members:
                logger_instance.warning(f"Não foi possível buscar membros de {group_id}")
                return False

            self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)

            logger_instance.info(f"Cache do grupo {group_id} atualizado com sucesso")
            return True

        except Exception as e:
            logger_instance.error(f"Erro ao atualizar cache: {e}")
            return False

    def get_group_members(self, group_id: str) -> list[dict]:
        """Obter lista de membros de um grupo.

        Args:
            group_id: JID do grupo

        Returns:
            Lista de membros com id e admin status
        """
        try:
            # Tenta cache primeiro
            members = self.group_repo.get_group_members(group_id)

            if not members:
                # Se vazio, busca da Evolution
                members = self.group_client.get_group_participants(group_id)
                if members:
                    self.group_repo.save_group_members(group_id, f"Grupo {group_id}", members)

            return members

        except Exception as e:
            logger_instance.error(f"Erro ao buscar membros: {e}")
            return []

    def is_user_in_any_authorized_group(
        self,
        phone_number: str,
        authorized_group_ids: list[str]
    ) -> bool:
        """Verificar se usuário é membro de ALGUM grupo autorizado.

        Args:
            phone_number: Número do telefone
            authorized_group_ids: Lista de JIDs de grupos autorizados

        Returns:
            True se for membro de pelo menos um grupo, False caso contrário
        """
        try:
            for group_id in authorized_group_ids:
                if self.authorize_user(phone_number, group_id):
                    return True

            logger_instance.info(f"{phone_number} não é membro de nenhum grupo autorizado")
            return False

        except Exception as e:
            logger_instance.error(f"Erro ao verificar grupos: {e}")
            return False
