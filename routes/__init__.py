from utils.logger import configure_logging
import logging
from flask import Flask
from routes.webhooks import webhook_bp
logger: logging.Logger = logging.getLogger(__name__)


def create_app():

    

    logger.info("Iniciando configturação de rotas")
    configure_logging()
    app = Flask(__name__)

    app.register_blueprint(webhook_bp, url_prefix="/v1/webhooks")

    return app