import logging
import json
from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from agents.agent_base import BaseAgent # <-- Importa a BaseAgent
from interfaces.clients.ia_interface import IAI
# from interfaces.clients.calendar_interface import ICalendar 
from container.clients import ClientContainer
from container.repositories import RepositoryContainer
from utils.logger import logger

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
                        "description": "Data e hora de início no formato ISO (YYYY-MM-DDTHH:MM:SS)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Data e hora de fim no formato ISO (YYYY-MM-DDTHH:MM:SS)",
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
            "description": "Cria um novo evento na agenda do Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "O título do evento."},
                    "start_time": {
                        "type": "string",
                        "description": "Data e hora de início no formato ISO (YYYY-MM-DDTHH:MM:SS)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Data e hora de fim no formato ISO (YYYY-MM-DDTHH:MM:SS)",
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de e-mails dos participantes.",
                    },
                },
                "required": ["summary", "start_time", "end_time"],
            },
        },
    },
]


class AgentAgendamento(BaseAgent):

    def __init__(self, ai_client: IAI, calendar_client: Any): # Substitua 'Any' pela sua ICalendar
        self._ai_client = ai_client
        self._calendar_client = calendar_client 
        logger.info(f"Agente {self.id} inicializado.")

    @property
    def id(self) -> str:
        return "agent_agendamento"
    
    @property
    def description(self) -> str:
        return "Especialista em gerenciamento de agenda, eventos, Google Calendar, marcação e consulta de reuniões (Calendar access)."

    @property
    def model(self) -> str:
        return "gpt-4.1-mini"

    @property
    def instructions(self) -> str:
        return """
        # Identidade: Agente de Agendamento
        - **Função**: Gerenciador de Agenda (Google Calendar).
        - **Expertise**: Marcar, consultar e gerenciar eventos e reuniões.
        - **Restrições**: Você SÓ pode realizar ações relacionadas à agenda.
        
        # Tarefa
        - Você deve usar as ferramentas `get_calendar_events` e `Calendar` para atender às solicitações do usuário.
        - Sempre confirme com o usuário ANTES de criar um evento, repetindo os detalhes (o quê, quando, quem).
        - Se os detalhes estiverem faltando (ex: falta a data final, ou o título), peça ao usuário as informações necessárias.
        - Ao consultar a agenda, forneça um resumo claro dos eventos encontrados.
        - Converta pedidos em linguagem natural (ex: "amanhã às 10h") para o formato ISO (ex: "2025-11-14T10:00:00") antes de chamar a ferramenta. Assuma o fuso horário local (-03:00).
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
            messages.append(self._message_to_dict(response_message)) # Adiciona a resposta da IA (seja texto ou tool_call)

            while response_message.tool_calls:
                logger.info(f"[{self.id}] Acionando ferramentas: {[tc.function.name for tc in response_message.tool_calls]}")

                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    tool_output = ""
                    try:
                        if function_name == "get_calendar_events":
                            # tool_output = await self._calendar_client.get_events(
                            #     start_date=function_args.get("start_date"),
                            #     end_date=function_args.get("end_date")
                            # )
                            tool_output = f"EVENTOS_SIMULADOS: 2 eventos encontrados entre {function_args.get('start_date')} e {function_args.get('end_date')}"
                            logger.info(f"[{self.id}] Ferramenta 'get_calendar_events' chamada.")

                        elif function_name == "create_calendar_event":
                            # tool_output = await self._calendar_client.create_event(
                            #     summary=function_args.get("summary"),
                            #     start_time=function_args.get("start_time"),
                            #     end_time=function_args.get("end_time"),
                            #     attendees=function_args.get("attendees", [])
                            # )
                            tool_output = f"EVENTO_CRIADO_SIMULADO: Evento '{function_args.get('summary')}' criado com sucesso."
                            logger.info(f"[{self.id}] Ferramenta 'create_calendar_event' chamada.")
                        
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

            final_content = response_message.content or "OK."
            logger.info(f"[{self.id}] Resposta final gerada: {final_content[:50]}...")
            return messages

        except Exception as e:
            logger.error(f"[{self.id}] Erro ao executar: {e}", exc_info=True)
            return messages + [{"role": "assistant", "content": "Desculpe, o Agente de Agendamento encontrou um problema."}]


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
            logger.warning("Cliente ICalendar não encontrado. O Agente de Agendamento usará MOCKS.")
            pass 

        return cls(ai_client=ai_client, calendar_client=calendar_client)