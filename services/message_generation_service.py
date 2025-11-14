#
# services/message_generation_service.py (MODIFICADO)
#
import logging
from interfaces.clients.chat_interface import IChat 

logger = logging.getLogger(__name__)

class MessageGenerationService:
    def __init__(self, chat_client: IChat):
        self.chat_client = chat_client
        logger.info("MessageGenerationService inicializado.")

    async def send_message(self, phone: str, message: str):
        if not message or not phone:
            logger.warning("[MessageGenerationService] Tentativa de enviar mensagem vazia ou sem destinatário.")
            return

        try:
            # --- INÍCIO DA MUDANÇA ---
            # Assume que seu IChat (EvolutionClient) tem um método 'send_message'
            # (Se o método for async, adicione 'await' aqui)
            success = self.chat_client.send_message(phone, message)
            
            if success:
                logger.info(f"[MessageGenerationService] Mensagem enviada para {phone} com sucesso.")
            else:
                logger.error(f"[MessageGenerationService] Falha ao enviar mensagem para {phone} (cliente retornou 'false').")
            # --- FIM DA MUDANÇA ---
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {phone}: {e}", exc_info=True)