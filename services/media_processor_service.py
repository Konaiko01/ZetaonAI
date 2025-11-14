from clients.openai_client import OpenIAClient
from utils.logger import logger
from typing import Any

#--------------------------------------------------------------------------------------------------------------------#
class MediaProcessorService:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self):
        self.client =  OpenIAClient() 

#--------------------------------------------------------------------------------------------------------------------#

    async def verified_message(self, data: dict[str, Any]) -> str | None:     
        try:  
            texto_simples = data.get('conversation') or \
                data.get('extendedTextMessage', {}).get('text')
            if texto_simples:
                logger.info("Mensagem identificada como TEXTO.")
                return texto_simples
            elif data.get('audioMessage', {}):
                logger.info("Mensagem identificada como ÁUDIO. Iniciando transcrição.")
                return await self.transcricao_audio(None, None, None)
            else:            
                logger.info("[MediaProcessorService]Mensagem não é texto ou mídia suportada.")
                return None
        except Exception as e:
            logger.error(f"[MediaProcessorService]Erro ao verificar o tipo de mensagem: {e}", exc_info=True)
            return None
        
#--------------------------------------------------------------------------------------------------------------------#
    
    # --- FUNÇÃO CORRIGIDA ---
    async def treated_message(self, data: dict[str, Any])-> dict:
        try:
            data_obj = data.get('data', {})
            if not data_obj:
                return {"status": "ok", "message": "Payload inválido (sem 'data')."}
            
            key_obj = data_obj.get('key', {})
            if key_obj.get('fromMe', False):
                return {"status": "ok", "message": "Mensagem de saída ignorada."}

            message_data = data_obj.get('message', {})
            if not message_data:
                status = data_obj.get('status')
                if status:
                    return {"status": "ok", "message": f"Evento de status ({status}) ignorado."}
                return {"status": "ok", "message": "Payload inválido (sem 'message')."}

            input_text = await self.verified_message(message_data)

            if input_text is None:
                return {"status": "ok", "message": "Não é uma mensagem de texto/mídia suportada."}
            
            chat_id = key_obj.get('remoteJid', '') 
            user_auth_id = "" 
            phone_jid = ""    
            group_id = None 

            if chat_id.endswith('@g.us'):
                # É um grupo
                group_id = chat_id
                user_auth_id = key_obj.get('participant', '')  
                phone_jid = key_obj.get('participantPn', '') 
                logger.info(f"[MediaProcessorService]Mensagem recebida do GRUPO {group_id}")
            else:
                # É DM
                user_auth_id = key_obj.get('senderLid', '') 
                phone_jid = chat_id                        
                logger.info("[MediaProcessorService]Mensagem recebida de DM.")
            
            if not user_auth_id:
                user_auth_id = phone_jid
                logger.warning(f"[MediaProcessorService]Não foi possível encontrar @lid. Usando JID do telefone ({phone_jid}) como AuthId.")
            if not phone_jid:
                phone_jid = user_auth_id
                logger.warning(f"[MediaProcessorService]Não foi possível encontrar JID do telefone. Usando AuthId ({user_auth_id}) como JID.")
            
            # --- FIM DA LÓGICA ---

            logger.info(f"ID Telefone: {phone_jid} | ID Auth: {user_auth_id} (Grupo: {group_id})")
            return {
                'Mensagem': input_text, 
                'Numero': phone_jid,    
                'AuthId': user_auth_id,  
                'GroupId': group_id 
            }
            
        except Exception as e:
            logger.error(f"[MediaProcessorService]Erro crítico ao tratar a mensagem: {e}", exc_info=True)
            return {"status": "error", "message": f"Erro interno: {e}"}