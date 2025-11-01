import json
import uvicorn
import logging
from config import ope
import asyncio
import sys
from services import sys_prompts
from services.agent_service import Agente
from fastapi import FastAPI, Request, HTTPException


logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

try:
    agente_ronaldo = Agente(ope.get_key())
except Exception as e:
    logger.error(f"Erro ao inicializar Agente (OpenAI): {e}")
    exit()

app = FastAPI()

app.post("v1/webhooks/change-in-business")
async def mudanca_de_posicao(request: Request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        logger.warning("Corpo da requisição inválido (JSON esperado).")
        raise HTTPException(status_code=400, detail="Corpo da requisição inválido.") 
    try:
        await asyncio.to_thread(
            self._connector.enviar_resposta,
        )
    except:
        pass

if __name__ == "__main__":
    logger.info("Iniciando o servidor Uvicorn...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)