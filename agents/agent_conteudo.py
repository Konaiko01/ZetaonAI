from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletion
from agents.agent_base import BaseAgent
from interfaces.clients.ia_interface import IAI
from container.clients import ClientContainer
from container.repositories import RepositoryContainer
from utils.logger import logger
import json
#from interfaces.clients.websearch_interface import IWebSearch
#--------------------------------------------------------------------------------------------------------------------#
class AgentConteudo(BaseAgent):
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, ai_client: IAI, websearch_client: Any): 
        self._ai_client = ai_client 
        self._websearch_client = websearch_client 
        logger.info(f"Agente {self.id} inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def id(self) -> str:
        return "agent_conteudo"
    
#--------------------------------------------------------------------------------------------------------------------#

    @property
    def description(self) -> str:
        return "Especialista em criação de conteúdo, pesquisa, redação e acesso a ferramentas de busca (Web access)."

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def model(self) -> str:
        return "gpt-4.1-mini"

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def instructions(self) -> str:
        return """
        # Identidade: Scout, o Pesquisador Rápido
        - **Função**: Especialista em pesquisa, conteúdo e insights.
        - **Personalidade**: Inteligente, rápido, animado e muito entusiasmado. Você ama encontrar informações!
        - **Estilo de Fala**: Você usa poucas palavras, mas com energia. Vá direto ao ponto, de forma clara e positiva. (Ex: "Entendido!", "Aqui está!", "Buscando agora!").

        # Contexto Atual
        - A data e hora atuais são: {CURRENT_DATETIME}
        
        # Tarefa Principal
        - Sua tarefa é responder perguntas do usuário que exigem conhecimento externo ou criação de conteúdo.
        - **Regra de Ouro**: Você DEVE usar a ferramenta `search_web` PRIMEIRO para QUALQUER pergunta sobre fatos, notícias, pessoas, ou para escrever sobre qualquer tópico (ex: "quem ganhou o jogo?", "escreva um post sobre IA"). Você não deve confiar no seu conhecimento pré-treinado para fatos.
        - Após usar `search_web`, sintetize os resultados em uma resposta curta, precisa e entusiasmada.

        # Regras de Segurança (Guardrails)
        - **PROIBIDO**: Você NUNCA deve gerar, discutir ou pesquisar conteúdo que seja:
            - Sexual, pornográfico ou +18.
            - Violento, gráfico ou que promova ódio.
            - Relacionado a atividades ilegais (drogas, armas, etc.).
            - Desinformação ou teorias da conspiração.
        - **Ação de Recusa**: Se o usuário pedir algo que viole essas regras, recuse educadamente e de forma neutra (ex: "Desculpe, não posso ajudar com esse tópico.").
        """
    
#--------------------------------------------------------------------------------------------------------------------#

    @property
    def tools(self) -> Optional[List[Dict[str, Any]]]:
        return tools_definitions
    
#--------------------------------------------------------------------------------------------------------------------#


    async def exec(self, context: List[Dict[str, Any]], phone: str) -> List[Dict[str, Any]]:
        logger.info(f"[{self.id}] Executando agente para {phone}.")
        messages = self._insert_system_input(context)
        try:
            response_completion: ChatCompletion = await self._ai_client.create_model_response(
                model=self.model,
                input_messages=messages,
                tools=self.tools,
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
                            # --- LÓGICA MOCK REMOVIDA ---
                            query = function_args.get("query")
                            tool_output = await self._websearch_client.search(query) # <- Chamada real
                            logger.info(f"[{self.id}] Ferramenta 'search_web' chamada com query: {query}")
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

                logger.info(f"[{self.id}] Enviando resultados da web de volta para a IA.")
                
                # --- CORREÇÃO: Removido 'instructions=None' ---
                response_completion: ChatCompletion = await self._ai_client.create_model_response(
                    model=self.model,
                    input_messages=messages,
                    tools=self.tools,
                )
                response_message = response_completion.choices[0].message
                messages.append(self._message_to_dict(response_message))

            final_content = response_message.content or "Conteúdo processado."
            logger.info(f"[{self.id}] Resposta final gerada: {final_content[:50]}...")
            return messages

        except Exception as e:
            logger.error(f"[{self.id}] Erro ao executar: {e}", exc_info=True)
            return messages + [{"role": "assistant", "content": "Desculpe, o Agente de Conteúdo encontrou um problema."}]

#--------------------------------------------------------------------------------------------------------------------#

    @classmethod
    def factory(
        cls,
        client_container: ClientContainer,
        repository_container: RepositoryContainer,
    ) -> "AgentConteudo":
        ai_client = client_container.get_client("IAI")
        if not ai_client:
            raise ValueError("Cliente IAI não encontrado no container.")
        
        # --- Injeção agora é OBRIGATÓRIA ---
        websearch_client = client_container.get_client("IWebSearch") 
        if not websearch_client:
            raise ValueError("[AgentConteudo] Cliente IWebSearch não encontrado no container.")

        return cls(ai_client=ai_client, websearch_client=websearch_client)

#--------------------------------------------------------------------------------------------------------------------#

tools_definitions = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Busca informações na web usando um motor de busca.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A query de busca (ex: 'preço do bitcoin hoje').",
                    },
                },
                "required": ["query"],
            },
        },
    }
]