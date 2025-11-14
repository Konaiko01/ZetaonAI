#
# agents/base_agent.py (NOVO ARQUIVO)
#
import logging
from abc import abstractmethod
from typing import List, Dict, Any
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from interfaces.agent.agent_interface import IAgent

logger = logging.getLogger(__name__)

class BaseAgent(IAgent):
    """
    Classe base abstrata para todos os Agentes Especialistas.
    Implementa a lógica comum de processamento de contexto e extração de resposta.
    """

    @property
    @abstractmethod
    def id(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def instructions(self) -> str: ...

    @property
    @abstractmethod
    def tools(self) -> list: ...

    @abstractmethod
    async def exec(self, context: List[Dict[str, Any]], phone: str) -> List[Dict[str, Any]]: ...

    # --- Funções Auxiliares Comuns ---

    def _insert_system_input(self, input_list: list) -> list:
        """
        Remove qualquer prompt de sistema antigo e insere o 
        prompt de sistema (instructions) deste agente no início da lista.
        """
        # Filtra todos os 'system' prompts anteriores
        filtered_list = [msg for msg in input_list if msg.get("role") != "system"]
        
        # Adiciona o prompt de sistema específico deste agente
        system_prompt = {"role": "system", "content": self.instructions}
        filtered_list.insert(0, system_prompt)
        return filtered_list

    def _extract_text_from_completion(self, response: ChatCompletion) -> str:
        """
        Extrai a mensagem de texto de uma resposta de ChatCompletion.
        Usado por agentes que não usam ferramentas (como o Mentor).
        """
        try:
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except (AttributeError, IndexError, TypeError):
            logger.warning(f"[{self.id}] Não foi possível extrair conteúdo de texto da resposta da IA.")
            return ""

    def _message_to_dict(self, message: ChatCompletionMessage) -> Dict[str, Any]:
        """
        Converte um objeto ChatCompletionMessage (que pode ter tool_calls) 
        em um dicionário padrão para o histórico.
        """
        msg_dict = {"role": "assistant", "content": message.content or ""}
        
        if message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        
        # Limpa o "content" se for None ou vazio, o que acontece durante tool_calls
        if not msg_dict["content"]:
            del msg_dict["content"]
            
        return msg_dict