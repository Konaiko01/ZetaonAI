from ..utils.logger import logger
from ..services.media_processor_service import MediaProcessorService
from ..services.message_queue_service import MessageQueueService
from ..services.group_authorization_service import GroupAuthorizationService
from ..infrastructure import client_mongo

#--------------------------------------------------------------------------------------------------------------------#
class MessageProcessController:
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self, 
                 message_service: MessageQueueService,
                 media_service: MediaProcessorService,
                 group_auth_service: GroupAuthorizationService = None):
        self.processor = media_service
        self.queue = message_service
        self.group_auth = group_auth_service or GroupAuthorizationService(client_mongo)


#--------------------------------------------------------------------------------------------------------------------#


    def control(self, data: dict):
        """Processar mensagem recebida com validação de autorização.

        Fluxo:
        1. Extrai phone_number da mensagem
        2. Valida se usuário está em um grupo autorizado
        3. Se autorizado, processa e coloca na fila
        4. Se não autorizado, registra e retorna erro

        Args:
            data: Payload do webhook da Evolution
        """
        try:
            # Extrai informações da mensagem
            phone_number = data.get("from", "").replace("@s.whatsapp.net", "")
            
            if not phone_number:
                logger.warning("Mensagem sem phone_number detectada")
                return {"status": "error", "message": "Phone number não encontrado"}

            # TODO: Buscar lista de grupos autorizados de configuração/ambiente
            # authorized_group_ids = ["120363295648424210@g.us", "120363295648424211@g.us"]
            
            # Por enquanto, comentado para não quebrar fluxo existente
            # Descomentar quando grupos estiverem configurados
            # is_authorized = self.group_auth.is_user_in_any_authorized_group(
            #     phone_number,
            #     authorized_group_ids
            # )
            
            # if not is_authorized:
            #     logger.warning(f"Usuário {phone_number} não está autorizado")
            #     return {"status": "unauthorized", "message": "Usuário não autorizado para usar o agent"}

            # Processa a mensagem
            self.processor.process(data)
            
            # Adiciona à fila
            self.queue.add_message(phone_number, data)
            
            logger.info(f"Mensagem de {phone_number} processada com sucesso")
            return {"status": "success", "message": "Mensagem processada"}

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return {"status": "error", "message": str(e)}
        