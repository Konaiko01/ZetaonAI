from services.response_orchestrator_service import ResponseOrchestratorService
from controllers.message_process_controller import MessageProcessController
from services.group_autorization_service import GroupAuthorizationService 
from services.message_send_service import MessageSendService
from clients.calendar_client import GCalendarClient
from services.media_processor_service import MediaProcessorService
from services.message_queue_service import MessageQueueService
from container.repositories import RepositoryContainer 
from utils.logger import configure_logging, logger
from container.clients import ClientContainer 
from container.agents import AgentContainer
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import uvicorn

#--------------------------------------------------------------------------------------------------------------------#

load_dotenv()
configure_logging()

#--------------------------------------------------------------------------------------------------------------------#
class AppContainer:
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self):
        logger.info("[Main]Iniciando injeção de dependência...")
        self.client_container = ClientContainer()
        db_client = self.client_container.get_client("MongoDBClient")
        if not db_client:
            raise RuntimeError("Falha ao inicializar o MongoDBClient.")
        try:
            calendar_id = os.getenv("GCALENDAR_ID")
            if not calendar_id:
                raise ValueError("GCALENDAR_ID não encontrado no .env.")
            logger.info("[Main] Buscando credenciais do Google Calendar no MongoDB...")
            creds_doc = db_client.find_one_sync("config", {"_id": "google_creds"})         
            if not creds_doc or not creds_doc.get("value"):
                 raise FileNotFoundError("Credenciais 'google_creds' não encontradas no MongoDB.")
            
            service_account_info = creds_doc.get("value")
            calendar_client = GCalendarClient(
                service_account_info=service_account_info,
                calendar_id=calendar_id
            )
            self.client_container.register_client("ICalendar", calendar_client)  
        except Exception as e:
            logger.error(f"[Main] Falha ao carregar GCalendarClient: {e}")
            logger.warning("[Main] O AgentAgendamento falhará ou usará MOCKS.")
        self.repo_container = RepositoryContainer(
            db_client=db_client,
            cache_client=self.client_container.get_client("RedisClient")
        )

        self.agent_container = AgentContainer(
            clients=self.client_container,
            repositories=self.repo_container
        )
        
        self.message_gen_service = MessageSendService(
            chat_client=self.client_container.get_client("IChat")
        )
        self.orchestrator = ResponseOrchestratorService(
            agent_container=self.agent_container,
            ai_client=self.client_container.get_client("IAI"),
            message_generation_service=self.message_gen_service
        )
        self.media_service = MediaProcessorService()

        self.queue_service = MessageQueueService(
            orchestrator=self.orchestrator,
            context_repository=self.repo_container.context,  
            fragment_repository=self.client_container.cache
        )
        
        self.auth_service = GroupAuthorizationService(
            mongodb_instance=self.client_container.database,
            group_client=self.client_container.chat
        )

        self.message_controller = MessageProcessController(
            message_service=self.queue_service,
            media_service=self.media_service,
            group_auth_service=self.auth_service
        )
        logger.info("Container da Aplicação inicializado com sucesso.")

#--------------------------------------------------------------------------------------------------------------------#

app = FastAPI()
container = AppContainer()

#--------------------------------------------------------------------------------------------------------------------#

@app.post("/messages-upsert")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"[Main]Erro ao decodificar JSON do webhook: {e}")
        return JSONResponse(content={"status": "error", "detail": "Invalid JSON body"}, status_code=400)
    if not data:
        return JSONResponse(content={"status": "error", "detail": "Nenhum JSON recebido."}, status_code=400)
    try:
        response_data, status_code = await container.message_controller.control(data)
        return JSONResponse(content=response_data, status_code=status_code)
    
    except Exception as e:
        logger.error(f"[Main] Erro não tratado ao processar webhook: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "detail": "Erro interno do servidor."}, status_code=500)

#--------------------------------------------------------------------------------------------------------------------#

@app.get("/")
async def root():
    return {"message": "Servidor FastAPI está online."}

#--------------------------------------------------------------------------------------------------------------------#

if __name__ == "__main__":
    logger.info("[Main]Iniciando servidor Uvicorn diretamente...")
    uvicorn.run(app, host="0.0.0.0", port=8000)