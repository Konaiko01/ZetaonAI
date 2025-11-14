from typing import Any
from clients.evolution_client import EvolutionClient
from clients.openai_client import OpenIAClient
from clients.mongo_client import MongoDBClient
from clients.redis_client import RedisClient
from utils.logger import logger

#--------------------------------------------------------------------------------------------------------------------#
class ClientContainer:
#--------------------------------------------------------------------------------------------------------------------# 
    def __init__(self):
        self._clients: dict[str, Any] = {}
        self._initialize_clients()
        logger.info("ClientContainer inicializado (sem calendário).")

#--------------------------------------------------------------------------------------------------------------------#

    def _initialize_clients(self):
        """Inicializa clientes que NÃO dependem de dados do DB."""
        self.register_client("IAI", OpenIAClient())
        self.register_client("IChat", EvolutionClient()) 
        self.register_client("MongoDBClient", MongoDBClient()) 
        self.register_client("RedisClient", RedisClient()) 
        
        # Clientes Mock/Futuros
        self.register_client("IWebSearch", None) 
        self.register_client("IProspect", None)
        
        # Apenas registra a "interface" como None por enquanto.
        # O main.py irá preenchê-la.
        self.register_client("ICalendar", None)

#--------------------------------------------------------------------------------------------------------------------#

    def register_client(self, interface_name: str, client_instance: Any):
        """Registra (ou sobrescreve) uma instância de cliente."""
        if client_instance is None:
            # (Não registra o log de warning se for ICalendar, pois esperamos que seja None)
            if interface_name not in ["ICalendar", "IWebSearch", "IProspect"]:
                logger.warning(f"Cliente para '{interface_name}' não foi fornecido (None).")
        
        self._clients[interface_name] = client_instance
        logger.info(f"Cliente '{interface_name}' registrado/atualizado.")

#--------------------------------------------------------------------------------------------------------------------#

    def get_client(self, interface_name: str) -> Any:
        client = self._clients.get(interface_name)
        if not client and interface_name not in ["IWebSearch", "IProspect", "ICalendar"]:
             logger.error(f"[ClientContainer] Cliente '{interface_name}' não encontrado no container.")
             raise ValueError(f"Cliente '{interface_name}' não registrado ou não inicializado.")
        return client

#--------------------------------------------------------------------------------------------------------------------#
   
    @property
    def ai(self) -> OpenIAClient: 
        return self.get_client("IAI") 

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def chat(self) -> EvolutionClient: 
        return self.get_client("IChat") 

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def database(self) -> MongoDBClient: 
        return self.get_client("MongoDBClient") 

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def cache(self) -> RedisClient: 
        return self.get_client("RedisClient") 