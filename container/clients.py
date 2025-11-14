import os
import logging
from typing import Any
from clients.evolution_client import EvolutionClient
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
        
        # Lógica da Evolution (mantida)
        if os.getenv("APP_ENV") == "stage":
            self.register_client("IChat", EvolutionClient()) 
        else:
            self.register_client("IChat", EvolutionClient()) 
        
        # --- INÍCIO DA MUDANÇA ---
        # Carrega o GCalendarClient usando o caminho do .env
        calendar_key_path = os.getenv("GCALENDAR_SERVICE_ACCOUNT_FILE_PATH")
        if not calendar_key_path:
            logger.warning("GCALENDAR_SERVICE_ACCOUNT_FILE_PATH não definido no .env. "
                           "O Agente de Agendamento usará MOCKS.")
            self.register_client("ICalendar", None)
        else:
            try:
                self.register_client("ICalendar", GCalendarClient(json_keyfile_path=calendar_key_path))
                logger.info("GCalendarClient (Conta de Serviço) inicializado.")
            except Exception as e:
                logger.error(f"Falha ao inicializar GCalendarClient com {calendar_key_path}: {e}")
                self.register_client("ICalendar", None)
        # --- FIM DA MUDANÇA ---
        
        self.register_client("MongoDBClient", MongoDBClient()) 
        self.register_client("RedisClient", RedisClient()) 
        self.register_client("IWebSearch", None) 
        self.register_client("IProspect", None)

    # (O restante do arquivo 'clients.py' permanece o mesmo)
    
    def register_client(self, interface_name: str, client_instance: Any):
        """Registra uma instância de cliente com um nome de interface."""
        if client_instance is None:
            logger.warning(f"Cliente para '{interface_name}' não foi fornecido (None). "
                           f"Serviços que dependem dele podem falhar ou usar mocks.")
        
        self._clients[interface_name] = client_instance
        logger.info(f"Cliente '{interface_name}' registrado com sucesso.")

    def get_client(self, interface_name: str) -> Any:
        # (Restante do código)
        client = self._clients.get(interface_name)
        if not client and interface_name not in ["IWebSearch", "IProspect", "ICalendar"]: # Permite Mocks
             logger.error(f"Cliente '{interface_name}' não encontrado no container.")
             raise ValueError(f"Cliente '{interface_name}' não registrado ou não inicializado.")
        return client
    
    @property
    def ai(self) -> OpenIAClient: 
        """Retorna o cliente de IA (OpenIAClient)"""
        return self.get_client("IAI") 

    @property
    def chat(self) -> EvolutionClient: 
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