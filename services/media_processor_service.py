from clients.openai_client import OpenIAClient
from utils.logger import logger
from typing import List, Dict, Union, Any
from services.crypto.wpp_decoder import Decoder

#--------------------------------------------------------------------------------------------------------------------#
class MediaProcessorService:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self):
        self.client =  OpenIAClient() 
        self.decodificador = Decoder()

#--------------------------------------------------------------------------------------------------------------------#

    async def verified_message(self, data: Dict[str, Any]) -> str | None:     
        """Verifica o tipo de mensagem (texto, áudio) e retorna o conteúdo."""
        # (Esta função está correta, permanece a mesma)
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
                logger.info("Mensagem não é texto ou mídia suportada.")
                return None
        except Exception as e:
            logger.error(f"Erro ao verificar o tipo de mensagem: {e}", exc_info=True)
            return None
        
#--------------------------------------------------------------------------------------------------------------------#
    
    # --- FUNÇÃO CORRIGIDA ---
    async def treated_message(self, data: Dict[str, Any])-> dict:
        """
        Processa o payload, extrai os dados relevantes e retorna um 
        dicionário padronizado para o controlador.
        """
        
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

            # --- LÓGICA DE EXTRAÇÃO DO @LID CORRIGIDA ---
            
            chat_id = key_obj.get('remoteJid', '') 
            user_auth_id = "" # ID a ser usado para autorização
            group_id = None 

            if chat_id.endswith('@g.us'):
                # É um grupo: Pega o @lid do participant
                user_auth_id = key_obj.get('participant', '') 
                logger.info(f"Mensagem recebida do GRUPO {group_id}")
            else:
                # É DM: Pega o @lid do senderLid
                user_auth_id = key_obj.get('senderLid', '') 
                logger.info("Mensagem recebida de DM.")
            
            if not user_auth_id:
                # Fallback (se senderLid não existir na DM, usa o JID do telefone)
                if not chat_id.endswith('@g.us'):
                    user_auth_id = chat_id
                    logger.warning(f"Não foi possível encontrar @lid (senderLid). Usando remoteJid ({user_auth_id}) como fallback.")
                else:
                    logger.error("Não foi possível identificar o remetente (@lid) no grupo.")
                    return {"status": "ok", "message": "Não foi possível identificar o remetente."}
            
            # --- FIM DA CORREÇÃO ---

            logger.info(f"ID de Autenticação: {user_auth_id} (Grupo: {group_id})")
            return {
                'Mensagem': input_text, 
                'Numero': user_auth_id, # <-- Este é o ID que será validado
                'GroupId': group_id 
            }
            
        except Exception as e:
            logger.error(f"Erro crítico ao tratar a mensagem: {e}", exc_info=True)
            return {"status": "error", "message": f"Erro interno: {e}"}

#--------------------------------------------------------------------------------------------------------------------#

    async def transcricao_audio(self, url_audio: str, chave_midia: str, mime_type: str) -> str | None: 
        logger.warning("transcricao_audio AINDA NÃO IMPLEMENTADO.")
        return "[Transcrição de Áudio Simulada]"
    
# ... (restante do arquivo)