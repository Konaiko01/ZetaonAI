#
# tests/funcions_test.py (CORRIGIDO)
#
import os
import sys
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Any
import pymongo # <-- Precisamos do pymongo para o 'hack' do DB

# Adiciona a pasta raiz do projeto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import configure_logging, logger
from clients.openai_client import OpenIAClient
from clients.calendar_client import GCalendarClient
from agents.agent_agendamento import AgentAgendamento

async def main_test_loop():
    
    load_dotenv()
    configure_logging() 
    
    logger.info("--- INICIANDO TESTE DO AGENT_AGENDAMENTO (Modo Produção) ---")

    ai_client = None
    calendar_client = None

    try:
        ai_client = OpenIAClient()
    except ValueError as e:
        logger.error(f"Falha ao carregar AI Client: {e}")
        return

    # --- LÓGICA DE INJEÇÃO CORRIGIDA ---
    try:
        # 1. Pega o ID da agenda do .env
        calendar_id = os.getenv("GCALENDAR_ID")
        if not calendar_id:
            raise ValueError("GCALENDAR_ID não encontrado no .env.")

        # 2. Pega as credenciais do Mongo (usando o 'hack' síncrono)
        MONGO_URI = os.getenv("mUri")
        sync_client = pymongo.MongoClient(MONGO_URI)
        creds_doc = sync_client["client_context"]["config"].find_one({"_id": "google_creds"})
        sync_client.close()

        if not creds_doc or not creds_doc.get("value"):
             raise FileNotFoundError("Credenciais 'google_creds' não encontradas no MongoDB.")
        
        service_account_info = creds_doc.get("value")

        # 3. Injeta AMBOS (info E ID) no cliente
        calendar_client = GCalendarClient(
            service_account_info=service_account_info,
            calendar_id=calendar_id
        )

    except Exception as e:
        logger.error(f"Falha ao carregar GCalendarClient: {e}")
        logger.error("Este script de teste não pode rodar sem o ICalendar.")
        return 
    # --- FIM DA CORREÇÃO ---

    agent = AgentAgendamento(ai_client=ai_client, calendar_client=calendar_client)

    # (O loop de chat permanece o mesmo)
    context: List[Dict[str, Any]] = []
    phone_number = "test_user_123" 

    print("\n--- Teste Interativo: AgentAgendamento ---")
    print(f"Modo Calendário: REAL (Conectado a {calendar_id})")
    print("Digite 'sair' para terminar.")
    print("="*40)

    while True:
        try:
            user_input = input("Você: ")
            if user_input.lower() == 'sair':
                break
            
            context.append({"role": "user", "content": user_input})
            print("\nAgente pensando...")
            
            updated_context = await agent.exec(context, phone_number)
            
            last_response = updated_context[-1]
            if last_response.get("role") == "assistant":
                if last_response.get("content"):
                    print(f"Agente: {last_response.get('content')}")
            else:
                 print(f"Agente (Debug): {last_response}") 
            context = updated_context
            print("-"*40)
        except Exception as e:
            logger.error(f"Erro fatal no loop de teste: {e}", exc_info=True)
            break

    logger.info("--- TESTE FINALIZADO ---")

# --- Ponto de Entrada ---
if __name__ == "__main__":
    # (Verificações de 'try/except ImportError' permanecem as mesmas)
    try:
        asyncio.run(main_test_loop())
    except KeyboardInterrupt:
        print("\nTeste interrompido pelo usuário.")