import asyncio
import os
import json
from datetime import datetime
import motor.motor_asyncio
from dotenv import load_dotenv

# --- Definições ---
# Carrega as variáveis do .env
load_dotenv()

MONGO_URI = os.getenv("mUri")
DATABASE_NAME = "client_context" # O banco de dados do seu projeto
COLLECTION_NAME = "config"       # Coleção para salvar configurações
DOCUMENT_ID = "google_creds"   # O ID que o main.py irá buscar
JSON_FILE_PATH = "google-service-account.json" 

async def save_creds_to_mongo():
    """
    Lê o arquivo JSON das credenciais e o salva no MongoDB.
    """
    print("--- Script para Salvar Credenciais do Google no MongoDB ---")
    
    # 1. Validar URI do Mongo
    if not MONGO_URI:
        print(f"ERRO: 'mUri' (String de conexão do Mongo) não encontrada no .env.")
        print("Abortando.")
        return

    # 2. Ler o arquivo JSON local
    creds_dict = None
    if not os.path.exists(JSON_FILE_PATH):
        print(f"ERRO: Arquivo '{JSON_FILE_PATH}' não encontrado na raiz do projeto.")
        print("Por favor, baixe o JSON do Google Cloud, coloque-o na pasta D:\\ZetaonAI")
        print("e renomeie-o para 'google-service-account.json'.")
        print("Abortando.")
        return
    
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            creds_dict = json.load(f)
        print(f"Arquivo '{JSON_FILE_PATH}' lido com sucesso.")
    except Exception as e:
        print(f"ERRO: O arquivo '{JSON_FILE_PATH}' não é um JSON válido: {e}")
        print("Abortando.")
        return

    # 3. Conectar e Salvar no MongoDB
    client = None
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        print(f"Conectado ao MongoDB. Salvando em '{DATABASE_NAME}.{COLLECTION_NAME}'...")

        # O filtro para encontrar o documento
        filter = {"_id": DOCUMENT_ID}
        
        # O documento que queremos salvar (o JSON fica no campo 'value')
        update_data = {
            "$set": {
                "value": creds_dict,
                "description": "Credenciais da Conta de Serviço do Google Calendar",
                "updated_at": datetime.utcnow()
            }
        }
        
        # 'upsert=True' cria o documento se ele não existir, 
        # ou o atualiza se ele já existir.
        result = await collection.update_one(filter, update_data, upsert=True)
        
        if result.upserted_id:
            print("\nSUCESSO: Documento de credenciais criado no MongoDB.")
        elif result.modified_count > 0:
            print("\nSUCESSO: Documento de credenciais atualizado no MongoDB.")
        else:
            print("\nAVISO: O documento de credenciais já estava atualizado no MongoDB.")

    except Exception as e:
        print(f"\nERRO: Falha ao conectar ou salvar no MongoDB: {e}")
    finally:
        if client:
            client.close()
        print("Conexão fechada.")

# --- Ponto de Entrada ---
if __name__ == "__main__":
    # Verifica se as dependências estão instaladas
    try:
        import motor
        import dotenv
    except ImportError:
        print("Erro de dependência: 'motor' ou 'python-dotenv' não estão instalados.")
        print("Execute: pip install motor python-dotenv")
        exit(1)
        
    asyncio.run(save_creds_to_mongo())