import logging
from typing import Any, Dict, Optional
from flask import Blueprint, request, jsonify
from utils.validators import extract_and_validate_phone
from services import process_message_async
import asyncio
import threading

logger: logging.Logger = logging.getLogger(__name__)

# Cria uma rota modular para o webhooks
webhook_bp = Blueprint("webhook", __name__)


# Rota para o Webhook
@webhook_bp.route("/evolution", methods=["POST"])
def evolution_webhook():
    payload: Optional[Dict[str, Any]] = request.json
    logger.debug(f"Payload recebido no webhook: {payload}")

    if not payload:
        logger.warning("Nenhum payload recebido no webhook.")
        return jsonify({"error": "Nenhum payload recebido"}), 400

    response, status_code, phone_number = extract_and_validate_phone(payload)

    if phone_number is None:
        return response, status_code

    try:
        threading.Thread(
            target=lambda: asyncio.run(process_message_async(phone_number, payload))
        ).start()
        logger.info(f"Mensagem enfileirada para processamento: {phone_number}")
    except Exception:
        return jsonify({"error": "Falha ao processar a mensagem"}), 500

    return jsonify({"status": "success"}), 200
