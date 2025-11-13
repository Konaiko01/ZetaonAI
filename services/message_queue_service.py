'''import asyncio
from asyncio import Semaphore
import logging
from typing import Dict, Any, List, Optional
import inspect
from config import settings
from services.response_orchestrator_service import ResponseOrchestratorService
from infrastructure.mongoDB import MongoDB 
from interfaces.clients.queue_interface import IQueue 

logger = logging.getLogger(__name__)


class MessageQueueService:
    def __init__(
        self,
        orchestrator: ResponseOrchestratorService,
        message_repository: MongoDB, 
        redis_queue: IQueue 
    ):
        self.processing_tasks: Dict[str, asyncio.Task[Any]] = {}
        self._shutting_down = False
        self._batch_monitor_task: Optional[asyncio.Task[Any]] = None
        self._auto_stop_task: Optional[asyncio.Task[Any]] = None
        self._monitor_duration = 10 

        self.max_concurrent = settings.max_concurrent
        self._semaphore = Semaphore(self.max_concurrent)

        self.orchestrator = orchestrator
        self.message_repository = message_repository
        self.redis_queue = redis_queue
        
        logger.info(
            f"MessageQueueService inicializado. Concorrência máxima: {self.max_concurrent}"
        )


    async def refresh_monitoring_cycle(self):
        """Inicia ou reinicia o monitoramento contínuo dos lotes."""
        if self._auto_stop_task and not self._auto_stop_task.done():
            self._auto_stop_task.cancel()
            try:
                await self._auto_stop_task
            except asyncio.CancelledError:
                pass

        if not self._batch_monitor_task or self._batch_monitor_task.done():
            self._shutting_down = False
            self._batch_monitor_task = asyncio.create_task(self._monitor_batches())
            logger.info("Monitor de batches (ZSET) iniciado")

        self._auto_stop_task = asyncio.create_task(self._auto_stop_monitoring())
        logger.info(f"Monitor será encerrado em {self._monitor_duration} segundos se inativo")

    async def add_message(self, phone_number: str, message_data: Dict[str, Any]):
        if self._shutting_down:
            logger.warning("Serviço está desligando, mensagem ignorada")
            return

        try:
            await self.redis_queue.add_message(phone_number, message_data)
            logger.debug(f"Mensagem adicionada para {phone_number}")

            await self.refresh_monitoring_cycle()

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem para {phone_number}: {e}")
            raise e

    async def _auto_stop_monitoring(self):
        """Agenda o encerramento automático do monitoramento"""
        try:
            await asyncio.sleep(self._monitor_duration)
            await self.stop_monitoring()
            logger.info(
                "Monitor de batches encerrado automaticamente após tempo limite de inatividade"
            )
        except asyncio.CancelledError:
            logger.info("Timer de auto-stop cancelado (nova mensagem chegou)")

    async def _monitor_batches(self):
        """Monitora continuamente os lotes (ZSET) com limite de concorrência."""
        logger.info(f"--- Monitoramento iniciado (Max Concurrency: {self.max_concurrent})")

        while not self._shutting_down:
            try:
                batch_keys: List[str] = (
                    await self.redis_queue.get_messages_batches()
                )

                if batch_keys:
                    logger.info(
                        f"Encontrados {len(batch_keys)} lotes (ZSET) para processar"
                    )
                tasks: List[Any] = []
                for key in batch_keys:
                    task = asyncio.create_task(self._process_with_limit(key))
                    tasks.append(task)

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    successful = sum(1 for r in results if not isinstance(r, Exception))
                    failed = sum(1 for r in results if isinstance(r, Exception))

                    if successful > 0 or failed > 0:
                        logger.info(
                            f"Processamento de lote finalizado: {successful} sucesso, {failed} falhas"
                        )

            except asyncio.CancelledError:
                logger.info("Monitor de batches recebendo sinal de cancelamento.")
                break
            except Exception as e:
                logger.error(f"Erro crítico no loop do monitor de batches: {e}", exc_info=True)

            await asyncio.sleep(1)
        
        logger.info("--- Monitoramento de batches finalizado.")


    async def _process_with_limit(self, redis_key: str) -> None:
        async with self._semaphore:
            if self._shutting_down:
                logger.warning(f"Ignorando processamento de {redis_key}, serviço desligando.")
                return
                
            try:
                logger.debug(
                    f"Iniciando processamento de {redis_key} "
                    f"(semaphore: {self._semaphore._value}/{self.max_concurrent})"
                )
                await self._process_scheduled_batch(redis_key)

            except Exception as e:
                logger.error(f"Erro (dentro do semáforo) ao processar {redis_key}: {e}", exc_info=True)
            
    async def _process_scheduled_batch(self, redis_key: str):
        try:
            new_messages: List[Dict[str, Any]] = (
                await self.redis_queue.get_pending_messages(redis_key)
            )

            if len(new_messages) > 0:
                phone_number = redis_key.split(":", 1)[-1]

                await self._process_single_batch(phone_number, new_messages)

                logger.info(f"Batch processado com sucesso para {phone_number} ({len(new_messages)} msgs)")
            else:
                logger.info(f"Nenhuma mensagem pendente para {redis_key} (batch vazio)")

        except Exception as e:
            logger.error(f"Erro ao processar batch agendado para {redis_key}: {e}", exc_info=True)

    async def _process_single_batch(
        self, phone_number: str, messages: List[Dict[str, Any]]
    ):
        """
        --- LÓGICA IMPLEMENTADA ---
        Processa um único lote de mensagens, buscando histórico e chamando o orquestrador.
        """
        logger.info(f"Enviando lote de {phone_number} ({len(messages)} msgs) para o Orquestrador.")
        try:
            history = await self.message_repository.get_history(phone_number, limit=10)

            formatted_new_messages = [
                {"role": "user", "content": msg.get("Mensagem", "")} 
                for msg in messages if msg.get("Mensagem")
            ]
            
            if not formatted_new_messages:
                logger.warning(f"Batch para {phone_number} não continha mensagens válidas.")
                return

            full_context = history + formatted_new_messages

            await self.orchestrator.execute(context=full_context, phone=phone_number)

            try:
                for msg_data in messages:
                    await self.message_repository.save(
                        phone_number, 
                        msg_data.get("Mensagem", ""),
                        "user"
                    )
            except Exception as e:
                logger.error(f"Falha ao salvar histórico do usuário {phone_number}: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Erro crítico ao chamar o Orquestrador para {phone_number}: {e}", exc_info=True)


    async def stop_monitoring(self):
        """Para o monitoramento gracefuly"""
        self._shutting_down = True

        tasks_to_cancel: List[Any] = []
        if self._batch_monitor_task and not self._batch_monitor_task.done():
            tasks_to_cancel.append(self._batch_monitor_task)
        if self._auto_stop_task and not self._auto_stop_task.done():
            tasks_to_cancel.append(self._auto_stop_task)

        for task in tasks_to_cancel:
            try:
                task.cancel()
            except RecursionError:
                logger.error("RecursionError ao cancelar task; ignorando")
                continue

        if tasks_to_cancel:
            try:
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            except RecursionError:
                logger.error("RecursionError ao aguardar cancelamento; prosseguindo")

        logger.info("Monitor de batches parado")

    async def cleanup(self):
        """Limpeza de recursos"""
        await self.stop_monitoring()
        awaitables: List[Any] = []
        for task in self.processing_tasks.values():
            try:
                if asyncio.isfuture(task) or inspect.isawaitable(task):
                    try: task.cancel()
                    except Exception: pass
                    awaitables.append(task)
                elif hasattr(task, "cancel"):
                    try: task.cancel()
                    except Exception: pass
            except Exception:
                continue

        if awaitables:
            await asyncio.gather(*awaitables, return_exceptions=True)
        
        logger.info("MessageQueueService cleanup finalizado.")'''