import logging
import sys

#--------------------------------------------------------------------------------------------------------------------#

LOG_LEVEL = logging.INFO
LOG_FORMAT_STR = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = r"%d-%m-%Y %H:%M:%S"
LOG_FORMATTER = logging.Formatter(LOG_FORMAT_STR, datefmt=DATE_FORMAT)

#--------------------------------------------------------------------------------------------------------------------#


def configure_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(LOG_FORMATTER)
    root_logger.addHandler(console_handler)
    file_handler = logging.FileHandler("app_debug.log")
    file_handler.setFormatter(LOG_FORMATTER)
    root_logger.addHandler(file_handler)
    logger.info("Configuração de logging aplicada com sucesso.")


#--------------------------------------------------------------------------------------------------------------------#


logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
logger.propagate = True # Garante que os logs subam para o root