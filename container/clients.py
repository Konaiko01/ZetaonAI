import os
from clients.evolution_client import EvolutionClient
from clients.openai_client import OpenIAClient
from clients.mongo_client import MongoDBClient
from clients.redis_client import RedisClient
from clients.calendar_client import GCalendarClient


class ClientContainer:
    @property
    def chat(self) -> EvolutionClient:
        if os.getenv("APP_ENV") == "stage":
            return EvolutionClient()

        return EvolutionClient()

    @property
    def ai(self) -> OpenIAClient:
        return OpenIAClient()

    @property
    def database(self) -> MongoDBClient:
        return MongoDBClient()

    @property
    def cache(self) -> RedisClient:
        return RedisClient()

    @property
    def crm(self) -> GCalendarClient:
        return GCalendarClient()
