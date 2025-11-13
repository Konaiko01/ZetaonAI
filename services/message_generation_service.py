import logging
from interfaces.clients.chat_interface import IChat # (Assumindo que você tem um cliente de chat, ex: WhatsApp)

logger = logging.getLogger(__name__)

class MessageGenerationService:
    def __init__(self, chat_client: IChat):
        self.chat_client = chat_client
        logger.info("MessageGenerationService inicializado.")

    async def send_message(self, phone: str, message: str):
        if not message or not phone:
            logger.warning("[MessageGenerationService]Tentativa de enviar mensagem vazia ou sem destinatário.")
            return

        try:
            # Inserir logica de envio de texto aqui
            logger.info(f"[MessageGenerationService]Mensagem enviada para {phone} com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {phone}: {e}", exc_info=True)
            # Você pode querer adicionar um retry ou notificar o admin aqui