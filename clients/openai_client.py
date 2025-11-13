import os
import logging
from interfaces.clients.ia_interface import IAI
from openai import AsyncOpenAI # Importa o cliente Assíncrono
from openai.types.audio import Transcription
from openai.types.chat import ChatCompletion
from utils.logger import logger
from typing import List, Dict, Any, Optional

class OpenIAClient(IAI):

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.max_output_tokens = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "2048"))
        logger.info("AsyncOpenAIClient inicializado.")

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
        messages = input_messages.copy()
        
        if instructions:
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {"role": "system", "content": instructions})

        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                model=model,
                messages=messages, 
                tools=tools if tools else None, 
                temperature=0.5,
                max_tokens=self.max_output_tokens,
                top_p=1,
            )
            
            logger.info("Resposta da OpenAI (ChatCompletion) recebida com sucesso.")
            return response
            
        except Exception as e:
            logger.error(f"Erro ao chamar ChatCompletions: {e}", exc_info=True)
            raise e