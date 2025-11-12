from ..utils.logger import logger
from ..services.media_processor_service import MediaProcessorService
from ..services.message_queue_service import MessageQueueService
from typing import Any

#--------------------------------------------------------------------------------------------------------------------#
class MessageProcessController:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, 
                 message_service: MessageQueueService,
                 media_service: MediaProcessorService):
        self.media_service = media_service
        self.queue_service = message_service
        logger.info("MessageProcessController inicializado com sucesso.")

#--------------------------------------------------------------------------------------------------------------------#

    def control(self, data: dict) -> dict[str, Any]:
        logger.debug(f"[MessageProcessController]Controlador recebeu dados: {data}")
        try:
            processed_data = self.media_service.treated_message(data)
            
            phone_number = processed_data.get('Numero')
            message_content = processed_data.get('Mensagem')

            if not phone_number or not message_content:
                logger.info(f"[MessageProcessController]Mensagem ignorada. Motivo: {processed_data.get('message', 'Formato inválido')}")
                return {"status": "received_ignored", "detail": processed_data.get('message')}

            # 3. Adicionar à fila do Redis
            # (Isto funcionará após a correção no Passo 2)
            self.queue_service.add_message(
                phone_number=phone_number, 
                message_data=processed_data 
            )

            logger.info(f"[MessageProcessController]Mensagem de {phone_number} adicionada com sucesso à fila.")
            
            # 4. Retornar sucesso imediato para o webhook
            return {"status": "received_queued", "detail": f"Mensagem de {phone_number} enfileirada."}

        except Exception as e:
            logger.error(f"[MessageProcessController]Erro crítico no controlador ao processar mensagem: {e}", exc_info=True)
            # Em caso de falha, é importante que o webhook saiba
            # Você pode querer usar HTTPException aqui se estiver no contexto do FastAPI
            return {"status": "error", "detail": "Falha interna ao processar a mensagem."}