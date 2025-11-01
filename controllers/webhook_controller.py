from ..utils.logger import logger
from..services.media_processor import MediaProcessor
#--------------------------------------------------------------------------------------------------------------------#
class TratamentoMsg:
#--------------------------------------------------------------------------------------------------------------------#


    def __init__(self):
        self.EVO_URL = evo.get_url()
        self.EVO_INSTANCIA = evo.get_instancia()
        self.EVO_TOKEN = evo.get_token()
        self.Z_URL = z.get_url()
        self.Z_INSTANCIA = z.get_instancia()
        self.Z_TOKEN = z.get_token()
        self.S_Z_TOKEN = z.get_s_token()


#--------------------------------------------------------------------------------------------------------------------#


    async def ProcessIncomingMessage(self, data: dict) -> List[dict[str]]:
        
 
        #ajustar para que receba a mensagem e coloque ela na fila(queue)
        data_message = data.get('message', {})
        input_text = media_processor.verificar_tipo_e_processar(data_message)

        if input_text is None:
            logger.info("Mensagem ignorada: não é um texto simples ou formato de mídia suportado.")
            return {"status": "ok", "message": "Não é uma mensagem de texto/mídia suportada."}

        numero_completo = mapped_data.get('remoteJid', '')
        numero = numero_completo.split('@')[0]

        logger.info(f"Mensagem recebida. De: {numero}.")
        return {'Mensagem': input_text, 'Numero': numero}