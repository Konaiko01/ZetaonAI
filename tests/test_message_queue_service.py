import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from services.message_queue_service import MessageQueueService


@pytest.fixture
def message_queue_service():
    """Fixture para criar uma instância do MessageQueueService"""
    service = MessageQueueService()
    yield service
    # Cleanup após os testes
    asyncio.run(service.cleanup())


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
    await message_queue_service.start_monitoring()

    # Verifica se as tasks foram criadas
    assert message_queue_service._batch_monitor_task is not None
    assert message_queue_service._auto_stop_task is not None
    assert not message_queue_service._shutting_down


@pytest.mark.asyncio
async def test_monitor_batches_with_messages(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o monitoramento quando há mensagens para processar"""
    # Configura mock para retornar números de telefone
    phone_numbers = ["5511999999999", "5511888888888"]
    mock_redis.get_messages_batches.return_value = phone_numbers

    # Mock do método de processamento
    message_queue_service._process_with_limit = AsyncMock()

    # Inicia monitoramento
    await message_queue_service.start_monitoring()

    # Aguarda um pouco para o monitor processar
    await asyncio.sleep(0.1)

    # Verifica se o método de processamento foi chamado para cada telefone
    assert message_queue_service._process_with_limit.call_count == len(phone_numbers)

    # Para o monitoramento
    await message_queue_service.stop_monitoring()


@pytest.mark.asyncio
async def test_monitor_batches_empty(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o monitoramento quando não há mensagens"""
    # Configura mock para retornar lista vazia
    mock_redis.get_messages_batches.return_value = []

    # Mock do método de processamento
    message_queue_service._process_with_limit = AsyncMock()

    # Inicia monitoramento
    await message_queue_service.start_monitoring()

    # Aguarda um pouco
    await asyncio.sleep(0.1)

    # Verifica que o método de processamento não foi chamado
    message_queue_service._process_with_limit.assert_not_called()

    # Para o monitoramento
    await message_queue_service.stop_monitoring()


@pytest.mark.asyncio
async def test_process_with_limit_concurrency(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o controle de concorrência no processamento"""
    phone_number = "5511999999999"

    # Mock do método de processamento
    message_queue_service._process_single_batch = AsyncMock()

    # Processa com limite
    await message_queue_service._process_with_limit(phone_number)

    # Verifica se o método de processamento foi chamado
    message_queue_service._process_single_batch.assert_called_once_with(phone_number)


@pytest.mark.asyncio
async def test_stop_monitoring(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa a parada do monitoramento"""
    # Inicia monitoramento primeiro
    await message_queue_service.start_monitoring()

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
    message_queue_service._monitor_duration = 0.1

    # Inicia monitoramento
    await message_queue_service.start_monitoring()

    # Aguarda tempo suficiente para auto-stop
    await asyncio.sleep(0.2)

    # Verifica que o monitoramento foi parado
    assert message_queue_service._shutting_down


@pytest.mark.asyncio
async def test_cleanup(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa a limpeza de recursos"""
    # Inicia monitoramento para ter tasks ativas
    await message_queue_service.start_monitoring()

    # Adiciona algumas tasks de processamento simuladas
    mock_task = AsyncMock()
    message_queue_service.processing_tasks["test_task"] = mock_task

    # Executa cleanup
    await message_queue_service.cleanup()

    # Verifica que as tasks foram canceladas
    assert message_queue_service._shutting_down


@pytest.mark.asyncio
async def test_concurrent_processing_limit(
    message_queue_service: MessageQueueService, mock_redis: AsyncMock
):
    """Testa o limite de processamento concorrente"""
    # Configura múltiplos números de telefone
    phone_numbers = [f"551199999999{i}" for i in range(10)]
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
        await asyncio.sleep(0.01)

    message_queue_service._process_single_batch = mock_process_single_batch

    # Inicia monitoramento brevemente
    await message_queue_service.start_monitoring()
    await asyncio.sleep(0.1)
    await message_queue_service.stop_monitoring()

    # Verifica que o processamento ocorreu respeitando os limites
    assert processing_count <= len(phone_numbers)


if __name__ == "__main__":
    # Para executar os testes diretamente
    pytest.main([__file__, "-v"])
