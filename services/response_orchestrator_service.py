from utils.logger import logger
from container.agents import AgentContainer
from interfaces.clients.ia_interface import IAI
from interfaces.agent.orchestrator_interface import IOrchestrator 
from services.message_send_service import MessageSendService 
from openai.types.chat import ChatCompletion
from typing import Optional
import json
import re

#--------------------------------------------------------------------------------------------------------------------#
class ResponseOrchestratorService(IOrchestrator):
#--------------------------------------------------------------------------------------------------------------------#

    model: str = "gpt-4-turbo" 
    system_prompt: dict = {
        "role": "system",
        "content": """
#1. Identidade
- Você é o "Agente Organizador" (Orquestrador). Sua função é analisar a mensagem do usuário e decidir a próxima ação.

#2. Regras de Decisão
- **PRIORIDADE 1 (TAREFAS):** Se a mensagem for uma tarefa, pergunta, ou solicitação complexa, sua ÚNICA ação é chamar a ferramenta `route_to_agent` para encaminhar ao especialista.
- **PRIORIDADE 2 (TRIVIAL):** Se a mensagem for **trivial** (apenas saudações como "oi", "bom dia"; confirmações como "ok", "beleza"; ou agradecimentos como "obrigado", "vlw"), responda você mesmo com uma saudação ou confirmação curta (ex: "Olá!", "De nada!").
- **NUNCA** responda a uma tarefa complexa. Apenas roteie.

#3. Agentes para Roteamento (Ferramenta 'route_to_agent')
- **agent_mentor**: Fallback. Perguntas gerais, conselhos, conversas.
- **agent_conteudo**: Pesquisa web, notícias, escrever/resumir textos.
- **agent_agendamento**: Gerenciar/consultar agenda ou calendário.
- **agent_marketing**: Estratégias de negócios, vendas, anúncios, prospecção.
"""
    }

    @property
    def tools(self) -> list:
        return self._routing_tool_definition

#--------------------------------------------------------------------------------------------------------------------#

    def __init__(
        self,
        agent_container: AgentContainer,
        ai_client: IAI, 
        message_generation_service: MessageSendService
    ) -> None:
        self.agent_container = agent_container
        self.ai = ai_client
        self.message_generation_service = message_generation_service
        self.agent_ids = [agent.id for agent in self.agent_container.all()]
        if not self.agent_ids:
            raise ValueError("Nenhum agente foi registrado no AgentContainer.")
        self._routing_tool_definition = self._build_routing_tool(self.agent_ids)
        logger.info("ResponseOrchestratorService inicializado.")

#--------------------------------------------------------------------------------------------------------------------#

    def _build_routing_tool(self, agent_ids: list[str]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "route_to_agent",
                    "description": "Encaminha a solicitação do usuário para o agente especialista apropriado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "O ID do agente especialista que deve responder.",
                                "enum": agent_ids 
                            }
                        },
                        "required": ["agent_id"]
                    }
                }
            }
        ]
    
#--------------------------------------------------------------------------------------------------------------------#

    def _insert_system_input(self, input_list: list) -> list:
        if not any(msg.get("role") == "system" for msg in input_list):
            input_list.insert(0, self.system_prompt)
        return input_list
    
#--------------------------------------------------------------------------------------------------------------------#


    def _extract_agent_from_tool_call(self, response: ChatCompletion) -> Optional[str]:
        try:
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "route_to_agent":
                args = json.loads(tool_call.function.arguments)
                agent_id = args.get("agent_id")
                

                if agent_id in self.agent_ids:
                    return agent_id
            
            logger.warning(f"Chamada de ferramenta inesperada ou ID de agente inválido: {tool_call.function.name}")
            return None
            
        except (AttributeError, IndexError, TypeError, json.JSONDecodeError):
            logger.error("Falha ao extrair agent_id da chamada de ferramenta (tool_call).", exc_info=True)
            return None


#--------------------------------------------------------------------------------------------------------------------#

    async def _handle_agent(
        self, phone: str, context: list, agent_id: str
    ) -> list[dict]:
        agent = self.agent_container.get(agent_id)
        if not agent:
            logger.error(f"Agente '{agent_id}' não encontrado no container.")
            return [{"role": "assistant", "content": "Desculpe, ocorreu um erro interno (agente não encontrado)."}]
        
        logger.info(f"[Orchestrator] Acionando agente: {agent_id}")
        try:
            agent_output_list = await agent.exec(context=context, phone=phone)
            return agent_output_list
        except Exception as e:
            logger.error(f"Erro ao executar agente '{agent_id}': {e}", exc_info=True)
            return [{"role": "assistant", "content": f"Desculpe, o {agent_id} encontrou um problema."}]

#--------------------------------------------------------------------------------------------------------------------#
    async def execute(self, context: list, phone: str) -> list[dict]:
        original_context = context.copy()
        routing_context = self._insert_system_input(original_context)
        response_completion: ChatCompletion = await self.ai.create_model_response(
            model=self.model,
            input_messages=routing_context,
            tools=self.tools,
        )
        logger.info(f"[Orchestrator] Resposta da IA: {(response_completion)}")
        response_message = response_completion.choices[0].message 
        final_history = []
        if response_message.tool_calls:
            logger.info("[Orchestrator] Decisão: Roteamento para agente.")
            agent_id_to_call = self._extract_agent_from_tool_call(response_completion)
            chosen_agent_id = agent_id_to_call if agent_id_to_call else "agent_mentor"
            
            if not agent_id_to_call:
                 logger.warning(f"Roteamento (tool_call) falhou ou IA não escolheu. Usando 'agent_mentor' como fallback.")
            final_history = await self._handle_agent(
                phone=phone,
                context=context, 
                agent_id=chosen_agent_id,
            )
            
        elif response_message.content:
            logger.info(f"[Orchestrator] Decisão: Responder diretamente (Trivial): {response_message.content}")
            final_history = original_context + [{"role": "assistant", "content": response_message.content}]
        else:
            logger.warning("[Orchestrator] Resposta da IA estava vazia (sem tool_call e sem content). Usando 'agent_mentor'.")
            final_history = await self._handle_agent(
                phone=phone,
                context=context, 
                agent_id="agent_mentor",
            )
        final_response_message = next(
            (msg["content"] for msg in reversed(final_history) if msg["role"] == "assistant" and msg.get("content")),
            None
        )
        if final_response_message:
            await self.message_generation_service.send_message(phone, final_response_message)
            logger.info(f"[ResponseOrchetrator] Resposta enviada: {final_response_message[:50]}...")
        else:
            logger.error("[Orchestrator] Nenhuma resposta final gerada (nem trivial, nem agente).")
        return final_history