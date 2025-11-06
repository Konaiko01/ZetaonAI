from interfaces.clients.ia_interface import IAI
from openai import OpenAI
from openai.types.audio import Transcription
from utils.logger import logger

class OpenIAClient(IAI):

    def __init__(self):
        self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.max_output_tokens = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "998"))

    def transcribe_audio(self, audio_bytes): ...
    '''Verificar como fazer transcrição, biblioteca já está nos imports'''

    #usando responses ao invès de completions
    def create_response(self, model, input, tools = ..., instructions = None):
        response = self.client.responses.create(
            model=model,
            instructions=instructions,
            input=input,
            temperature=0.5,
            max_output_tokens=2048,      
            top_p=1,
            tools = tools,
          )
        resposta_agente = response.choices[0].message.content
        logger.info("Resposta da OpenAI recebida com sucesso.")
        return resposta_agente