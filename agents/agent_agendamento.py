from container.repositories import RepositoryContainer
from interfaces.clients.ia_interface import IAI
from container.clients import ClientContainer
from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletion
from agents.agent_base import BaseAgent 
from utils.logger import logger
import json

from interfaces.clients.calendar_inteface import ICalendar 

#--------------------------------------------------------------------------------------------------------------------#
class AgentAgendamento(BaseAgent):
#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, ai_client: IAI, calendar_client: ICalendar): 
        self._ai_client = ai_client
        self._calendar_client = calendar_client 
        logger.info(f"[AgentAgendamento] Agente {self.id} inicializado com GCalendarClient.")

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def id(self) -> str:
        return "agent_agendamento"
    
#--------------------------------------------------------------------------------------------------------------------#

    @property
    def description(self) -> str:
        return "Especialista em gerenciamento de agenda, eventos, Google Calendar, marcação e consulta de reuniões (Calendar access)."

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def model(self) -> str:
        return "gpt-4.1-mini"

#--------------------------------------------------------------------------------------------------------------------#

    @property
    def instructions(self) -> str:
        return """
        # Identidade: Agente de Agendamento
        - **Função**: Gerenciador de Agenda (Google Calendar).
        - **Expertise**: Marcar, consultar, REMARCAR (update) e DELETAR eventos.

        # Contexto Atual
        - A data e hora atuais (Fuso São Paulo) são: {CURRENT_DATETIME}
        - Use esta data como referência para pedidos como "hoje", "amanhã" ou "próxima semana".
        
        # Regra de Segurança (Guardrail)
        - **IMPORTANTE**: Você NUNCA deve mostrar IDs de eventos ao usuário. IDs são apenas para uso interno das ferramentas.
        - **LIMITAÇÃO**: Você NÃO PODE convidar participantes (attendees).

        # --- INÍCIO DA CORREÇÃO ---
        - **Formato de Data (Usuário)**: Ao confirmar dados com o usuário, use um formato amigável (ex: "dia 15 de novembro, das 10h às 11h"). 
        - **Formato de Data (Ferramenta)**: Use o formato ISO (YYYY-MM-DDTHH:MM:SS-03:00) APENAS internamente para as chamadas de ferramenta.
        # --- FIM DA CORREÇÃO ---

        # Tarefa
        - Converta datas em linguagem natural (ex: "amanhã") para o formato ISO (YYYY-MM-DDTHH:MM:SS-03:00) usando a data atual como base.
        - Assuma o fuso horário de São Paulo (UTC-03:00).
        
        # Fluxo de Criação (create_calendar_event):
        1. Peça ao usuário: Título, Data/Hora de Início e Data/Hora de Fim. (NÃO peça e-mails).
        2. Confirme os detalhes com o usuário.
        3. Após a confirmação, chame a ferramenta `Calendar`. 
        4. Informe ao usuário que o evento foi criado.

        # Fluxo de Consulta (get_calendar_events):
        1. Use para verificar a agenda ou encontrar eventos.
        2. Se o usuário pedir para "remarcar" ou "deletar" um evento, use `get_calendar_events` PRIMEIRO para listar os eventos do dia e encontrar o ID (para seu uso interno).
        
        # Fluxo de Remarcar (update_calendar_event):
        1. (NUNCA use 'create_calendar_event' para remarcar!)
        2. Use `get_calendar_events` para encontrar o ID do evento que o usuário quer alterar.
        3. Confirme com o usuário (usando TÍTULO e HORA) qual evento será alterado.
        4. Peça QUAIS campos devem ser alterados (ex: novo título, novo horário de início, novo horário de fim).
        5. Construa o `update_body` (um JSON) contendo APENAS os campos que mudaram.
           - Se for o título: `{{"summary": "Novo Título"}}`
           - Se for o horário: `{{"start": {{"dateTime": "ISO_TIME_START"}}, "end": {{"dateTime": "ISO_TIME_END"}}}}`
           - Se for ambos: `{{"summary": "Novo Título", "start": ...}}`
        6. Chame `update_calendar_event` passando o ID e o `update_body`

        # Fluxo de Deleção (delete_calendar_event):
        1. Pergunte o dia/título do evento a ser deletado.
        2. Use `get_calendar_events` para listar os eventos do dia (e seus IDs, para seu uso interno).
        3. Confirme com o usuário (usando TÍTULO e HORA) o evento a ser deletado.
        4. Após a confirmação, chame `delete_calendar_event` com o ID (que você guardou).
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
                        if function_name == "get_calendar_events":
                            tool_output = await self._calendar_client.get_events(
                                start_date=function_args.get("start_date"),
                                end_date=function_args.get("end_date")
                            )
                            logger.info(f"[{self.id}] Ferramenta 'get_calendar_events' chamada.")
                        
                        elif function_name == "create_calendar_event":
                            tool_output = await self._calendar_client.create_event(
                                summary=function_args.get("summary"),
                                start_time=function_args.get("start_time"),
                                end_time=function_args.get("end_time")
                            )
                            logger.info(f"[{self.id}] Ferramenta 'create_calendar_event' chamada.")
                        
                        elif function_name == "update_calendar_event":
                            event_id = function_args.get("event_id")
                            update_body = function_args.get("update_body")
                            tool_output = await self._calendar_client.update_event(event_id, update_body)
                            logger.info(f"[{self.id}] Ferramenta 'update_calendar_event' chamada para ID: {event_id}")

                        elif function_name == "delete_calendar_event":
                            event_id = function_args.get("event_id")
                            tool_output = await self._calendar_client.delete_event(event_id)
                            logger.info(f"[{self.id}] Ferramenta 'delete_calendar_event' chamada para ID: {event_id}")
                            
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
                            "content": json.dumps(tool_output, default=str),
                        }
                    )
                
                logger.info(f"[{self.id}] Enviando resultados das ferramentas de volta para a IA.")
                response_completion: ChatCompletion = await self._ai_client.create_model_response(
                    model=self.model,
                    input_messages=messages,
                    tools=self.tools,
                )
                response_message = response_completion.choices[0].message
                messages.append(self._message_to_dict(response_message))
                
            final_content = response_message.content or "OK."
            logger.info(f"[{self.id}] Resposta final gerada: {final_content[:50]}...")
            return messages
            
        except Exception as e:
            logger.error(f"[{self.id}] Erro ao executar: {e}", exc_info=True)
            return messages + [{"role": "assistant", "content": "Desculpe, o Agente de Agendamento encontrou um problema."}]

#--------------------------------------------------------------------------------------------------------------------#

    @classmethod
    def factory(
        cls,
        client_container: ClientContainer,
        repository_container: RepositoryContainer,
    ) -> "AgentAgendamento":
        ai_client = client_container.get_client("IAI")
        if not ai_client:
            raise ValueError("Cliente IAI não encontrado no container.")
        calendar_client = client_container.get_client("ICalendar") 
        if not calendar_client:
            raise ValueError("[AgentAgendamento] Cliente ICalendar não encontrado no container.")
        return cls(ai_client=ai_client, calendar_client=calendar_client)
    
#--------------------------------------------------------------------------------------------------------------------#
tools_definitions = [
    {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Busca eventos na agenda do Google Calendar dentro de um período.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Data/hora de início (ISO 8601 com fuso, ex: 2025-11-15T00:00:00-03:00)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Data/hora de fim (ISO 8601 com fuso, ex: 2025-11-15T23:59:59-03:00)",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Cria um novo evento na agenda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "O título do evento."},
                    "start_time": {
                        "type": "string",
                        "description": "Data/hora de início (ISO 8601 com fuso, ex: 2025-11-16T10:00:00-03:00)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Data/hora de fim (ISO 8601 com fuso, ex: 2025-11-16T11:00:00-03:00)",
                    },
                },
                "required": ["summary", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "Atualiza (remarca ou renomeia) um evento existente usando seu ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string", 
                        "description": "O ID do evento a ser modificado (obtido via 'get_calendar_events')."
                    },
                    "update_body": {
                        "type": "object",
                        "description": "Um objeto JSON contendo APENAS os campos a serem alterados (ex: 'summary', 'start', 'end')."
                    }
                },
                "required": ["event_id", "update_body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "Deleta um evento existente usando seu ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string", 
                        "description": "O ID do evento a ser deletado (obtido via 'get_calendar_events')."
                    }
                },
                "required": ["event_id"],
            },
        },
    }
]