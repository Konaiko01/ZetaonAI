from ..controllers.process_incoming_message import MessageProcessController
from container.services import ServiceContainer 


class ControllerContainer:

    def __init__(self, services: ServiceContainer):
        self._services = services

    @property
    def process_incoming_message(self) -> MessageProcessController:
        return MessageProcessController.ProcessIncomingMessage(
            service=self._services.message_queue_service,
        )
