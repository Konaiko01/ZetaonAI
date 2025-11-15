from datetime import datetime, timezone
from utils.logger import logger
try:
    # (Python 3.9+)
    from zoneinfo import ZoneInfo 
except ImportError:
    # (Python < 3.9 - Fallback)
    logger.error("'zoneinfo' não encontrado. Instalando 'pytz' (pip install pytz) ou atualizando o Python é recomendado.")
    from datetime import timedelta
    # Fallback caso 'zoneinfo' falhe
    class FallbackZoneInfo(timezone):
        def __init__(self, key):
            if key == "America/Sao_Paulo":
                super().__init__(timedelta(hours=-3))
            else:
                super().__init__(timezone.utc)
    ZoneInfo = FallbackZoneInfo # Aponta ZoneInfo para o nosso fallback
# --- FIM DA CORREÇÃO ---