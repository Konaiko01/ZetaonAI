from ..utils.logger import logger
from..services.media_processor import MediaProcessor
#--------------------------------------------------------------------------------------------------------------------#
class MessageProcessController:
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self):
        processor = MediaProcessor()


#--------------------------------------------------------------------------------------------------------------------#


    def ProcessIncomingMessage(self, data: dict): ...
        
    #fazer logica para que receba a mensagem e coloque ela na fila(queue)
        