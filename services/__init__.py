from .message_queue_service import MessageQueueService
from typing import Dict, Any
import logging

logger: logging.Logger = logging.getLogger(__name__)
_mqs = MessageQueueService()


async def process_message_async(phone_number: str, payload: Dict[str, Any]):
    """Processa uma mensagem de forma assíncrona"""
    try:
        await _mqs.refresh_monitoring_cycle()
        await _mqs.add_message(phone_number, payload)
        logger.info(f"Mensagem processada com sucesso: {phone_number}")
    except Exception as e:
        logger.error(f"Erro no processamento assíncrono para {phone_number}: {e}")
        raise


async def stop_services():
    """Para todos os serviços gracefuly"""
    await _mqs.stop_monitoring()