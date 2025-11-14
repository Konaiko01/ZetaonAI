from utils.logger import logger
from services.media_processor_service import MediaProcessorService
from services.message_queue_service import MessageQueueService
from services.group_autorization_service import GroupAuthorizationService
from typing import Any

#--------------------------------------------------------------------------------------------------------------------#
class MessageProcessController:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self,
                 message_service: MessageQueueService,
                 media_service: MediaProcessorService,
                 group_auth_service: GroupAuthorizationService):
        self.media_service = media_service
        self.queue_service = message_service
        self.group_auth = group_auth_service # (Recebe o serviço 'async' corrigido)
        logger.info("MessageProcessController (async) inicializado com sucesso.")

#--------------------------------------------------------------------------------------------------------------------#

    async def control(self, data: dict) -> tuple[dict[str, Any], int]:
        logger.debug(f"[MessageProcessController]Controlador recebeu dados: {data}")
        try:
            processed_data = await self.media_service.treated_message(data)
            
            auth_id = processed_data.get('GroupId')
            phone_number = processed_data.get('Numero')
            message_content = processed_data.get('Mensagem')

            if not phone_number or not message_content:
                logger.info(f"[MessageProcessController]Mensagem ignorada. Motivo: {processed_data.get('message', 'Formato inválido')}")
                return ({"status": "received_ignored", "detail": processed_data.get('message')}, 200)
            
            authorized_group_ids = ["120363424101109821@g.us"]
            
            is_authorized = await self.group_auth.is_user_in_any_authorized_group(
                 auth_id,
                 authorized_group_ids
            )
            
            if not is_authorized:
                logger.warning(f"Usuário {phone_number} não está autorizado")
                return ({"status": "unauthorized", "message": "Usuário não autorizado para usar o agent"}, 403) # (Status 403 é melhor)
            
            await self.queue_service.enqueue_message(
                phone_number=phone_number, 
                message_data=processed_data 
            )

            logger.info(f"[MessageProcessController]Mensagem de {phone_number} adicionada com sucesso à fila.")
            
            return ({"status": "received_queued", "detail": f"Mensagem de {phone_number} enfileirada."}, 200)

        except Exception as e:
            logger.error(f"[MessageProcessController]Erro crítico no controlador ao processar mensagem: {e}", exc_info=True)
            return ({"status": "error", "detail": "Falha interna ao processar a mensagem."}, 500)