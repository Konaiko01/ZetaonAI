import pytest
import pytest_asyncio
from infrastructure import client_mongo, client_redis
from infrastructure.mongoDB import MongoDB
from infrastructure.redis_queue import RedisQueue
from typing import Tuple, Dict, Any


@pytest_asyncio.fixture
async def setup_clients():
    # Setup
    assert client_mongo.check_health()

    assert await client_redis.check_health()

    yield client_mongo, client_redis

    # Teardown: close test redis and drop test mongo data
    try:
        await client_redis.close()
    except Exception:
        pass

    if client_mongo.conversations is not None:
        client_mongo.conversations.drop()


@pytest.mark.asyncio
async def test_mongo_save_and_get_history(setup_clients: Tuple[MongoDB, RedisQueue]):
    mongo, _ = setup_clients
    phone = "5511999999999"

    # Testa salvamento
    message: Dict[str, Any] = {
        "type_message": "text",
        "message": {"text": "Teste unitário"},
    }

    try:
        mongo.save(
            phone_number=phone,
            message_data=message["message"],
            msg_type=message["type_message"],
        )

        # Recupera histórico
        history = mongo.get_history(phone_number=phone)

        assert len(history) > 0, "Histórico deveria ter pelo menos uma mensagem"
        latest = history[-1]

        assert latest["type_message"] == "text"
        assert latest["message"]["text"] == "Teste unitário"

    finally:
        # Limpa teste
        if mongo.conversations is not None:
            mongo.conversations.delete_many({"phone_number": phone})


async def test_redis_message_operations(setup_clients: Tuple[MongoDB, RedisQueue]):
    _, redis = setup_clients
    id = "test_key"
    message = {
        "type": "test",
        "content": "Mensagem de teste",
    }

    try:
        # Testa adição
        await redis.add_message(key=f"whatsapp:{id}", payload_data=message)

        # Recupera mensagens
        messages = await redis.get_pending_messages(id=id)

        assert len(messages) == 1, "Deveria ter exatamente uma mensagem"
        assert messages[0]["type"] == "test"
        assert messages[0]["content"] == "Mensagem de teste"

        # Verifica se fila foi limpa
        empty_messages = await redis.get_pending_messages(id=id)
        assert (
            len(empty_messages) == 0
        ), "Fila deveria estar vazia após get_pending_messages"

    finally:
        # Garante limpeza
        await redis.delete(f"whatsapp:{id}")
