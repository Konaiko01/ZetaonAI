from clients.openai_client import OpenIAClient
from interfaces.clients.ia_interface import IAI
from utils.logger import logger
from typing import Any
from services.crypto.wpp_decoder import Decoder
import httpx 
import base64
import io    
#--------------------------------------------------------------------------------------------------------------------#
class MediaProcessorService:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, ai_client: IAI, decoder: Decoder):
        self.client = ai_client 
        self.decodificador = decoder
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("[MediaProcessorService] Inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    async def verified_message(self, data: dict[str, Any]) -> str | None:     
        try:  
            texto_simples = data.get('conversation') or \
                data.get('extendedTextMessage', {}).get('text')
            if texto_simples:
                logger.info("Mensagem identificada como TEXTO.")
                return texto_simples
            elif data.get('audioMessage', {}):
                info_audio = data.get('audioMessage', {})
                logger.info("Mensagem identificada como ÁUDIO. Iniciando transcrição.")
                chave_midia_obj = info_audio.get('mediaKey') # <-- Isto é um dict
                mime_type = info_audio.get('mimetype')
                url_audio = info_audio.get('url')
                
                if not all([url_audio, chave_midia_obj, mime_type]):
                    logger.error("Payload de áudio incompleto (faltando url, mediaKey ou mimetype).")
                    return None
                
                chave_midia_base64 = None
                if isinstance(chave_midia_obj, dict):
                    try:
                        sorted_keys = sorted(chave_midia_obj.keys(), key=int)
                        media_key_bytes = bytes([chave_midia_obj[k] for k in sorted_keys])            
                        chave_midia_base64 = base64.b64encode(media_key_bytes).decode('utf-8')
                        
                    except Exception as e:
                        logger.error(f"Falha ao converter o objeto mediaKey (dict) para Base64: {e}")
                        return None
                elif isinstance(chave_midia_obj, str):
                    chave_midia_base64 = chave_midia_obj
                else:
                    logger.error(f"Formato de mediaKey inesperado: {type(chave_midia_obj)}")
                    return None       
                return await self.transcricao_audio(url_audio, chave_midia_base64, mime_type)
            else:            
                logger.info("Mensagem não é texto ou mídia suportada.")
                return None
        except Exception as e:
            logger.error(f"Erro ao verificar o tipo de mensagem: {e}", exc_info=True)
            return None
        
#--------------------------------------------------------------------------------------------------------------------#
    
    async def treated_message(self, data: dict[str, Any])-> dict:
        """
        Processa o payload, extrai os dados relevantes e retorna um 
        dicionário padronizado para o controlador.
        """
        
        try:
            data_obj = data.get('data', {})
            key_obj = data_obj.get('key', {})
            if key_obj.get('fromMe', False):
                return {"status": "ok", "message": "Mensagem de saída ignorada."}

            message_data = data_obj.get('message', {})
            if not message_data:
                status = data_obj.get('status')
                if status: return {"status": "ok", "message": f"Evento de status ({status}) ignorado."}
                return {"status": "ok", "message": "Payload inválido (sem 'message')."}

            input_text = await self.verified_message(message_data)
            if input_text is None:
                return {"status": "ok", "message": "Não é uma mensagem de texto/mídia suportada."}
            
            chat_id = key_obj.get('remoteJidAlt', '')
            user_auth_id = "" 
            phone_jid = ""   
            group_id = None 

            if chat_id.endswith('@g.us'):
                group_id = chat_id
                user_auth_id = key_obj.get('participant', '')  
                phone_jid = key_obj.get('remoteJid', '') 
                logger.info(f"Mensagem recebida do GRUPO {group_id}")
            else:
                user_auth_id = key_obj.get('remoteJidAlt', '') 
                phone_jid = key_obj.get('remoteJid', '') 
                logger.info("Mensagem recebida de DM.")

            if not user_auth_id:
                user_auth_id = phone_jid
                logger.warning(f"Não foi possível encontrar @lid (senderLid/participant). Usando JID do telefone ({phone_jid}) como AuthId.")
            
            if not phone_jid:
                phone_jid = user_auth_id
                logger.warning(f"Não foi possível encontrar JID do telefone (participantPn). Usando AuthId ({user_auth_id}) como JID.")

            logger.info(f"ID Telefone: {phone_jid} | ID Auth: {user_auth_id} (Grupo: {group_id})")
            return {
                'Mensagem': input_text, 
                'Numero': phone_jid,  
                'AuthId': user_auth_id,
                'GroupId': group_id 
            }
            
        except Exception as e:
            logger.error(f"Erro crítico ao tratar a mensagem: {e}", exc_info=True)
            return {"status": "error", "message": f"Erro interno: {e}"}

#--------------------------------------------------------------------------------------------------------------------#

    async def transcricao_audio(self, url_audio: str, chave_midia_base64: str, mime_type: str) -> str | None: 
        try:
            logger.info(f"Baixando áudio de: {url_audio[:50]}...")
            response = await self.http_client.get(url_audio)
            response.raise_for_status()
            encrypted_bytes = response.content
            encrypted_buffer = io.BytesIO(encrypted_bytes)
            logger.info("Áudio criptografado baixado. Descriptografando...")
            decrypted_buffer = self.decodificador.decodificar_buffer(
                buffer_criptografado=encrypted_buffer,
                chave_midia_base64=chave_midia_base64,
                mime_type=mime_type
            )
            logger.info("Áudio descriptografado. Enviando para transcrição...")
            transcricao = await self.client.transcribe_audio(decrypted_buffer)  
            logger.info(f"Transcrição concluída: {transcricao[:30]}...")
            return transcricao

        except httpx.RequestError as e:
            logger.error(f"Falha ao BAIXAR o áudio: {e}", exc_info=True)
            return None
        except ImportError as e:
            logger.critical(f"ERRO DE DEPENDÊNCIA: {e}. Você instalou 'pycryptodome'? (pip install pycryptodome)")
            return None
        except Exception as e:
            logger.error(f"Falha no pipeline de transcrição: {e}", exc_info=True)
            return None
    