import logging
from typing import Any

# --- Importações dos Clientes (Injetados) ---
from clients.mongo_client import MongoDBClient
from clients.redis_client import RedisClient

# --- Importações das Implementações Reais ---
from repositories.context_repository import ContextRepository
from repositories.community_repository import CommunityRepository
from repositories.message_fragment_repository import MessageFragmentRepository

# --- Importações das Interfaces (para mapeamento) ---
from interfaces.repositories.context_repository_interface import IContextRepository
from interfaces.repositories.comunity_repository_interface import ICommunityRepository
from interfaces.repositories.message_fragment_repository_interface import IMessageFragmentRepository

logger = logging.getLogger(__name__)

class RepositoryContainer:
    
    def __init__(self, db_client: MongoDBClient, cache_client: RedisClient):
        """
        O Container de Repositórios recebe os CLIENTES (db e cache)
        e os injeta nos repositórios que ele cria.
        """
        self._repositories: dict[str, Any] = {}
        self._initialize_repositories(db_client, cache_client)
        logger.info("RepositoryContainer inicializado com todos os repositórios.")

    def _initialize_repositories(self, db_client: MongoDBClient, cache_client: RedisClient):
        """
        Instancia e registra todos os Repositórios Reais.
        """
        
        # --- Context Repository (Mongo) ---
        context_repo = ContextRepository(db_client=db_client)
        self.register_repository("IContextRepository", context_repo)

        # --- Community Repository (Mongo) ---
        community_repo = CommunityRepository(db_client=db_client)
        self.register_repository("ICommunityRepository", community_repo)
        
        # --- Message Fragment Repository (Redis) ---
        fragment_repo = MessageFragmentRepository(cache_client=cache_client)
        self.register_repository("IMessageFragmentRepository", fragment_repo)

    def register_repository(self, interface_name: str, repo_instance: Any):
        """Registra uma instância de repositório com um nome de interface."""
        self._repositories[interface_name] = repo_instance
        logger.info(f"Repositório '{interface_name}' registrado com sucesso.")

    def get_repository(self, interface_name: str) -> Any:
        """
        Recupera um repositório pelo nome da sua interface.
        (Ex: agent_container.py chamaria `repository_container.get_repository("IContextRepository")`)
        """
        repo = self._repositories.get(interface_name)
        
        if not repo:
             logger.error(f"Repositório '{interface_name}' não encontrado no container.")
             raise ValueError(f"Repositório '{interface_name}' não registrado.")
        
        return repo

    # --- Propriedades de Acesso (Opcional, mas útil) ---
    
    @property
    def context(self) -> IContextRepository:
        return self.get_repository("IContextRepository")

    @property
    def community(self) -> ICommunityRepository:
        return self.get_repository("ICommunityRepository")

    @property
    def fragments(self) -> IMessageFragmentRepository:
        return self.get_repository("IMessageFragmentRepository")