from infrastructure import mongoDB, redis_queue

client_mongo = mongoDB.MongoDB()
client_redis = redis_queue.RedisQueue()
