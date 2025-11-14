import redis.asyncio as redis
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("rHost")
REDIS_PORT = os.getenv("rPort")
REDIS_PASS = os.getenv("rPass")

async def flush_all_redis_data():
    print("--- SCRIPT PARA LIMPAR O REDIS ---")
    print(f"Conectando a: {REDIS_HOST}:{REDIS_PORT}")
    print("\n" + "="*60)
    print("  ATENÇÃO: Este script irá deletar TODAS as chaves")
    print(f"  do banco de dados Redis em {REDIS_HOST}.")
    print("  Isto inclui todas as filas de fragmentos, contextos, etc.")
    print("  Esta ação NÃO PODE ser desfeita.")
    print("="*60 + "\n")
    confirmacao = input("Para confirmar, digite 'SIM' em maiúsculas: ")
    if confirmacao != "SIM":
        print("Ação cancelada pelo usuário.")
        return
    redis_conn = None
    try:
        redis_conn = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASS
        )
        await redis_conn.ping()
        print("Conectado ao Redis com sucesso.")
        await redis_conn.flushdb()
        
        print("\n-------------------------------------------")
        print(" SUCESSO! O banco de dados Redis foi limpo.")
        print("-------------------------------------------\n")

    except Exception as e:
        print(f"\nERRO: Não foi possível conectar ou limpar o Redis.")
        print(f"Detalhe: {e}")
        
    finally:
        if redis_conn:
            await redis_conn.aclose()
            print("Conexão com o Redis fechada.")

if __name__ == "__main__":
    asyncio.run(flush_all_redis_data())