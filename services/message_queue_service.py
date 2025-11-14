import asyncio
from utils.logger import logger
from interfaces.repositories.context_repository_interface import IContextRepository
from interfaces.repositories.message_fragment_repository_interface import IMessageFragmentRepository
from services.response_orchestrator_service import ResponseOrchestratorService

class MessageQueueService:

    def __init__(
        self,
        orchestrator: ResponseOrchestratorService,
        context_repository: IContextRepository,       
        fragment_repository: IMessageFragmentRepository 
    ):
        self.DEBOUNCE_PERIOD_SECONDS = 8.0 
        self.orchestrator = orchestrator
        self.context_repo = context_repository
        self.fragment_repo = fragment_repository
        self.active_debounce_timers: dict[str, asyncio.Task] = {}      
        logger.info(
            f"MessageQueueService (Debounce) inicializado. "
            f"Tempo de espera: {self.DEBOUNCE_PERIOD_SECONDS}s."
        )

    async def enqueue_message(self, phone: str, message: str):
        logger.info(f"[{phone}] Mensagem enfileirada. Resetando timer de {self.DEBOUNCE_PERIOD_SECONDS}s.")
        fragment_key = self._get_fragment_key(phone)
        await self.fragment_repo.add_fragment(fragment_key, message)

        if phone in self.active_debounce_timers:
            self.active_debounce_timers[phone].cancel() 
        
        self.active_debounce_timers[phone] = asyncio.create_task(self._process_message_batch(phone))

    async def _process_message_batch(self, phone: str):
        try:
            await asyncio.sleep(self.DEBOUNCE_PERIOD_SECONDS)
            
            logger.info(f"[{phone}] Timer expirou. Processando lote de mensagens...")
            fragment_key = self._get_fragment_key(phone)
            fragments = await self.fragment_repo.get_and_clear_fragments(fragment_key)
            
            if not fragments:
                logger.warning(f"[{phone}] Timer expirou, mas não há fragmentos. Ignorando.")
                return
            full_message = " ".join(map(str, fragments))
            logger.info(f"[{phone}] Mensagem completa montada: '{full_message}'")

            context_data = await self.context_repo.get_context(phone)
            history = context_data.get("history", []) if context_data else []
            
            history.append({"role": "user", "content": full_message})

            output_history = await self.orchestrator.execute(history, phone)

            await self.context_repo.save_context(phone, {"history": output_history})
            logger.info(f"[{phone}] Processamento e salvamento de contexto concluídos.")

        except asyncio.CancelledError:
            logger.info(f"[{phone}] Timer resetado (nova mensagem chegou).")
        
        except Exception as e:
            logger.error(f"[{phone}] Erro crítico ao processar lote: {e}", exc_info=True)
            
        finally:
            self.active_debounce_timers.pop(phone, None)

    def _get_fragment_key(self, phone: str) -> str:
        return f"fragments:{phone}"

    async def cleanup(self):
        logger.info("Desligando MessageQueueService... Cancelando timers ativos...")
        tasks = list(self.active_debounce_timers.values())
        for task in tasks:
            task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.active_debounce_timers.clear()
        logger.info("Timers cancelados. Desligamento concluído.")