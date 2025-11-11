from clients.calendar_client import *
from clients.mongo_client import MongoDBClient
from clients.openai_client import OpenIAClient
from clients.redis_client import RedisClient
from clients.evolution_client import EvolutionClient


class ClientsContainer():
	"""Container simples para instanciar clientes.

	Atualmente este projeto utiliza exclusivamente o `EvolutionClient` para envio de
	mensagens (integração com Evolution API).
	"""
	def __init__(self):
		# Instanciação direta: sempre usar EvolutionClient
		self.chat_client = EvolutionClient()
