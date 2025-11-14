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
        try:  
            # 1. Verifica se é uma mensagem de texto simples
            texto_simples = data.get('conversation') or \
                data.get('extendedTextMessage', {}).get('text')
            if texto_simples:
                logger.info("Mensagem identificada como TEXTO.")
                return texto_simples

            # 2. Verifica se é uma mensagem de áudio
            elif data.get('audioMessage', {}):
                info_audio = data.get('audioMessage', {})
                logger.info("Mensagem identificada como ÁUDIO. Iniciando transcrição.")
                chave_midia = info_audio.get('mediaKey')
                mime_type = info_audio.get('mimetype')
                url_audio = info_audio.get('url')
                
                return await self.transcricao_audio(url_audio, chave_midia, mime_type)

            # 3. Se não for nenhum dos suportados, retorna None
            else:            
                logger.info("Mensagem não é texto ou mídia suportada (áudio, imagem, pdf).")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao verificar e processar o tipo de mensagem: {e}", exc_info=True)
            return None
        
#--------------------------------------------------------------------------------------------------------------------#
    
    # --- FUNÇÃO MODIFICADA ---
    async def treated_message(self, data: Dict[str, Any])-> dict:
        """
        Processa o payload completo da Evolution API, extrai os dados 
        relevantes e retorna um dicionário padronizado.
        """
        
        try:
            # 1. Pega o objeto 'data' principal do payload
            data_obj = data.get('data', {})
            if not data_obj:
                logger.warning("Payload ignorado: não contém o objeto 'data'.")
                return {"status": "ok", "message": "Payload inválido (sem 'data')."}
            
            # 2. Ignora mensagens enviadas PELO AGENTE ('fromMe' == True)
            key_obj = data_obj.get('key', {})
            if key_obj.get('fromMe', False):
                logger.info("Mensagem ignorada: 'fromMe' é verdadeiro.")
                return {"status": "ok", "message": "Mensagem de saída ignorada."}

            # 3. Pega o objeto 'message'
            message_data = data_obj.get('message', {})
            
            # Se 'message' estiver vazio, pode ser um evento de status (ex: DELIVERY_ACK)
            if not message_data:
                status = data_obj.get('status')
                if status:
                    logger.info(f"Mensagem ignorada: é um evento de status ({status}).")
                    return {"status": "ok", "message": f"Evento de status ({status}) ignorado."}
                
                logger.warning("Payload ignorado: objeto 'data' não contém 'message'.")
                return {"status": "ok", "message": "Payload inválido (sem 'message')."}

            # 4. Verifica o conteúdo da mensagem (texto ou áudio)
            input_text = await self.verified_message(message_data)

            if input_text is None:
                logger.info("Mensagem ignorada: não é um texto simples ou formato de mídia suportado.")
                return {"status": "ok", "message": "Não é uma mensagem de texto/mídia suportada."}

            # 5. Pega o número de telefone (remetente)
            numero_completo = key_obj.get('remoteJid', '')
            if not numero_completo:
                logger.error("Não foi possível extrair 'remoteJid' do payload.")
                return {"status": "ok", "message": "Não foi possível identificar o remetente."}
                
            numero = numero_completo.split('@')[0]

            logger.info(f"Mensagem recebida de: {numero}.")
            return {'Mensagem': input_text, 'Numero': numero}
            
        except Exception as e:
            logger.error(f"Erro crítico ao tratar a mensagem: {e}", exc_info=True)
            return {"status": "error", "message": f"Erro interno: {e}"}

#--------------------------------------------------------------------------------------------------------------------#

    async def transcricao_audio(self, url_audio: str, chave_midia: str, mime_type: str) -> str | None: 
        #fazer nova nlogica de transcrição de midia
        # Ex: bytes_audio = await self.decodificador.processar_criptografia(url_audio, ...)
        #     return await self.client.transcribe_audio(bytes_audio)
        logger.warning("transcricao_audio AINDA NÃO IMPLEMENTADO.")
        return "[Transcrição de Áudio Simulada]"

#--------------------------------------------------------------------------------------------------------------------#

    async def _processar_criptografia(self, url: str, chave_midia: str, mime_type: str, prompt_text: str | None, tipo: str, conteudo: str) -> List[Dict[str, Any]] | None: ...
        #fazer nova logica para o processo de descriptografia na vps