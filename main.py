import json
import uvicorn
from utils.logger import logger
from fastapi import FastAPI, Request, HTTPException
import container

app = FastAPI()

app.post("/")
def message_recieved(request: Request):
    try:
        data = request.json()
        return container.controllers.process_incoming_message_controller.handle(data)
    except json.JSONDecodeError:
        logger.warning("Corpo da requisição inválido (JSON esperado).")
        raise HTTPException(status_code=400, detail="Corpo da requisição inválido.") 

if __name__ == "__main__":
    logger.info("Iniciando o servidor Uvicorn...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)