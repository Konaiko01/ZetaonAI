from openai.types.chat import ChatCompletion, ChatCompletionMessage
from interfaces.agent.agent_interface import IAgent
from utils.logger import logger
from utils.date import ZoneInfo
from abc import abstractmethod
from typing import Any
from datetime import datetime, timezone



#--------------------------------------------------------------------------------------------------------------------#
class BaseAgent(IAgent):
#--------------------------------------------------------------------------------------------------------------------#

    @property
    @abstractmethod
    def id(self) -> str: ...

#--------------------------------------------------------------------------------------------------------------------#

    @property
    @abstractmethod
    def description(self) -> str: ...

#--------------------------------------------------------------------------------------------------------------------#

    @property
    @abstractmethod
    def model(self) -> str: ...

#--------------------------------------------------------------------------------------------------------------------#

    @property
    @abstractmethod
    def instructions(self) -> str: ...

#--------------------------------------------------------------------------------------------------------------------#

    @property
    @abstractmethod
    def tools(self) -> list: ...

#--------------------------------------------------------------------------------------------------------------------#

    @abstractmethod
    async def exec(self, context: list[dict[str, Any]], phone: str) -> list[dict[str, Any]]: ...

#--------------------------------------------------------------------------------------------------------------------#

    def _insert_system_input(self, input_list: list) -> list:
        filtered_list = [msg for msg in input_list if msg.get("role") != "system"]
        try:
            sao_paulo_tz = ZoneInfo("America/Sao_Paulo")
            now = datetime.now(sao_paulo_tz)
            current_time_str = now.isoformat()
        except Exception as e:
            logger.warning(f"Falha ao obter fuso 'America/Sao_Paulo' ({e}). Usando UTC.")
            now = datetime.now(timezone.utc)
            current_time_str = now.isoformat() + " (UTC)"
        instructions_content = self.instructions.format(
            CURRENT_DATETIME=current_time_str
        )
        system_prompt = {"role": "system", "content": instructions_content}
        filtered_list.insert(0, system_prompt)
        return filtered_list

#--------------------------------------------------------------------------------------------------------------------#

    def _extract_text_from_completion(self, response: ChatCompletion) -> str:
        try:
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except (AttributeError, IndexError, TypeError):
            logger.warning(f"[{self.id}] Não foi possível extrair conteúdo de texto da resposta da IA.")
            return ""

#--------------------------------------------------------------------------------------------------------------------#

    def _message_to_dict(self, message: ChatCompletionMessage) -> dict[str, Any]:
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
        if not msg_dict["content"]:
            del msg_dict["content"]
            
        return msg_dict

