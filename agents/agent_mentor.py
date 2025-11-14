#
# agents/agent_mentor.py (LIMPO)
#
from container.repositories import RepositoryContainer
from interfaces.clients.ia_interface import IAI
from container.clients import ClientContainer
from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletion
from agents.agent_base import BaseAgent
from utils.logger import logger

#--------------------------------------------------------------------------------------------------------------------#
class AgentMentor(BaseAgent): 
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, ai_client: IAI):
        self._ai_client = ai_client
        logger.info(f"Agente {self.id} inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def id(self) -> str:
        return "agent_mentor"

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def description(self) -> str:
        return "Especialista em responder perguntas gerais, dar conselhos, mentorias e conversas que não exigem ferramentas externas (No external access)."

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def model(self) -> str:
        return "gpt-4.1-mini" 

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def instructions(self) -> str:
        return """
        # Identidade: Agente Mentor
        - **Função**: Mentor e assistente de conversação geral.
        - **Expertise**: Responder perguntas gerais, dar conselhos, bater-papo.
        - **Restrições**: Você NÃO tem acesso a ferramentas externas (web, calendário, etc.).
        
        # Tarefa
        - Responda diretamente ao usuário de forma amigável e prestativa.
        - Se o usuário pedir algo que você não pode fazer (ex: "pesquise na web", "marque na minha agenda"), explique que você é o Agente Mentor e não tem acesso a essas ferramentas, mas que ele pode tentar perguntar de outra forma para acionar o agente correto.
        - Seja uma IA prestativa e conversacional.
        """

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def tools(self) -> Optional[List[Dict[str, Any]]]:
        return None

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
            final_content = self._extract_text_from_completion(response_completion)            
            logger.info(f"[{self.id}] Resposta gerada: {final_content[:50]}...")
            output_messages = messages + [{"role": "assistant", "content": final_content}]
            return output_messages

        except Exception as e:
            logger.error(f"[{self.id}] Erro ao executar: {e}", exc_info=True)
            return messages + [{"role": "assistant", "content": "Desculpe, encontrei um problema ao processar sua solicitação."}]
        
#--------------------------------------------------------------------------------------------------------------------#

    @classmethod
    def factory(
        cls,
        client_container: ClientContainer,
        repository_container: RepositoryContainer,
    ) -> "AgentMentor":
        ai_client = client_container.get_client("IAI") 
        if not ai_client:
            raise ValueError("Cliente IAI não encontrado no container.")
            
        return cls(ai_client=ai_client)