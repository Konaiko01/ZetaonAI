from utils.logger_Sugestão import configure_logging
import logging
from infrastructure import client_mongo, client_redis

logger: logging.Logger = logging.getLogger(__name__)


async def create_app():
    """Cria e configura a aplicação Flask"""
    from flask import Flask
    from routes.webhooks import webhook_bp

    configure_logging()

    logger.info("Iniciando configturação de rotas")
    client_mongo.check_health()
    await client_redis.check_health()
    app = Flask(__name__)

    app.register_blueprint(webhook_bp, url_prefix="/v1/webhooks")

    return app
