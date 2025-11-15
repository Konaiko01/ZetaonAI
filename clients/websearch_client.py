import os
import httpx
from typing import List, Dict, Any
from utils.logger import logger
from interfaces.clients.websearch_interface import IWebSearch

class WebSearchClient(IWebSearch):
    
    _SEARCH_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            logger.error("[WebSearchClient] Variável de ambiente 'SERPER_API_KEY' não definida.")
            raise ValueError("Chave da API Serper não configurada.")
            
        self.http_client = httpx.AsyncClient(
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            },
            timeout=10.0
        )
        logger.info("[WebSearchClient] Cliente (Serper.dev) inicializado.")

    async def search(self, query: str) -> str:
        """
        Executa uma busca na web e retorna uma string formatada 
        com os resultados.
        """
        logger.info(f"[WebSearchClient] Buscando por: '{query}'")
        payload = {"q": query}
        
        try:
            response = await self.http_client.post(self._SEARCH_URL, json=payload)
            response.raise_for_status() # Lança erro se a API falhar
            
            results = response.json()
            
            # Formata os resultados em uma string limpa para a IA
            return self._format_results(results)

        except httpx.RequestError as e:
            logger.error(f"[WebSearchClient] Erro na requisição para Serper API: {e}")
            return f"Erro ao conectar ao serviço de busca: {e}"
        except Exception as e:
            logger.error(f"[WebSearchClient] Erro ao processar resultados da busca: {e}", exc_info=True)
            return f"Erro interno ao processar a busca: {e}"

    def _format_results(self, results: Dict[str, Any]) -> str:
        """Pega o JSON do Serper e formata os 3 melhores resultados."""
        
        if not results or "organic" not in results:
            return "Nenhum resultado encontrado."

        organic_results = results.get("organic", [])
        if not organic_results:
            return "Nenhum resultado orgânico encontrado."
            
        snippets = []
        # Pega os 3 primeiros resultados
        for item in organic_results[:3]:
            title = item.get("title", "Sem título")
            snippet = item.get("snippet", "Sem descrição")
            link = item.get("link", "#")
            snippets.append(f"Fonte: {link}\nTítulo: {title}\nResumo: {snippet}")
            
        return "\n\n---\n\n".join(snippets)