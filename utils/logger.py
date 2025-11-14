#
# utils/logger.py (CORRIGIDO)
#
import logging
import sys

# --- 1. Definições de Configuração ---
LOG_LEVEL = logging.INFO
LOG_FORMAT_STR = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = r"%d-%m-%Y %H:%M:%S"

# --- 2. Cria o Formatter (será usado pelos handlers) ---
LOG_FORMATTER = logging.Formatter(LOG_FORMAT_STR, datefmt=DATE_FORMAT)

# --- 3. Função de Configuração (Modificada) ---
def configure_logging():
    """
    Configura o logger raiz para usar nossos handlers.
    Isso substitui o basicConfig() e funciona com Uvicorn.
    """
    # Pega o logger raiz (root)
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Limpa quaisquer handlers que o Uvicorn possa ter adicionado
    root_logger.handlers.clear()

    # Adiciona nosso handler do Console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(LOG_FORMATTER)
    root_logger.addHandler(console_handler)

    # Adiciona nosso handler de Arquivo
    file_handler = logging.FileHandler("app_debug.log")
    file_handler.setFormatter(LOG_FORMATTER)
    root_logger.addHandler(file_handler)
    
    logger.info("Configuração de logging aplicada com sucesso.")

# --- 4. Cria a instância do logger que seus arquivos irão importar ---
# (O nome deste logger será 'utils.logger')
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
logger.propagate = True # Garante que os logs subam para o root