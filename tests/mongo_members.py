import asyncio
import os
import motor.motor_asyncio
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

MONGO_URI = os.getenv("mUri")
DATABASE_NAME = "client_context"
COLLECTION_NAME = "group_members"

async def get_group_members_from_mongo():
    print(f"--- Script para Listar Membros do MongoDB ---")
    if not MONGO_URI:
        print("ERRO: 'mUri' (String de conexão do Mongo) não encontrada no .env.")
        return
    client = None

    try:
        print(f"Conectando ao MongoDB em {MONGO_URI}...")
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        print(f"Buscando grupos na coleção '{COLLECTION_NAME}'...")
        cursor = collection.find({})
        group_count = 0

        async for group_doc in cursor:
            group_count += 1
            group_name = group_doc.get("group_name", "Grupo Sem Nome")
            group_id = group_doc.get("group_id", "ID Desconhecido")
            members: list[Dict[str, Any]] = group_doc.get("members", [])   
            print("\n" + "="*50)
            print(f"Grupo: {group_name} ({group_id})")
            print(f"Total de Membros: {len(members)}")
            print("-"*50)            
            if not members:
                print("  (Nenhum membro listado para este grupo)")
            else:
                for i, member in enumerate(members):
                    member_id = member.get('id', 'ID Inválido')
                    is_admin = "Sim" if member.get('admin') else "Não"
                    print(f"  {i+1:02d}) ID: {member_id} | Admin: {is_admin}")
            print("="*50 + "\n")
        if group_count == 0:
            print(f"\nNenhum grupo encontrado na coleção '{COLLECTION_NAME}'.")
        else:
            print(f"Total de {group_count} grupos encontrados.")
    except Exception as e:
        print(f"\nERRO: Ocorreu um problema ao se conectar ou buscar no MongoDB.")
        print(f"Detalhe: {e}")
    finally:
        if client:
            client.close()
            print("Conexão com o MongoDB fechada.")

if __name__ == "__main__":
    try:
        import motor
        import dotenv
    except ImportError:
        print("Erro de dependência: 'motor' ou 'python-dotenv' não estão instalados.")
        print("Execute: pip install motor python-dotenv")
        exit(1)
        
    asyncio.run(get_group_members_from_mongo())