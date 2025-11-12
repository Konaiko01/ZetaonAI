from typing import Callable, Any, Dict, Tuple, Optional
from functools import wraps
from flask import jsonify
import logging

logger: logging.Logger = logging.getLogger(__name__)


def validator_health(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator de módulo que verifica `self.is_healthy` antes de executar o método.

    Como usar:

        @validator_health
        def metodo(self, ...):
            ...
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if not getattr(args[0], "is_healthy", False):
            raise ConnectionError("Redis não está disponível")
        return func(*args, **kwargs)

    return wrapper


def extract_and_validate_phone(
    payload: Dict[str, Any],
) -> Tuple[Any, int, Optional[str]]:

    raw_jid = payload["data"]["key"].get("remoteJid", "")

    if not raw_jid:
        logger.warning("Não foi possível extrair número do payload")
        return jsonify({"error": "phone not found"}), 400, None

    if not "s.whatsapp.net" in raw_jid:
        logger.warning("Messagem não vem do privado")
        return (
            jsonify({"status": "skipped", "message": "Número não é do privado"}),
            200,
            None,
        )

    phone_number = _get_number(raw_jid)

    return (
        jsonify({"status": "queued", "phone": phone_number}),
        202,
        phone_number,
    )


def _get_number(strTelefone: Any) -> str:
    tel: str = strTelefone.split("@")[0]
    if len(tel) == 12:
        tel = tel[:3] + "9" + tel[4:]
        logger.info(f"Número ajustado para formato com 13 dígitos")

    logger.info(f"Número extraído: {tel}")
    return tel