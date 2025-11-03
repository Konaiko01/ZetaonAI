import io
import os   
import whisper
import requests
import tempfile 
from openai import OpenAI
from ..utils import logger
from typing import List, Dict, Union, Any
from services.crypto.wpp_decoder import Decoder


#--------------------------------------------------------------------------------------------------------------------#
class MediaProcessor:
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self, key: str, temp_media_dir: str):
        self.client =  OpenAI(api_key=key) 
        self.decodificador = Decoder()
        self.modelo_whisper_local = whisper.load_model("base") 
        self.TEMP_MEDIA_DIR = temp_media_dir


#--------------------------------------------------------------------------------------------------------------------#


    def message_verification(self, data) -> str | None:     
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
    
    
    def message_processing(self, data)-> dict:

        message_data = data.get('message', {})
        input_text = MediaProcessor.message_verification(message_data)

        if input_text is None:
            logger.info("Mensagem ignorada: não é um texto simples ou formato de mídia suportado.")
            return {"status": "ok", "message": "Não é uma mensagem de texto/mídia suportada."}

        numero_completo = message_data.get('remoteJid', '')
        numero = numero_completo.split('@')[0]

        logger.info(f"Mensagem recebida. De: {numero}.")
        return {'Mensagem': input_text, 'Numero': numero}


#--------------------------------------------------------------------------------------------------------------------#
    def _baixar_midia(self, url_midia: str, extensao_arquivo: str) -> io.BytesIO | None:
        try:
            resposta = requests.get(url_midia, stream=True, timeout=15) 
            resposta.raise_for_status()
            buffer_midia = io.BytesIO(resposta.content)
            logger.info(f"Download da mídia concluído. Tipo: {extensao_arquivo}. Tamanho: {len(resposta.content)} bytes.")
            return buffer_midia
        except requests.exceptions.RequestException as e:
            logger.error(f"Falha ao baixar mídia da URL {url_midia}: {e}")
            return None
        

#--------------------------------------------------------------------------------------------------------------------#


    def transcricao_audio(self, url_audio: str, chave_midia: str, mime_type: str) -> str | None:
        extensao_download = "midia_bruta" 
        buffer_criptografado = self._baixar_midia(url_audio, extensao_download)
        if buffer_criptografado is None:
            return None
        
        temp_caminho_entrada = None
        try:
            logger.info("Iniciando descriptografia do áudio (AES/HKDF)...")
            buffer_decodificado = self.decodificador.decodificar_buffer(
                buffer_criptografado=buffer_criptografado,
                chave_midia_base64=chave_midia, 
                mime_type=mime_type
            )
            logger.info("Descriptografia do áudio concluída.")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp_ogg:
                buffer_decodificado.seek(0)
                ogg_content = buffer_decodificado.getvalue()
                
                logger.info(f"Salvando OGG decodificado para transcrição local: {len(ogg_content)} bytes.") 
                tmp_ogg.write(ogg_content)
                temp_caminho_entrada = tmp_ogg.name
                tmp_ogg.flush()
            logger.info("Iniciando transcrição local com modelo Whisper...")
            resultado = self.modelo_whisper_local.transcribe(
                temp_caminho_entrada,
                language="pt" 
            )
            transcricao = resultado["text"]
            logger.info("Transcrição local bem-sucedida (via Whisper local).")
            return transcricao
        except Exception as e:
            logger.error(f"Erro na transcrição com Whisper local: {e}", exc_info=True)
            return None    
        finally:
            if temp_caminho_entrada and os.path.exists(temp_caminho_entrada):
                os.remove(temp_caminho_entrada)


#--------------------------------------------------------------------------------------------------------------------#


    def _processar_criptografia(self, url: str, chave_midia: str, mime_type: str, prompt_text: str | None, tipo: str, conteudo: str) -> List[Dict[str, Any]] | None:
        extensao_download = "midia_bruta" 
        buffer_criptografado = self._baixar_midia(url, extensao_download)
        if buffer_criptografado is None:
            return None
        
        temp_caminho_midia = None

        try:
            logger.info("Iniciando descriptografia da mídia (AES/HKDF)...")
            buffer_decodificado = self.decodificador.decodificar_buffer(
                buffer_criptografado=buffer_criptografado,
                chave_midia_base64=chave_midia, 
                mime_type=mime_type
            )
            logger.info("Descriptografia concluída. Conteúdo decodificado em buffer.")
            buffer_decodificado.seek(0)
            extensao = self.decodificador._EXTENSAO.get(mime_type.split("/")[0], mime_type.split("/")[-1])
            if mime_type == 'application/pdf':
               extensao = 'pdf'
            elif 'image' in mime_type:
                if extensao == 'bin': 
                    extensao = 'jpg' 
            
            nome_arquivo = f"{os.urandom(16).hex()}.{extensao}"
            temp_caminho_midia = os.path.join(self.TEMP_MEDIA_DIR, nome_arquivo)
            
            logger.info(f"Salvando binário descriptografado diretamente como .{extensao}...")

            with open(temp_caminho_midia, 'wb') as f:
                f.write(buffer_decodificado.getvalue())
                 
            logger.info(f"Mídia salva localmente para ser enviada via path: {temp_caminho_midia}")

            payload_final = []
            if prompt_text:
                 payload_final.append({"type": "input_text", "text": prompt_text})
            payload_final.append({"type": "input_file", "file_path" : temp_caminho_midia})
            
            return payload_final

        except Exception as e:
            logger.error(f"Erro ao processar mídia criptografada para arquivo local: {e}", exc_info=True)
            # Limpeza em caso de erro
            if temp_caminho_midia and os.path.exists(temp_caminho_midia):
                os.remove(temp_caminho_midia)
            return None
        

#--------------------------------------------------------------------------------------------------------------------#

