from interfaces.clients.queue_interface import IQueue
import os
import redis
from utils.logger import logger


class RedisClient(IQueue):

    def __init__(self):
        host = os.getenv("rHost")
        port = os.getenv("rPort")
        password = os.getenv("rPass")
        self.app = redis.Redis(host=host, port=port, password=password, decode_responses=True)

    def create_queue(self, data):
        try:
            self.app.hset("555",mapping=data)
        except Exception as e:
            logger.info(f'[RedisClient]Erro ao adicionar item a fila. Erro {e}')

    def read_queue(self, queue_key):
        return self.app.hget(queue_key,'number')
    
    def del_queue(self, queue_key):
        self.app.delete(queue_key)
        