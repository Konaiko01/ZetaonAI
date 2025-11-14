from utils.logger import configure_logging, logger
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn
from flask import jsonify
from dotenv import load_dotenv
from container.clients import ClientContainer 
from container.repositories import RepositoryContainer 
from container.agents import AgentContainer 
from services.group_autorization_service import GroupAuthorizationService
from services.media_processor_service import MediaProcessorService
from services.message_queue_service import MessageQueueService
from services.response_orchestrator_service import ResponseOrchestratorService
from services.message_generation_service import MessageGenerationService
from controllers.message_process_controller import MessageProcessController 

load_dotenv()
configure_logging()
class AppContainer:

    def __init__(self):
        logger.info("Iniciando injeção de dependência...")

        self.client_container = ClientContainer()

        self.repo_container = RepositoryContainer(
            db_client=self.client_container.get_client("MongoDBClient"),
            cache_client=self.client_container.get_client("RedisClient")
        )

        self.agent_container = AgentContainer(
            clients=self.client_container,
            repositories=self.repo_container
        )
        
        self.message_gen_service = MessageGenerationService(
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


app = FastAPI()
container = AppContainer()

# --- 5. Rota do Webhook (Estilo FastAPI) ---
@app.post("/messages-upsert")
async def handle_webhook(request: Request):
    """
    Endpoint POST que recebe a mensagem de input e a adiciona à fila.
    """
    try:

        data = await request.json()
        logger.info(data)
    except Exception as e:
        logger.error(f"Erro ao decodificar JSON do webhook: {e}")
        return JSONResponse(content={"status": "error", "detail": "Invalid JSON body"}, status_code=400)

    if not data:
        return JSONResponse(content={"status": "error", "detail": "Nenhum JSON recebido."}, status_code=400)

    try:
        response_data, status_code = await container.message_controller.control(data)
        return JSONResponse(content=response_data, status_code=status_code)
    
    except Exception as e:
        logger.error(f"[Rota FastAPI] Erro não tratado ao processar webhook: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "detail": "Erro interno do servidor."}, status_code=500)

@app.get("/")
async def root():
    return {"message": "Servidor FastAPI está online."}

# --- 6. Execução (se rodar 'python main.py') ---
if __name__ == "__main__":
    logger.info("Iniciando servidor Uvicorn diretamente...")
    uvicorn.run(app, host="0.0.0.0", port=8000)