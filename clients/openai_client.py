import os
import logging
from interfaces.clients.ia_interface import IAI
from openai import AsyncOpenAI 
from openai.types.audio import Transcription
from openai.types.chat import ChatCompletion
from utils.logger import logger
from typing import List, Dict, Any, Optional

class OpenIAClient(IAI):

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY não definida no ambiente.")
            raise ValueError("OPENAI_API_KEY não foi configurada.")
            
        self.client = AsyncOpenAI(api_key=api_key) 
        self.max_output_tokens = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "2048")) 
        logger.info("AsyncOpenAIClient (OpenIAClient) inicializado.") 

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

    async def create_model_response(
        self, 
        model: str, 
        input_messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None, 
        instructions: Optional[str] = None 
        ) -> ChatCompletion: 

        try:
            kwargs = {
                "model": model,
                "messages": input_messages,
                "temperature": 0.5,
                "max_tokens": self.max_output_tokens,
                "top_p": 1,
            }
            
            if tools:
                kwargs["tools"] = tools
            
            response: ChatCompletion = await self.client.chat.completions.create(**kwargs) 
            
            logger.info("Resposta da OpenAI (ChatCompletion) recebida com sucesso.") 
            return response
            
        except Exception as e:
            logger.error(f"Erro ao chamar ChatCompletions: {e}", exc_info=True) 
            raise e