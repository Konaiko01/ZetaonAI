import pytest
from config.app_settings import AppSettings
from pathlib import Path
import shutil


@pytest.fixture(autouse=True)
def setup_test_env():
    """Fixture que configura o ambiente de teste usando .env.test"""
    # Guarda o caminho original do .env se existir
    original_env = Path(".env")
    original_env_backup = None

    if original_env.exists():
        original_env_backup = Path(".env.backup")
        shutil.copy2(original_env, original_env_backup)

    # Copia .env.test para .env
    shutil.copy2(".env.test", ".env")

    yield  # Executa os testes

    # Restaura o .env original se existia
    if original_env_backup and original_env_backup.exists():
        shutil.copy2(original_env_backup, original_env)
        original_env_backup.unlink()
    else:
        # Se não havia .env original, remove o de teste
        original_env.unlink(missing_ok=True)


def test_test_env_settings():
    """Testa se as configurações do ambiente de teste estão corretas"""
    settings = AppSettings()

    # Verifica configurações do MongoDB
    assert settings.mongodb_uri == "mongodb://teste:27018"
    assert settings.mongodb_db_name == "zeta_test_db"

    # Verifica configurações do Redis
    assert settings.redis_url == "redis://teste:6380"

    # Verifica delay de processamento
    assert settings.debounce_delay == 100
    assert isinstance(settings.debounce_delay, int)

    # Verifica números autorizados
    assert isinstance(settings.authorized_numbers, list)
    assert len(settings.authorized_numbers) == 2
    assert "5511999999999" in settings.authorized_numbers
    assert "5511888888888" in settings.authorized_numbers


def test_all_required_settings_present():
    """Testa se todas as configurações necessárias estão presentes no .env.test"""
    settings = AppSettings()

    # Lista de configurações que devem estar presentes
    required_settings = [
        "mongodb_uri",
        "mongodb_db_name",
        "redis_url",
        "batch_processing_delay",
        "authorized_numbers",
    ]

    for setting in required_settings:
        assert hasattr(settings, setting), f"Configuração '{setting}' não encontrada"
        assert (
            getattr(settings, setting) is not None
        ), f"Configuração '{setting}' está None"
