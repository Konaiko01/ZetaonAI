import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Configurar variáveis de ambiente antes de qualquer import
os.environ.setdefault('mongodb_db_name', 'test_db')

# Mock dos módulos de infraestrutura antes de imports
sys.modules['infrastructure.mongoDB'] = MagicMock()
sys.modules['infrastructure.redis_queue'] = MagicMock()

@pytest.fixture
def mock_mongodb_instance():
    """Fixture: instância mocada de MongoDB."""
    mock_instance = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    mock_instance.db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    return mock_instance

