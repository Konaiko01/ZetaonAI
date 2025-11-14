from interfaces.clients.ia_interface import IAI
from openai.types.audio import Transcription
from openai.types.chat import ChatCompletion
from typing import Any, Optional
from openai import AsyncOpenAI 
from utils.logger import logger
import os

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

#--------------------------------------------------------------------------------------------------------------------#

    async def transcribe_audio(self, audio_file_path: str) -> str:
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription: Transcription = await self.client.audio.transcriptions.create( 
                    model="whisper-1", 
                    file=audio_file
                )
            logger.info("Áudio transcrito com sucesso.") 
            return transcription.text
        except Exception as e:
            logger.error(f"Erro ao transcrever áudio: {e}", exc_info=True) 
            return ""

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