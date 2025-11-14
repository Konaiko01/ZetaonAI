from interfaces.clients.ia_interface import IAI
from openai.types.audio import Transcription
from openai.types.chat import ChatCompletion
from typing import Any, Optional
from openai import AsyncOpenAI 
from utils.logger import logger
import os
import io
import asyncio  
import tempfile 
import whisper


#--------------------------------------------------------------------------------------------------------------------#
class OpenIAClient(IAI):
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY não definida no ambiente.")
            raise ValueError("OPENAI_API_KEY não foi configurada.")
            
        self.client = AsyncOpenAI(api_key=api_key) 
        self.max_output_tokens = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "2048")) 
        logger.info("AsyncOpenAIClient (OpenIAClient) inicializado.") 

        self.whisper_model = None
        if whisper:
            try:
                self.whisper_model = whisper.load_model("base")
                logger.info("Modelo Whisper (local) 'base' carregado com sucesso.")
            except Exception as e:
                logger.error(f"Falha ao carregar o modelo Whisper local: {e}")
                logger.error("Verifique se o FFMPEG está instalado e no PATH do sistema.")
        else:
            logger.error("Transcrição de áudio está DESABILITADA (whisper não importado).")

#--------------------------------------------------------------------------------------------------------------------#

    async def transcribe_audio(self, audio_buffer: io.BytesIO) -> str:

        if not self.whisper_model:
            logger.error("Transcrição falhou: Modelo Whisper local não está carregado.")
            return "[ERRO: Modelo Whisper não carregado]"

        temp_file_path = ""
        try:
            ext = os.path.splitext(audio_buffer.name)[-1] or ".ogg"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(audio_buffer.getvalue())
                temp_file_path = tmp_file.name

            logger.info(f"Áudio salvo em arquivo temporário: {temp_file_path}")


            def _run_transcription_sync():
                result = self.whisper_model.transcribe(temp_file_path, fp16=False)
                return result["text"]
            transcription = await asyncio.to_thread(_run_transcription_sync)
            
            logger.info("Áudio (local) transcrito com sucesso.")
            return transcription

        except Exception as e:
            logger.error(f"Erro ao transcrever áudio (local): {e}", exc_info=True)
            if "ffmpeg" in str(e).lower():
                logger.critical("ERRO: 'ffmpeg' não encontrado. "
                                "O Whisper precisa do ffmpeg instalado no PATH do sistema.")
            return ""
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.debug(f"Arquivo temporário {temp_file_path} removido.")

#--------------------------------------------------------------------------------------------------------------------#

    async def create_model_response(
        self, 
        model: str, 
        input_messages: list[dict[str, Any]], 
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
        ) -> ChatCompletion: 
        try:
            api_kwargs = {
                "model": model,
                "messages": input_messages,
                "temperature": 0.5,
                "max_tokens": self.max_output_tokens,
                "top_p": 1,
            }
            if tools:
                api_kwargs["tools"] = tools
            if kwargs:
                api_kwargs.update(kwargs)
            
            response: ChatCompletion = await self.client.chat.completions.create(**api_kwargs) 
            logger.info("Resposta da OpenAI (ChatCompletion) recebida com sucesso.") 
            return response
            
        except Exception as e:
            logger.error(f"Erro ao chamar ChatCompletions: {e}", exc_info=True) 
            raise e