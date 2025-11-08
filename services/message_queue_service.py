import asyncio
import logging
import time
from typing import Dict, Any

from config import settings
from infrastructure import client_redis

logger = logging.getLogger(__name__)


class MessageQueueService:
    def __init__(self):
        self.processing_tasks: Dict[str, asyncio.Task[Any]] = {}
        self.batch_timeout = settings.batch_processing_delay
        # self.message_processor = MessageProcessor()
        self._shutting_down = False
        self._batch_monitor_task: asyncio.Task[Any] | None = None

    async def start_monitoring(self):
        """Inicia o monitoramento contínuo dos lotes"""
        self._batch_monitor_task = asyncio.create_task(self._monitor_batches())

    async def add_message(self, phone_number: str, message_data: dict[str, Any]):
        """Adiciona mensagem ao Redis e agenda processamento"""
        if self._shutting_down:
            return

        try:
            # Adiciona a mensagem ao Redis (método existente)
            client_redis.add_message(phone_number, message_data)

            # Agenda o processamento deste telefone
            await self._schedule_batch_processing(phone_number)

            logger.info(f"Mensagem adicionada e agendada para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem para {phone_number}: {e}")
            raise

    async def _schedule_batch_processing(self, phone_number: str):
        """Agenda o processamento do batch para este telefone"""
        try:
            # Define um timestamp de expiração no Redis
            processing_key = f"batch_processing:{phone_number}"
            expiry_time = time.time() + self.batch_timeout

            logger.info(f"AGENDANDO: {phone_number} -> expira em {self.batch_timeout}")

            # Usa SET com NX para evitar agendamentos duplicados
            scheduled = await asyncio.get_event_loop().run_in_executor(
                None, lambda: client_redis.set(processing_key, str(expiry_time))
            )

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client_redis.expireat(processing_key, int(time.time() + 60)),
            )

            if scheduled:
                logger.info(
                    f"Batch agendado para {phone_number} em {self.batch_timeout}s"
                )
            else:
                logger.info(f"Expiração do batch atualizado para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao agendar batch para {phone_number}: {e}")

    async def _monitor_batches(self):
        """Monitora continuamente os lotes prontos para processamento"""
        import functools

        if not self._shutting_down:
            logger.info(f"--- Monitoramento de batch iniciado")

        while not self._shutting_down:
            try:
                # Encontra lotes que expiraram (devem ser processados)
                phones_numbers: list[str] = await client_redis.get_messages_batches()

                for phone in phones_numbers:
                    try:
                        # Remove a chave e processa o lote
                        removed = await asyncio.get_running_loop().run_in_executor(
                            None,
                            functools.partial(
                                client_redis.delete, f"batch_processing:{phone}"
                            ),
                        )

                        if removed:
                            await self._process_scheduled_batch(phone)

                    except Exception as e:
                        logger.error(f"Erro ao processar batch key {phone}: {e}")
                        continue

                # Espera um curto período antes da próxima verificação
                await asyncio.sleep(1)  # 1s

            except Exception as e:
                logger.error(f"Erro no monitor de batches: {e}")
                await asyncio.sleep(1)

    async def _process_scheduled_batch(self, phone_number: str):
        """Processa um batch agendado"""
        try:
            # Verifica se há mensagens pendentes
            pending_count: int | Any = await asyncio.get_event_loop().run_in_executor(
                None, lambda: client_redis.llen(f"whatsapp:{phone_number}")
            )

            if pending_count > 0:
                logger.info(
                    f"Processando batch agendado para {phone_number} com {pending_count} mensagens"
                )

                # Usa o MessageProcessor existente para processar
                # await self.message_processor.process_phone_messages(phone_number)

                logger.info(f"Batch processado com sucesso para {phone_number}")
            else:
                logger.info(f"Nenhuma mensagem pendente para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao processar batch agendado para {phone_number}: {e}")

    async def stop_monitoring(self):
        """Para o monitoramento gracefuly"""
        self._shutting_down = True
        if self._batch_monitor_task and not self._batch_monitor_task.done():
            self._batch_monitor_task.cancel()
            try:
                await self._batch_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitor de batches parado")
