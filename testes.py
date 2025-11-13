'''import asyncio
import logging
import os
from dotenv import load_dotenv
from typing import Dict, Any, List

# --- Importações do Sistema Real ---
from container.clients import ClientContainer
from container.repositories import RepositoryContainer
from container.agents import AgentContainer
from services.response_orchestrator_service import ResponseOrchestratorService
from services.message_generation_service import MessageGenerationService

# --- Importações das Interfaces e Mocks ---
from interfaces.clients.chat_interface import IChat

# --- Configuração de LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constantes do Teste ---
TEST_PHONE_NUMBER = "5511999991234" # Número de telefone para o teste
MESSAGE_WINDOW_SECONDS = 8.0 # Janela para agrupar mensagens (conforme sua regra)

logger.info("--- 7.5: VERIFICANDO DADOS SALVOS NO MONGODB ---")
        
        # O db_client é o mongo_client
        # Vamos usar o repo_container para saber o nome da coleção
collection_name = repo_container.context._COLLECTION_NAME
        
data_from_db = await db_client.find_one(
collection_name, 
{"phone": TEST_PHONE_NUMBER}
)
        
if data_from_db:
            logger.info("Dados encontrados no MongoDB:")
            # Imprimir no console formatado
            print("\n" + "="*30)
            print(f"  DADOS DO MONGO DB (para {TEST_PHONE_NUMBER}):")
            print("="*30)
            # O `json.dumps` é usado para formatar o dict de forma legível
            # `default=str` é para o caso de ter um `_id` do tipo ObjectId
            print(json.dumps(data_from_db, indent=2, default=str))
            print("="*30 + "\n")
else:
            logger.error("--- VERIFICAÇÃO FALHOU: Nenhum dado encontrado no MongoDB. ---")

        # --- FIM DO NOVO BLOCO DE VERIFICAÇÃO ---

# --- ÚNICO MOCK: O Cliente de Chat ---
# Simula a camada de "envio" (ex: EvolutionAPI) imprimindo no terminal.
# Isso satisfaz o requisito "exceto pelo de envio e recepção".

class MockChatClientPrinter(IChat):
    """
    Mock que implementa a interface IChat.
    Em vez de ENVIAR a mensagem, ele a IMPRIME no console.
    """
    async def send_message(self, phone: str, message: str):
        """Imprime a mensagem final no terminal em vez de enviar."""
        logger.info(f"[MockChatClientPrinter] Simulando envio para {phone}...")
        print("\n" + "="*30)
        print(f"  RESPOSTA FINAL GERADA NO TERMINAL (para {phone}):")
        print("="*30)
        print(message)
        print("="*30 + "\n")
        return True
    
    # Métodos não usados
    def get_chat_id(self) -> str: return ""
    def get_phone_number(self) -> str: return ""
    def get_message(self) -> str: return ""
    def is_valid(self) -> bool: return True

# --- SCRIPT DE TESTE FUNCIONAL ---

async def run_functional_test():
    logger.info("--- Iniciando Teste FUNCIONAL COMPLETO ---")
    
    # 1. Carregar .env
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("ERRO: OPENAI_API_KEY não encontrada. Teste abortado.")
        return
    if not os.getenv("mUri"):
        logger.error("ERRO: mUri (Mongo) não encontrada. Teste abortado.")
        return
    if not os.getenv("rHost"):
        logger.error("ERRO: rHost (Redis) não encontrada. Teste abortado.")
        return

    # 2. Inicializar o Sistema Completo
    client_container = None
    try:
        # --- Containers de Injeção ---
        client_container = ClientContainer()
        
        # Pega os clientes de dados para o RepositoryContainer
        db_client = client_container.get_client("MongoDBClient")
        cache_client = client_container.get_client("RedisClient")
        
        repo_container = RepositoryContainer(
            db_client=db_client,
            cache_client=cache_client
        )
        
        agent_container = AgentContainer(
            clients=client_container,
            repositories=repo_container
        )
        
        # --- Serviços ---
        # Injeta o MOCK de chat (Printer) no MessageGenerationService
        mock_chat_printer = MockChatClientPrinter()
        msg_gen_service = MessageGenerationService(chat_client=mock_chat_printer)
        
        orchestrator = ResponseOrchestratorService(
            agent_container=agent_container,
            ai_client = client_container.get_client("IAI"),
            message_generation_service = msg_gen_service
        )
        
        logger.info("--- Sistema Real inicializado com sucesso (Chat Mockado). ---")
        
        # --- 3. Limpeza de Dados de Teste Anteriores ---
        logger.info(f"Limpando dados de teste antigos para o fone: {TEST_PHONE_NUMBER}")
        fragment_key = f"fragments:{TEST_PHONE_NUMBER}"
        await repo_container.fragments.delete_queue(fragment_key) #
        await db_client.database[repo_container.context._COLLECTION_NAME].delete_many({"phone": TEST_PHONE_NUMBER})
        logger.info("Dados anteriores limpos (Redis e Mongo).")

        # --- 4. TESTE 1: Mensagens Fragmentadas e Salvar Contexto ---
        logger.info("--- TESTE 1: Mensagens Fragmentadas (Redis) e Salvar Contexto (Mongo) ---")
        
        logger.info("Simulando recebimento de mensagens fragmentadas...")
        await repo_container.fragments.add_fragment(fragment_key, "Me fale")
        await asyncio.sleep(2) # Simula usuário digitando
        await repo_container.fragments.add_fragment(fragment_key, "sobre o futuro da IA")
        await asyncio.sleep(3) # Simula usuário digitando
        await repo_container.fragments.add_fragment(fragment_key, "no Brasil.")
        
        logger.info(f"3 fragmentos enviados. Aguardando {MESSAGE_WINDOW_SECONDS}s para a janela de mensagens fechar...")
        await asyncio.sleep(MESSAGE_WINDOW_SECONDS)
        
        logger.info("Janela fechada. Processando pacote...")
        fragments = await repo_container.fragments.get_and_clear_fragments(fragment_key)
        
        if not fragments:
            raise Exception("Falha no teste! O Repositório de Fragmentos não retornou nada.")
            
        full_message = " ".join(fragments)
        logger.info(f"Mensagem completa montada: '{full_message}'")
        
        # --- 5. Execução do Orquestrador (Teste 1) ---
        logger.info("Buscando contexto do MongoDB (deve estar vazio)...")
        context_data = await repo_container.context.get_context(TEST_PHONE_NUMBER)
        history = context_data.get("history", []) if context_data else []
        
        history.append({"role": "user", "content": full_message})

        logger.info("Executando Orquestrador (com chamada real à OpenAI)...")
        output_history = await orchestrator.execute(history, TEST_PHONE_NUMBER)
        
        # --- 6. Salvar Contexto (Teste 1) ---
        logger.info("Salvando novo contexto no MongoDB...")
        await repo_container.context.save_context(TEST_PHONE_NUMBER, {"history": output_history})
        logger.info("--- TESTE 1 Concluído (Resposta deve ter aparecido no console) ---")

        # --- 7. TESTE 2: Ler Contexto Salvo ---
        logger.info("--- TESTE 2: Ler Contexto Salvo (Mongo) ---")
        await asyncio.sleep(2) # Pequena pausa
        
        logger.info("Buscando contexto do MongoDB (deve existir)...")
        context_data_test2 = await repo_container.context.get_context(TEST_PHONE_NUMBER)
        
        if not context_data_test2:
            raise Exception("Falha no Teste 1! Contexto não foi salvo no MongoDB.")
            
        history_test2 = context_data_test2.get("history", [])
        logger.info(f"Contexto com {len(history_test2)} mensagens encontrado.")
        
        new_message = "Baseado no que eu disse, qual agente você acha que seria melhor para falar sobre agendamentos?"
        history_test2.append({"role": "user", "content": new_message})
        
        logger.info(f"Enviando nova mensagem: '{new_message}'")
        logger.info("Executando Orquestrador com contexto...")
        
        final_history = await orchestrator.execute(history_test2, TEST_PHONE_NUMBER)
        
        # Salva o contexto final
        await repo_container.context.save_context(TEST_PHONE_NUMBER, {"history": final_history})
        logger.info("Contexto final (com 2 interações) salvo.")
        logger.info("--- TESTE 2 Concluído ---")

    except Exception as e:
        logger.error(f"--- Teste Funcional Falhou: {e} ---", exc_info=True)
    
    finally:
        # --- 8. Fechar Conexões ---
        if client_container:
            logger.info("Fechando conexões (OpenAI, Redis, Mongo)...")
            await client_container.ai.client.close()
            await client_container.cache.close()
            client_container.database.app.close() # O 'motor' usa 'close' síncrono
            logger.info("Conexões fechadas.")
        
        logger.info("--- Teste Funcional COMPLETO Finalizado ---")


if __name__ == "__main__":
    # Garante que todos os 'await' sejam executados
    asyncio.run(run_functional_test())'''

import asyncio
import logging
import json
import os
from dotenv import load_dotenv

# Importa o cliente real do MongoDB
from clients.mongo_client import MongoDBClient
# Importa a interface apenas para type hinting (opcional, mas bom)
from interfaces.clients.db_interface import IDB

# --- Configuração de LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURE AQUI O QUE VOCÊ QUER VER ---

# A coleção que você quer inspecionar (provavelmente "user_contexts")
COLLECTION_TO_CHECK = "user_contexts"

# O filtro que você quer aplicar
# Para ver um telefone específico (o do seu teste):
FILTER_TO_APPLY = {"phone": "5511999991234"}

# Para ver TUDO na coleção (cuidado se for grande):
# FILTER_TO_APPLY = {} 

# --- FIM DA CONFIGURAÇÃO ---


async def get_db_state(db_client: IDB, collection: str, filter: dict):
    """
    Função isolada para buscar e imprimir dados do MongoDB.
    """
    logger.info(f"Buscando na coleção: '{collection}' com o filtro: {filter}")
    
    # O MongoDBClient (motor) não tem um método "find_many" genérico,
    # então acessamos o objeto 'database' dele
    # e usamos o 'find' do motor diretamente.
    try:
        motor_collection = db_client.database[collection]
        
        cursor = motor_collection.find(filter)
        results = await cursor.to_list(length=100) # Limita a 100 resultados

        if not results:
            logger.warning("--- NENHUM DOCUMENTO ENCONTRADO ---")
            return

        logger.info(f"--- {len(results)} DOCUMENTO(S) ENCONTRADO(S) ---")
        
        # Imprime no console formatado
        print("\n" + "="*30)
        print(f"  ESTADO ATUAL DO DB (Coleção: {collection})")
        print("="*30)
        # default=str lida com 'ObjectId' e 'datetime'
        print(json.dumps(results, indent=2, default=str))
        print("="*30 + "\n")

    except Exception as e:
        logger.error(f"Erro ao buscar no MongoDB: {e}", exc_info=True)


async def main():
    logger.info("--- Iniciando Verificador de DB Isolado ---")
    load_dotenv()
    
    if not os.getenv("mUri"):
        logger.error("ERRO: mUri (Mongo) não encontrada no .env. Abortando.")
        return

    db_client = None
    try:
        # 1. Inicializa o cliente real do MongoDB
        db_client = MongoDBClient()
        
        # 2. Roda a função de verificação
        await get_db_state(db_client, COLLECTION_TO_CHECK, FILTER_TO_APPLY)

    except Exception as e:
        logger.error(f"--- Falha na execução: {e} ---", exc_info=True)
    
    finally:
        # 3. Fecha a conexão
        if db_client:
            db_client.app.close() # O 'motor' usa 'close' síncrono
            logger.info("Conexão com MongoDB fechada.")


if __name__ == "__main__":
    asyncio.run(main())