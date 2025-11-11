from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path
from typing import List, Union

_ENV_FILE_PATH = Path(__file__).resolve().parent.parent / ".env"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE_PATH))
    # Configuração da OpenAI

    # Configuração da EvolutionAPI

    # Configuração do MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = ""

    # Configuração do Redis
    redis_url: str = "redis://localhost:6379"

    # Tempo para processar lote
    debounce_delay: int = 3

    # Número máximo de tarefas simultâneas
    max_concurrent: int = 5

    # Números autorizados a usar o bot
    authorized_numbers: Union[List[str], str] = []

    @field_validator("authorized_numbers", mode="before")
    def _parse_csv_to_list(cls, value: str) -> List[str]:
        return value.split(",")
