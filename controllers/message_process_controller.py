from ..utils.logger import logger
from ..services.media_processor_service import MediaProcessorService
from ..services.message_queue_service import MessageQueueService

#--------------------------------------------------------------------------------------------------------------------#
class MessageProcessController:
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self):
        processor = MediaProcessorService()
        queue = MessageQueueService()


#--------------------------------------------------------------------------------------------------------------------#


    def control(self, data: dict): ...
        
    #fazer logica para que receba a mensagem e coloque ela na fila(queue)
    #usar media processor para coletar os dados e message queue para adicionar na fila
        