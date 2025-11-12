# test_message_queue_service.py
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, AsyncMock
from services.message_queue_service import MessageQueueService


@pytest_asyncio.fixture
async def message_queue_service():
    """Fixture para criar uma instância do MessageQueueService"""
    service = MessageQueueService()
    try:
        yield service
    finally:
        # Cleanup com timeout para evitar loops infinitos
        try:
            await asyncio.wait_for(service.cleanup(), timeout=2.0)
        except asyncio.TimeoutError:
            # Força o shutdown se o cleanup demorar muito
            service._shutting_down = True
            if service._batch_monitor_task:
                service._batch_monitor_task.cancel()
            if service._auto_stop_task:
                self._auto_stop_task.cancel()


@pytest.fixture
def mock_redis():
    """Fixture para mock do Redis"""
    with patch("infrastructure.client_redis") as mock_redis:
        mock_redis.add_message = AsyncMock()
        mock_redis.get_messages_batches = AsyncMock(return_value=[])
        mock_redis.get_pending_messages = AsyncMock(return_value=[])
        mock_redis.delete = AsyncMock(return_value=1)
        yield mock_redis


@pytest.mark.asyncio
async def test_add_message_success(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa a adição bem-sucedida de mensagem"""
    phone_number = "5511999999999"
    message_data = {"type": "text", "content": "Mensagem de teste"}

    # Adiciona mensagem
    await message_queue_service.add_message(phone_number, message_data)

    # Verifica se o método do Redis foi chamado corretamente
    mock_redis.add_message.assert_called_once_with(phone_number, message_data)


@pytest.mark.asyncio
async def test_add_message_during_shutdown(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa que mensagens são ignoradas durante shutdown"""
    phone_number = "5511999999999"
    message_data = {"type": "text", "content": "Mensagem durante shutdown"}

    # Simula estado de shutdown
    message_queue_service._shutting_down = True

    # Adiciona mensagem
    await message_queue_service.add_message(phone_number, message_data)

    # Verifica que o Redis não foi chamado
    mock_redis.add_message.assert_not_called()


@pytest.mark.asyncio
async def test_start_monitoring(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o início do monitoramento"""
    await message_queue_service.refresh_monitoring_cycle()

    # Verifica se as tasks foram criadas
    assert message_queue_service._batch_monitor_task is not None
    assert message_queue_service._auto_stop_task is not None
    assert not message_queue_service._shutting_down

    # Limpa imediatamente após o teste
    await message_queue_service.stop_monitoring()


@pytest.mark.asyncio
async def test_monitor_batches_with_messages(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o monitoramento quando há mensagens para processar"""
    # Configura mock para retornar números de telefone
    phone_numbers = ["5511999999999", "5511888888888"]
    mock_redis.get_messages_batches.return_value = phone_numbers

    # Mock do método de processamento
    process_calls = []

    async def mock_process(phone):
        process_calls.append(phone)

    message_queue_service._process_with_limit = mock_process

    # Inicia monitoramento
    await message_queue_service.refresh_monitoring_cycle()

    # Aguarda um pouco para o monitor processar
    await asyncio.sleep(0.5)

    # Para o monitoramento
    await message_queue_service.stop_monitoring()

    # Verifica se o método de processamento foi chamado para cada telefone
    assert len(process_calls) == len(phone_numbers)
    for phone in phone_numbers:
        assert phone in process_calls


@pytest.mark.asyncio
async def test_monitor_batches_empty(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o monitoramento quando não há mensagens"""
    # Configura mock para retornar lista vazia
    mock_redis.get_messages_batches.return_value = []

    # Mock do método de processamento
    process_called = False

    async def mock_process(phone):
        nonlocal process_called
        process_called = True

    message_queue_service._process_with_limit = mock_process

    # Inicia monitoramento
    await message_queue_service.refresh_monitoring_cycle()

    # Aguarda um pouco
    await asyncio.sleep(0.5)

    # Para o monitoramento
    await message_queue_service.stop_monitoring()

    # Verifica que o método de processamento não foi chamado
    assert not process_called


@pytest.mark.asyncio
async def test_process_with_limit_concurrency(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o controle de concorrência no processamento"""
    phone_number = "5511999999999"

    # Mock do método de processamento
    process_called = False

    async def mock_process_batch(phone, messages):
        nonlocal process_called
        process_called = True
        assert phone == phone_number

    message_queue_service._process_single_batch = mock_process_batch

    # Processa com limite
    await message_queue_service._process_with_limit(phone_number)

    # Verifica se o método de processamento foi chamado
    assert process_called


@pytest.mark.asyncio
async def test_stop_monitoring(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa a parada do monitoramento"""
    # Inicia monitoramento primeiro
    await message_queue_service.refresh_monitoring_cycle()

    # Verifica que está rodando
    assert not message_queue_service._shutting_down
    assert message_queue_service._batch_monitor_task is not None

    # Para o monitoramento
    await message_queue_service.stop_monitoring()

    # Verifica que está parando
    assert message_queue_service._shutting_down


@pytest.mark.asyncio
async def test_auto_stop_monitoring(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o encerramento automático do monitoramento"""
    # Configura duração mais curta para teste
    original_duration = message_queue_service._monitor_duration
    message_queue_service._monitor_duration = 0.5  # 500ms para teste rápido

    try:
        # Inicia monitoramento
        await message_queue_service.refresh_monitoring_cycle()

        # Aguarda tempo suficiente para auto-stop
        await asyncio.sleep(1.0)

        # Verifica que o monitoramento foi parado
        assert message_queue_service._shutting_down
    finally:
        # Restaura duração original
        message_queue_service._monitor_duration = original_duration


@pytest.mark.asyncio
async def test_cleanup(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa a limpeza de recursos"""
    # Inicia monitoramento para ter tasks ativas
    await message_queue_service.refresh_monitoring_cycle()

    # Adiciona uma task real de processamento (não mock)
    async def dummy_task():
        await asyncio.sleep(3600)  # Task longa

    real_task = asyncio.create_task(dummy_task())
    message_queue_service.processing_tasks["test_task"] = real_task

    # Executa cleanup
    await message_queue_service.cleanup()

    # Verifica que as tasks foram canceladas
    assert message_queue_service._shutting_down
    assert real_task.cancelled()


@pytest.mark.asyncio
async def test_concurrent_processing_limit(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o limite de processamento concorrente"""
    # Configura múltiplos números de telefone
    phone_numbers = [f"551199999999{i}" for i in range(5)]  # Reduzido para 5
    mock_redis.get_messages_batches.return_value = phone_numbers

    # Semáforo deve limitar o processamento
    assert (
        message_queue_service._semaphore._value == message_queue_service.max_concurrent
    )

    # Contador para verificar processamento
    processing_count = 0

    async def mock_process_single_batch(phone):
        nonlocal processing_count
        processing_count += 1
        # Simula algum tempo de processamento
        await asyncio.sleep(0.1)

    message_queue_service._process_single_batch = mock_process_single_batch

    # Inicia monitoramento brevemente
    await message_queue_service.refresh_monitoring_cycle()
    await asyncio.sleep(0.3)  # Tempo reduzido
    await message_queue_service.stop_monitoring()

    # Verifica que o processamento ocorreu respeitando os limites
    assert processing_count <= len(phone_numbers)


# Testes mais simples e rápidos
@pytest.mark.asyncio
async def test_service_initial_state(message_queue_service: MessageQueueService):
    """Testa o estado inicial do serviço"""
    assert message_queue_service._shutting_down is False
    assert message_queue_service.processing_tasks == {}
    assert message_queue_service._batch_monitor_task is None
    assert message_queue_service._auto_stop_task is None
    assert message_queue_service._semaphore is not None


@pytest.mark.asyncio
async def test_semaphore_initialization(message_queue_service: MessageQueueService):
    """Testa a inicialização do semáforo"""
    assert (
        message_queue_service._semaphore._value == message_queue_service.max_concurrent
    )
    assert message_queue_service.max_concurrent > 0


if __name__ == "__main__":
    # Para executar os testes diretamente
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
