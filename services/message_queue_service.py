import asyncio
from asyncio import Semaphore
import logging
from typing import Dict, Any, List, Optional
import infrastructure
import inspect
from config import settings

logger = logging.getLogger(__name__)


class MessageQueueService:
    def __init__(self):
        self.processing_tasks: Dict[str, asyncio.Task[Any]] = {}
        self._shutting_down = False
        self._batch_monitor_task: Optional[asyncio.Task[Any]] = None
        self._auto_stop_task: Optional[asyncio.Task[Any]] = None
        self._monitor_duration = 10  # duração em segundos

        # Controla o número máximo de tasks simultâneas
        self.max_concurrent = settings.max_concurrent
        self._semaphore = Semaphore(self.max_concurrent)

    async def start_monitoring(self):
        """Inicia ou reinicia o monitoramento contínuo dos lotes para 1 minuto"""
        # Cancela o timer de auto-stop anterior se existir
        if self._auto_stop_task and not self._auto_stop_task.done():
            self._auto_stop_task.cancel()
            try:
                await self._auto_stop_task
            except asyncio.CancelledError:
                pass

        # Inicia o monitor se não estiver rodando
        if not self._batch_monitor_task or self._batch_monitor_task.done():
            self._shutting_down = False
            self._batch_monitor_task = asyncio.create_task(self._monitor_batches())
            logger.info("Monitor de batches iniciado")

        # Agenda novo auto-stop
        self._auto_stop_task = asyncio.create_task(self._auto_stop_monitoring())
        logger.info(f"Monitor será encerrado em {self._monitor_duration} segundos")

    async def add_message(self, phone_number: str, message_data: dict[str, Any]):
        """Adiciona mensagem ao Redis e agenda processamento"""
        if self._shutting_down:
            logger.warning("Serviço está desligando, mensagem ignorada")
            return

        try:
            # Adiciona a mensagem ao Redis (método assíncrono)
            await infrastructure.client_redis.add_message(phone_number, message_data)
            logger.debug(f"Mensagem adicionada para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem para {phone_number}: {e}")
            raise e

    async def _auto_stop_monitoring(self):
        """Agenda o encerramento automático do monitoramento"""
        try:
            await asyncio.sleep(self._monitor_duration)
            await self.stop_monitoring()
            logger.info(
                "Monitor de batches encerrado automaticamente após tempo limite"
            )
        except asyncio.CancelledError:
            logger.info("Timer de auto-stop cancelado - monitor continuará rodando")

    async def _monitor_batches(self):
        """Monitora continuamente os lotes com limite de concorrência (em paralelo)"""
        logger.info(f"--- Monitoramento iniciado")

        while not self._shutting_down:
            try:
                phones_numbers: List[str] = (
                    await infrastructure.client_redis.get_messages_batches()
                )

                if phones_numbers:
                    logger.info(
                        f"Encontrados {len(phones_numbers)} lotes para processar"
                    )

                # Cria tasks limitadas pelo semaphore
                tasks: List[Any] = []
                for phone in phones_numbers:
                    # Cria task com controle de concorrência
                    task = asyncio.create_task(self._process_with_limit(phone))
                    tasks.append(task)

                # Aguarda todas as tasks completarem
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Log de resultados
                    successful = sum(1 for r in results if not isinstance(r, Exception))
                    failed = sum(1 for r in results if isinstance(r, Exception))

                    if successful > 0 or failed > 0:
                        logger.info(
                            f"Processamento: {successful} sucesso, {failed} falhas"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no monitor: {e}")
            await asyncio.sleep(1)

    async def _process_with_limit(self, phone_number: str) -> None:
        """Processa um telefone respeitando o limite de concorrência"""
        async with self._semaphore:
            try:
                logger.debug(
                    f"Iniciando processamento de {phone_number} "
                    f"(semaphore: {self._semaphore._value}/{self.max_concurrent})"
                )

                await self._process_single_batch(phone_number)

            except Exception as e:
                logger.error(f"Erro ao processar {phone_number}: {e}")
                raise

    async def _process_single_batch(self, phone_number: str):
        """Processa um único batch (mantém a lógica original)"""

    async def _process_scheduled_batch(self, phone_number: str):
        """Processa um batch agendado"""
        try:
            removed = await infrastructure.client_redis.delete(
                f"batch_processing:{phone_number}"
            )
            if not removed:
                pass

            # Recupera e processa as mensagens
            messages: List[Dict[str, Any]] = (
                await infrastructure.client_redis.get_pending_messages(phone_number)
            )

            if len(messages) > 0:
                # TODO: Implementar a lógica real de processamento
                print("Implemente apartir daqui")

                logger.info(f"Batch processado com sucesso para {phone_number}")
            else:
                logger.info(f"Nenhuma mensagem pendente para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao processar batch agendado para {phone_number}: {e}")

    async def stop_monitoring(self):
        """Para o monitoramento gracefuly"""
        self._shutting_down = True

        # Cancela tarefas de monitoramento
        tasks_to_cancel: List[Any] = []
        if self._batch_monitor_task and not self._batch_monitor_task.done():
            tasks_to_cancel.append(self._batch_monitor_task)
        if self._auto_stop_task and not self._auto_stop_task.done():
            tasks_to_cancel.append(self._auto_stop_task)

        for task in tasks_to_cancel:
            try:
                task.cancel()
            except RecursionError:
                logger.error(
                    "RecursionError ao cancelar task de monitoramento; ignorando cancelamento adicional"
                )
                # continue trying to cancel other tasks
                continue

        # Aguarda o cancelamento
        if tasks_to_cancel:
            try:
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            except RecursionError:
                logger.error(
                    "RecursionError ao aguardar cancelamento de tasks; prosseguindo"
                )

        logger.info("Monitor de batches parado")

    async def cleanup(self):
        """Limpeza de recursos"""
        await self.stop_monitoring()
        # Cancela todas as tarefas de processamento e aguarda apenas awaitables
        awaitables: List[Any] = []
        for task in self.processing_tasks.values():
            try:
                # If it's a Task or Future or an awaitable coroutine, cancel and schedule to await
                if asyncio.isfuture(task) or inspect.isawaitable(task):
                    # cancel if possible
                    try:
                        task.cancel()
                    except Exception:
                        pass
                    awaitables.append(task)
                else:
                    # Best-effort: if object has cancel method, call it, but don't await
                    if hasattr(task, "cancel"):
                        try:
                            task.cancel()
                        except Exception:
                            pass
            except Exception:
                # Ignore issues with mock/non-standard task objects
                continue

        if awaitables:
            await asyncio.gather(*awaitables, return_exceptions=True)
