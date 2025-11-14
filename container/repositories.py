from interfaces.repositories.message_fragment_repository_interface import IMessageFragmentRepository
from interfaces.repositories.comunity_repository_interface import ICommunityRepository
from interfaces.repositories.context_repository_interface import IContextRepository
from repositories.message_fragment_repository import MessageFragmentRepository
from repositories.community_repository import CommunityRepository
from repositories.context_repository import ContextRepository
from clients.mongo_client import MongoDBClient
from clients.redis_client import RedisClient
from utils.logger import logger
from typing import Any

#--------------------------------------------------------------------------------------------------------------------#
class RepositoryContainer:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, db_client: MongoDBClient, cache_client: RedisClient):
        self._repositories: dict[str, Any] = {}
        self._initialize_repositories(db_client, cache_client)
        logger.info("RepositoryContainer inicializado com todos os repositórios.")

#--------------------------------------------------------------------------------------------------------------------#

    def _initialize_repositories(self, db_client: MongoDBClient, cache_client: RedisClient):
        context_repo = ContextRepository(db_client=db_client)
        self.register_repository("IContextRepository", context_repo)

        community_repo = CommunityRepository(db_client=db_client)
        self.register_repository("ICommunityRepository", community_repo)
        
        fragment_repo = MessageFragmentRepository(cache_client=cache_client)
        self.register_repository("IMessageFragmentRepository", fragment_repo)

#--------------------------------------------------------------------------------------------------------------------#

    def register_repository(self, interface_name: str, repo_instance: Any):
        self._repositories[interface_name] = repo_instance
        logger.info(f"Repositório '{interface_name}' registrado com sucesso.")

#--------------------------------------------------------------------------------------------------------------------#

    def get_repository(self, interface_name: str) -> Any:
        repo = self._repositories.get(interface_name)
        if not repo:
             logger.error(f"Repositório '{interface_name}' não encontrado no container.")
             raise ValueError(f"Repositório '{interface_name}' não registrado.")
        
        return repo

#--------------------------------------------------------------------------------------------------------------------#
    
    @property
    def context(self) -> IContextRepository:
        return self.get_repository("IContextRepository")

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def community(self) -> ICommunityRepository:
        return self.get_repository("ICommunityRepository")

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def fragments(self) -> IMessageFragmentRepository:
        return self.get_repository("IMessageFragmentRepository")