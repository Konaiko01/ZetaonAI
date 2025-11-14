import pytest
from unittest.mock import Mock, MagicMock, patch, call
from services.group_authorization_service import GroupAuthorizationService
from infrastructure.group_members_repository import GroupMembersRepository


@pytest.fixture
def mock_group_client():
    """Mock do GroupClient."""
    return Mock()


@pytest.fixture
def group_auth_service(mock_mongodb_instance, mock_group_client):
    """Instância do serviço com mocks."""
    with patch('infrastructure.group_members_repository.logger_instance'):
        with patch('services.group_authorization_service.logger_instance'):
            service = GroupAuthorizationService(mock_mongodb_instance, mock_group_client)
            return service


def test_authorize_user_from_cache(group_auth_service, mock_group_client):
    """Testar autorização usando membros em cache."""
    phone = "5511999999999"
    group_id = "120363295648424210@g.us"

    # Mock: membros em cache
    with patch.object(
        group_auth_service.group_repo,
        'get_group_members',
        return_value=[
            {"id": "5511999999999@s.whatsapp.net", "admin": "regular"},
            {"id": "5512999999999@s.whatsapp.net", "admin": "superadmin"}
        ]
    ):
        result = group_auth_service.authorize_user(phone, group_id)

    assert result is True
    mock_group_client.get_group_participants.assert_not_called()


def test_authorize_user_fetch_from_evolution(group_auth_service, mock_group_client):
    """Testar autorização buscando membros da Evolution API."""
    phone = "5511999999999"
    group_id = "120363295648424210@g.us"

    members_from_api = [
        {"id": "5511999999999@s.whatsapp.net", "admin": "regular"},
        {"id": "5512999999999@s.whatsapp.net", "admin": "superadmin"}
    ]

    # Mock: cache vazio, API retorna membros
    with patch.object(group_auth_service.group_repo, 'get_group_members', return_value=[]):
        with patch.object(group_auth_service.group_repo, 'save_group_members', return_value=True):
            with patch.object(group_auth_service.group_repo, 'is_member_in_group', return_value=True):
                mock_group_client.get_group_participants.return_value = members_from_api

                result = group_auth_service.authorize_user(phone, group_id)

    assert result is True
    mock_group_client.get_group_participants.assert_called_once_with(group_id)
def test_authorize_user_not_member(group_auth_service, mock_group_client):
    """Testar rejeição de usuário que não é membro."""
    phone = "5513999999999"
    group_id = "120363295648424210@g.us"

    # Mock: membros em cache, mas phone não está lá
    with patch.object(
        group_auth_service.group_repo,
        'get_group_members',
        return_value=[
            {"id": "5511999999999@s.whatsapp.net", "admin": "regular"},
            {"id": "5512999999999@s.whatsapp.net", "admin": "superadmin"}
        ]
    ):
        result = group_auth_service.authorize_user(phone, group_id)

    assert result is False


def test_authorize_user_empty_members_from_evolution(group_auth_service, mock_group_client):
    """Testar quando Evolution API retorna lista vazia."""
    phone = "5511999999999"
    group_id = "120363295648424210@g.us"

    # Mock: cache vazio, API retorna vazio
    with patch.object(group_auth_service.group_repo, 'get_group_members', return_value=[]):
        mock_group_client.get_group_participants.return_value = []

        result = group_auth_service.authorize_user(phone, group_id)

    assert result is False


def test_refresh_group_cache_success(group_auth_service, mock_group_client):
    """Testar atualização de cache com sucesso."""
    group_id = "120363295648424210@g.us"
    members = [
        {"id": "5511999999999@s.whatsapp.net", "admin": "regular"}
    ]

    mock_group_client.get_group_participants.return_value = members

    with patch.object(group_auth_service.group_repo, 'save_group_members', return_value=True):
        result = group_auth_service.refresh_group_cache(group_id)

    assert result is True
    mock_group_client.get_group_participants.assert_called_once_with(group_id)


def test_refresh_group_cache_failure(group_auth_service, mock_group_client):
    """Testar atualização de cache quando API falha."""
    group_id = "120363295648424210@g.us"

    mock_group_client.get_group_participants.return_value = []

    result = group_auth_service.refresh_group_cache(group_id)

    assert result is False


def test_is_user_in_any_authorized_group_success(group_auth_service):
    """Testar se usuário está em algum grupo autorizado."""
    phone = "5511999999999"
    authorized_groups = ["120363295648424210@g.us", "120363295648424211@g.us"]

    with patch.object(group_auth_service, 'authorize_user', side_effect=[True, False]):
        result = group_auth_service.is_user_in_any_authorized_group(phone, authorized_groups)

    assert result is True


def test_is_user_in_any_authorized_group_failure(group_auth_service):
    """Testar quando usuário não está em nenhum grupo autorizado."""
    phone = "5511999999999"
    authorized_groups = ["120363295648424210@g.us", "120363295648424211@g.us"]

    with patch.object(group_auth_service, 'authorize_user', return_value=False):
        result = group_auth_service.is_user_in_any_authorized_group(phone, authorized_groups)

    assert result is False


def test_get_group_members_from_cache(group_auth_service, mock_group_client):
    """Testar busca de membros usando cache."""
    group_id = "120363295648424210@g.us"
    members = [
        {"id": "5511999999999@s.whatsapp.net", "admin": "regular"}
    ]

    with patch.object(group_auth_service.group_repo, 'get_group_members', return_value=members):
        result = group_auth_service.get_group_members(group_id)

    assert result == members
    mock_group_client.get_group_participants.assert_not_called()
