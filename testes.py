from clients.redis_client import RedisClient
from clients.mongo_client import MongoDBClient
from utils.logger import logger

data: dict = {
    "name":"joao",
    "number":"5511987774476",
    "age":21
}

''' Testes de query redis
r = RedisClient()
r.create_queue(data=data)
r.del_queue("555")
to_print = r.read_queue("555")
'''
m = MongoDBClient()

#m.add_query("555", data)
logger.info(f"[Teste]{m.select_query("555")}")
m.delete_query("555")
logger.info(f"[Teste]{m.select_query("555")}")