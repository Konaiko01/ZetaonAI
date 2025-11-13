import os
import logging
from typing import Any
from clients.evolution_client import EvolutionAPIClient
from clients.openai_client import OpenIAClient
from clients.mongo_client import MongoDBClient
from clients.redis_client import RedisClient
from clients.calendar_client import GCalendarClient

logger = logging.getLogger(__name__)

class ClientContainer:
    
    def __init__(self):
        self._clients: dict[str, Any] = {}
        self._initialize_clients()
        logger.info("ClientContainer inicializado com todos os clientes registrados.")

    def _initialize_clients(self):
        self.register_client("IAI", OpenIAClient())
        if os.getenv("APP_ENV") == "stage":
            self.register_client("IChat", EvolutionAPIClient()) 
        else:
            self.register_client("IChat", EvolutionAPIClient()) 
        self.register_client("ICalendar", GCalendarClient()) 
        self.register_client("MongoDBClient", MongoDBClient()) 
        self.register_client("RedisClient", RedisClient()) 
        self.register_client("IWebSearch", None) 
        self.register_client("IProspect", None)

    def register_client(self, interface_name: str, client_instance: Any):
        """Registra uma instância de cliente com um nome de interface."""
        if client_instance is None:
            logger.warning(f"Cliente para '{interface_name}' não foi fornecido (None). "
                           f"Serviços que dependem dele podem falhar ou usar mocks.")
        
        self._clients[interface_name] = client_instance
        logger.info(f"Cliente '{interface_name}' registrado com sucesso.")

    def get_client(self, interface_name: str) -> Any:
        """
        Recupera um cliente pelo nome da sua interface.
        Este é o método principal que os Agentes usarão.
        """
        client = self._clients.get(interface_name)
        
        if not client and interface_name not in ["IWebSearch", "IProspect"]: # Permite Mocks
             logger.error(f"Cliente '{interface_name}' não encontrado no container.")
             raise ValueError(f"Cliente '{interface_name}' não registrado ou não inicializado.")
        
        return client

    @property
    def ai(self) -> OpenIAClient: 
        """Retorna o cliente de IA (OpenIAClient)"""
        return self.get_client("IAI") 

    @property
    def chat(self) -> EvolutionAPIClient: 
        """Retorna o cliente de Chat (EvolutionClient)"""
        return self.get_client("IChat") 

    @property
    def crm(self) -> GCalendarClient: 
        """Retorna o cliente de Calendário/CRM (GCalendarClient)"""
        return self.get_client("ICalendar") 

    @property
    def database(self) -> MongoDBClient: 
        """Retorna o cliente de Banco de Dados (MongoDBClient)"""
        return self.get_client("MongoDBClient") 

    @property
    def cache(self) -> RedisClient: 
        """Retorna o cliente de Cache (RedisClient)"""
        return self.get_client("RedisClient") 