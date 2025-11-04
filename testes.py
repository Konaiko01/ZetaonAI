from clients.redis_client import RedisClient
from utils.logger import logger

data: dict = {
    "name":"joao",
    "number":"5511987774476",
    "age":21
}

r = RedisClient()

#r.create_queue(data=data)
r.del_queue("555")
to_print = r.read_queue("555")
logger.info(to_print)

