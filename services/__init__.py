from .message_queue_service import MessageQueueService
from infrastructure import client_mongo, client_redis
from typing import Dict, Any
import logging

logger: logging.Logger = logging.getLogger(__name__)
# TODO : Definir orquestrador adequado
_mqs = MessageQueueService(
    orchestrator=, message_repository=client_mongo, redis_queue=client_redis
)


async def process_message_async(phone_number: str, payload: Dict[str, Any]):
    """Processa uma mensagem de forma assíncrona"""
    try:
        await _mqs.refresh_monitoring_cycle()
        await _mqs.add_message(phone_number, payload)
    except Exception as e:
        logger.error(f"Erro no processamento assíncrono para {phone_number}: {e}")
        raise


async def stop_services():
    """Para todos os serviços gracefuly"""
    await _mqs.stop_monitoring()
