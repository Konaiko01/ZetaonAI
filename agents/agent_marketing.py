import logging
import json
from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from agents.agent_base import BaseAgent 

from interfaces.clients.ia_interface import IAI
from container.clients import ClientContainer
from container.repositories import RepositoryContainer
from utils.logger import logger

tools_definitions = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Busca informações na web (ex: tendências de mercado, concorrentes).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "A query de busca."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prospect_leads_b2b",
            "description": "Busca leads B2B em uma base de dados interna com base em critérios.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {"type": "string", "description": "Setor da empresa (ex: 'tecnologia', 'saude')."},
                    "role": {"type": "string", "description": "Cargo do decisor (ex: 'CTO', 'CEO')."},
                    "region": {"type": "string", "description": "Região (ex: 'São Paulo')."},
                },
                "required": ["sector"],
            },
        },
    },
]


class AgentMarketing(BaseAgent):

    def __init__(self, ai_client: IAI, websearch_client: Any, prospect_client: Any):
        self._ai_client = ai_client
        self._websearch_client = websearch_client
        self._prospect_client = prospect_client
        logger.info(f"Agente {self.id} inicializado.")

    @property
    def id(self) -> str:
        return "agent_marketing"
    
    @property
    def description(self) -> str:
        return "Especialista em marketing, vendas, growth, tráfego pago, prospecção e acesso a ferramentas externas (Full access)."

    @property
    def model(self) -> str:
        return "gpt-4.1-mini"

    @property
    def instructions(self) -> str:
        return """
        # Identidade: Agente de Marketing e Vendas (SDR/BDR/Growth)
        - **Função**: Especialista em estratégias de marketing, prospecção e vendas.
        - **Expertise**: Growth Hacking, Tráfego Pago (Ads), Prospecção B2B (SDR/BDR), Análise de Mercado.
        - **Acesso**: Full Access (Web, DBs internos).
        
        # Tarefa
        - Use `search_web` para analisar tendências de mercado, concorrentes e notícias.
        - Use `prospect_leads_b2b` para buscar contatos qualificados na base de dados interna.
        - Forneça conselhos estratégicos sobre vendas, anúncios e growth.
        - Ao prospectar, seja claro sobre os critérios e retorne uma lista (simulada) de leads.
        - Seja proativo, estratégico e focado em resultados de negócios.
        """

    @property
    def tools(self) -> Optional[List[Dict[str, Any]]]:
        return tools_definitions

    async def exec(self, context: List[Dict[str, Any]], phone: str) -> List[Dict[str, Any]]:
        logger.info(f"[{self.id}] Executando agente para {phone}.")
        
        messages = self._insert_system_input(context)
        
        try:

            response_completion: ChatCompletion = await self._ai_client.create_model_response(
                model=self.model,
                input_messages=messages,
                tools=self.tools,
                instructions=None
            )
            response_message = response_completion.choices[0].message
            messages.append(self._message_to_dict(response_message))

            while response_message.tool_calls:
                logger.info(f"[{self.id}] Acionando ferramentas: {[tc.function.name for tc in response_message.tool_calls]}")
                
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    tool_output = ""
                    try:
                        if function_name == "search_web":
                            tool_output = f"RESULTADOS_SIMULADOS_DA_WEB sobre '{function_args.get('query')}': O mercado de Ads está competitivo."
                            logger.info(f"[{self.id}] Ferramenta 'search_web' chamada.")

                        elif function_name == "prospect_leads_b2b":
                            tool_output = f"LEADS_SIMULADOS_ENCONTRADOS para {function_args}: [Lead 1 (Tech/CEO), Lead 2 (Tech/CTO)]"
                            logger.info(f"[{self.id}] Ferramenta 'prospect_leads_b2b' chamada.")
                        
                        else:
                            tool_output = f"Erro: Ferramenta '{function_name}' desconhecida."
                            logger.warning(f"[{self.id}] Tentativa de chamar ferramenta desconhecida: {function_name}")
                    
                    except Exception as tool_e:
                        logger.error(f"[{self.id}] Erro ao executar ferramenta '{function_name}': {tool_e}", exc_info=True)
                        tool_output = f"Erro ao executar a ferramenta {function_name}: {str(tool_e)}"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_output),
                        }
                    )

                logger.info(f"[{self.id}] Enviando resultados das ferramentas de volta para a IA.")
                response_completion: ChatCompletion = await self._ai_client.create_model_response(
                    model=self.model,
                    input_messages=messages,
                    tools=self.tools,
                    instructions=None
                )
                response_message = response_completion.choices[0].message
                messages.append(self._message_to_dict(response_message))

            final_content = response_message.content or "Estratégia definida."
            logger.info(f"[{self.id}] Resposta final gerada: {final_content[:50]}...")
            return messages

        except Exception as e:
            logger.error(f"[{self.id}] Erro ao executar: {e}", exc_info=True)
            return messages + [{"role": "assistant", "content": "Desculpe, o Agente de Marketing encontrou um problema."}]

    @classmethod
    def factory(
        cls,
        client_container: ClientContainer,
        repository_container: RepositoryContainer,
    ) -> "AgentMarketing":
        ai_client = client_container.get_client("IAI")
        if not ai_client:
            raise ValueError("Cliente IAI não encontrado no container.")
        
        websearch_client = client_container.get_client("IWebSearch") 
        if not websearch_client:
            logger.warning("Cliente IWebSearch não encontrado. O Agente de Marketing usará MOCKS.")
            pass
        
        prospect_client = client_container.get_client("IProspect") 
        if not prospect_client:
            logger.warning("Cliente IProspect não encontrado. O Agente de Marketing usará MOCKS.")
            pass

        return cls(ai_client=ai_client, websearch_client=websearch_client, prospect_client=prospect_client)