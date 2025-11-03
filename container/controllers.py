from ..controllers.message_process_controller import MessageProcessController
from container.services import ServiceContainer 


class ControllerContainer:

    def __init__(self, services: ServiceContainer):
        self._services = services

    @property
    def process_message(self) -> MessageProcessController:
        return MessageProcessController.control(
            #service=self._services.message_queue_service????
        )
