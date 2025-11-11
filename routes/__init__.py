from utils.logger_Sugestão import configure_logging
import logging

logger: logging.Logger = logging.getLogger(__name__)


def create_app():
    """Cria e configura a aplicação Flask"""
    from flask import Flask
    from routes.webhooks import webhook_bp

    logger.info("Iniciando configturação de rotas")
    configure_logging()
    app = Flask(__name__)

    app.register_blueprint(webhook_bp, url_prefix="/v1/webhooks")

    return app
