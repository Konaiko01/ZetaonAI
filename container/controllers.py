from ..controllers.message_process_controller import MessageProcessController
from container.services import ServiceContainer 
from ..utils.logger import logger

class ControllerContainer:

    def __init__(self, services: ServiceContainer):
        self._services = services
        try:
            self._message_process_controller = MessageProcessController(
                message_service=self._services.message_queue_service,
                media_service=self._services.media_processor_service
            )
        except AttributeError as e:
            logger.error(f"[ControllerContainer] Falha ao injetar serviços: {e}")
            logger.error("Verifique se os nomes das propriedades em ServiceContainer estão corretos.")
            raise e

    @property
    def process_message(self) -> MessageProcessController:
        return self._message_process_controller