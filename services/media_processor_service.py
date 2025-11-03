from openai import OpenAI
from ..utils import logger
from typing import List, Dict, Union, Any
from services.crypto.wpp_decoder import Decoder


#--------------------------------------------------------------------------------------------------------------------#
class MediaProcessorService:
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self, key: str, temp_media_dir: str):
        self.client =  OpenAI(api_key=key) 
        self.decodificador = Decoder()


#--------------------------------------------------------------------------------------------------------------------#


    def verified_message(self, data) -> str | None:     
        try:  
            texto_simples = data.get('conversation') or \
                data.get('extendedTextMessage', {}).get('text')
            if texto_simples:
                logger.info("Mensagem identificada como TEXTO.")
                return texto_simples

            elif data.get('audioMessage', {}):
                info_audio = data.get('audioMessage', {})
                logger.info("Mensagem identificada como ÁUDIO. Iniciando transcrição.")
                chave_midia = info_audio.get('mediaKey')
                mime_type = info_audio.get('mimetype')
                url_audio = info_audio.get('url')
                return self.transcricao_audio(url_audio, chave_midia, mime_type)

            else:            
                logger.info("Mensagem não é texto ou mídia suportada (áudio, imagem, pdf).")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao verificar e processar o tipo de mensagem: {e}", exc_info=True)
            return None
        

#--------------------------------------------------------------------------------------------------------------------#
    
    
    def treated_message(self, data)-> dict:

        message_data = data.get('message', {})
        input_text = self.verified_message(message_data)

        if input_text is None:
            logger.info("Mensagem ignorada: não é um texto simples ou formato de mídia suportado.")
            return {"status": "ok", "message": "Não é uma mensagem de texto/mídia suportada."}

        numero_completo = message_data.get('remoteJid', '')
        numero = numero_completo.split('@')[0]

        logger.info(f"Mensagem recebida. De: {numero}.")
        return {'Mensagem': input_text, 'Numero': numero}


#--------------------------------------------------------------------------------------------------------------------#

    def transcricao_audio(self, url_audio: str, chave_midia: str, mime_type: str) -> str | None: ...
        #fazer nova nlogica de transcrição de midia

#--------------------------------------------------------------------------------------------------------------------#


    def _processar_criptografia(self, url: str, chave_midia: str, mime_type: str, prompt_text: str | None, tipo: str, conteudo: str) -> List[Dict[str, Any]] | None: ...
        #fazer nova logica para o processo de descriptografia na vps
        

#--------------------------------------------------------------------------------------------------------------------#

