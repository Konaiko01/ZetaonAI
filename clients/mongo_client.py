from interfaces.clients.db_interface import IDB
from utils.logger import logger
from pymongo import MongoClient
import os

class MongoDBClient(IDB):

    
    
    def __init__(self):
        connection = os.getenv("mUri")
        self.app = MongoClient(connection)
        self.database = self.app["client_context"]

    def add_query(self, collection_key,data):
        collect = self.database[collection_key]
        collect.insert_one(data)

    def delete_query(self,collection_key): 
        if self.collection_exists:
            self.database.drop_collection(collection_key)
        

    def select_query(self, collection_key):
        collect = self.database[collection_key]
        logger.info(f"[MongoDbClient]{collect.find_one()}")
        return collect.find_one()
    
    def collection_exists(self, collection_key):
        collection = self.database.list_collection_names()
        for col in range(0,len(self.database.list_collection_names)):
            if collection_key == collection[col]:
                return True
        return False