from interfaces.clients.chat_interface import IChat 
from utils.logger import logger

#--------------------------------------------------------------------------------------------------------------------#
class MessageSendService:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, chat_client: IChat):
        self.chat_client = chat_client
        logger.info("MessageSendService inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    async def send_message(self, phone: str, message: str):
        if not message or not phone:
            logger.warning("[MessageSendService] Tentativa de enviar mensagem vazia ou sem destinatário.")
            return
        phone_jid = f"{phone}@s.whatsapp.net"


        try:
            success = await self.chat_client.send_message(phone_jid, message)
            if success:
                logger.info(f"[MessageSendService] Mensagem enviada para {phone_jid} com sucesso.")
            else:
                logger.error(f"[MessageSendService] Falha ao enviar mensagem para {phone_jid} (cliente retornou 'false').")
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {phone_jid}: {e}", exc_info=True)