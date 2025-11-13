import asyncio
from asyncio import Semaphore
from asyncio import Semaphore
import logging
from typing import Dict, Any, List, Optional
from config import settings
from services.response_orchestrator_service import ResponseOrchestratorService
from typing import Dict, Any, List, Optional
import infrastructure

logger = logging.getLogger(__name__)


class MessageQueueService:
    def __init__(
        self,
        orchestrator: ResponseOrchestratorService,
        message_repository: infrastructure.mongoDB.MongoDB,
        redis_queue: infrastructure.redis_queue.RedisQueue,
    ):
        self.processing_tasks: Dict[str, asyncio.Task[Any]] = {}
        self._shutting_down = False
        self._batch_monitor_task: Optional[asyncio.Task[Any]] = None
        self._auto_stop_task: Optional[asyncio.Task[Any]] = None
        self._monitor_duration = settings.monitor_timeout  # duração em segundos
        self._monitoring_active = False  # Flag para controlar se o monitor está ativo

        # Controla o número máximo de tasks simultâneas
        self.max_concurrent = settings.max_concurrent
        self._semaphore = Semaphore(self.max_concurrent)

        self.orchestrator = orchestrator
        self.message_repository = message_repository
        self.redis_queue = redis_queue

    async def refresh_monitoring_cycle(self):
        """Inicia ou reinicia o monitoramento contínuo dos lotes"""
        # Se já está monitorando, apenas reinicia o timer de auto-stop
        if self._monitoring_active:
            await self._restart_auto_stop_timer()
            logger.debug("Timer de auto-stop reiniciado")
            return

        logger.debug("Iniciando novo timer de auto-stop")
        # Se não está monitorando, inicia tudo
        self._shutting_down = False
        self._monitoring_active = True

        # Inicia o monitor se não estiver rodando
        if not self._batch_monitor_task or self._batch_monitor_task.done():
            self._batch_monitor_task = asyncio.create_task(self._monitor_batches())
            logger.info("Monitor de batches iniciado")

        # Agenda auto-stop
        await self._restart_auto_stop_timer()
        logger.info(
            f"Monitor será encerrado em {self._monitor_duration} segundos de inatividade"
        )

    async def add_message(self, phone_number: str, message_data: Dict[str, Any]):
        """Adiciona mensagem ao Redis e agenda processamento"""
        if self._shutting_down:
            logger.warning("Serviço está desligando, mensagem ignorada")
            logger.warning("Serviço está desligando, mensagem ignorada")
            return

        try:
            # Adiciona a mensagem ao Redis (método assíncrono)
            await self.redis_queue.add_message(phone_number, message_data)
            logger.debug(f"Mensagem adicionada para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem para {phone_number}: {e}")
            logger.error(f"Erro ao adicionar mensagem para {phone_number}: {e}")
            raise e

    async def _restart_auto_stop_timer(self):
        """Reinicia o timer de auto-stop"""
        # Cancela o timer anterior se existir
        if self._auto_stop_task and not self._auto_stop_task.done():
            self._auto_stop_task.cancel()
            try:
                await self._auto_stop_task
            except asyncio.CancelledError:
                logger.debug("Timer de auto-stop anterior cancelado")

        # Cria novo timer
        self._auto_stop_task = asyncio.create_task(self._auto_stop_monitoring())

    async def _auto_stop_monitoring(self):
        """Agenda o encerramento automático do monitoramento após período de inatividade"""
        logger.debug(f"Auto-stop: aguardando {self._monitor_duration}s")
        try:
            await asyncio.sleep(self._monitor_duration)
        except asyncio.CancelledError:
            # Cancelamento esperado ao reiniciar o timer; sair silenciosamente
            await asyncio.sleep(self._monitor_duration)

        # Se chegou aqui, o tempo expirou — fazer o stop normalmente
        try:
            await self.stop_monitoring()
            logger.info("Monitor de batches encerrado automaticamente por inatividade")
        except Exception as e:
            logger.error(f"Erro ao encerrar monitor no auto-stop: {e}")

    async def _monitor_batches(self):
        """Monitora continuamente os lotes com limite de concorrência (em paralelo)"""
        logger.info(f"--- Monitoramento iniciado")

        while not self._shutting_down:
            try:
                phones_numbers: List[str] = (
                    await self.redis_queue.get_messages_batches()
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

            except asyncio.CancelledError as e:
                logger.debug("Monitor de batches cancelado")
                break
            except Exception as e:
                logger.error(f"Erro no monitor: {e}")

            # Pequena pausa para não sobrecarregar
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                logger.debug("Monitor de batches cancelado durante sleep")
                await asyncio.sleep(1)

    async def _process_with_limit(self, phone_number: str) -> None:
        """Processa um telefone respeitando o limite de concorrência"""
        async with self._semaphore:
            try:
                logger.debug(
                    f"Iniciando processamento de {phone_number} "
                    f"(semaphore: {self._semaphore._value}/{self.max_concurrent})"
                )

                await self._process_scheduled_batch(phone_number)

            except Exception as e:
                logger.error(f"Erro ao processar {phone_number}: {e}")
                raise

    async def _process_scheduled_batch(self, phone_number: str):
        """Processa um lote agendado"""
        try:
            await self.redis_queue.delete(f"debounce:{phone_number}")

            # Recupera e processa as mensagens
            messages: List[Dict[str, Any]] = (
                await self.redis_queue.get_pending_messages(phone_number)
            )

            if len(messages) > 0:
                await self._process_single_batch(phone_number, messages)

                logger.info(
                    f"Batch processado com sucesso para {phone_number} ({len(messages)} msgs)"
                )
            else:
                logger.info(
                    f"Nenhuma mensagem pendente para {phone_number} (batch vazio)"
                )

        except Exception as e:
            logger.error(
                f"Erro ao processar batch agendado para {phone_number}: {e}",
                exc_info=True,
            )

    async def _process_single_batch(
        self, phone_number: str, messages: List[Dict[str, Any]]
    ):
        """Processa um único lote de mensagens"""
        # TODO: Implementar a lógica real de processamento
        logger.info(f"Processando {len(messages)} mensagens para {phone_number}")

    async def stop_monitoring(self):
        """Para o monitoramento com proteção contra RecursionError"""
        self._shutting_down = True
        self._monitoring_active = False

        logger.debug("Iniciando parada graceful do monitoramento...")

        # Usa asyncio.shield para evitar cancelamento recursivo
        try:
            # Para o batch monitor
            if self._batch_monitor_task and not self._batch_monitor_task.done():
                try:
                    self._batch_monitor_task.cancel()
                    # Aguarda com shield para proteger da recursão
                    await asyncio.wait_for(
                        asyncio.shield(self._batch_monitor_task), timeout=3.0
                    )
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    logger.warning("Timeout ao parar batch monitor")

            # Para o auto-stop task
            if self._auto_stop_task and not self._auto_stop_task.done():
                try:
                    self._auto_stop_task.cancel()
                    await asyncio.wait_for(
                        asyncio.shield(self._auto_stop_task), timeout=2.0
                    )
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    logger.warning("Timeout ao parar auto-stop task")

        except Exception as e:
            logger.error(f"Erro durante parada do monitoramento: {e}")

        logger.debug("Monitor de batches parado com sucesso")

    async def cleanup(self):
        """Limpeza de recursos - versão iterativa"""
        await self.stop_monitoring()

        # Coleta todas as tasks de processamento
        processing_tasks = list(self.processing_tasks.values())
        self.processing_tasks.clear()

        # Cancela tasks de forma iterativa
        for task in processing_tasks:
            try:
                if asyncio.isfuture(task) and not task.done():
                    task.cancel()
            except Exception as e:
                logger.debug(f"Erro ao cancelar task de processamento: {e}")

        # Aguarda cancelamento com timeout
        if processing_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*processing_tasks, return_exceptions=True),
                    timeout=3.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Timeout ao aguardar cancelamento de tasks de processamento"
                )
            except Exception as e:
                logger.error(f"Erro no cleanup: {e}")
