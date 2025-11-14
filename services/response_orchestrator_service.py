#
# services/response_orchestrator_service.py (MODIFICADO)
#
import re
from utils.logger import logger
from container.agents import AgentContainer
from interfaces.clients.ia_interface import IAI
from interfaces.clients.chat_interface import IChat
from interfaces.agent.orchestrator_interface import IOrchestrator 
from services.message_generation_service import MessageGenerationService 
from openai.types.chat import ChatCompletion

class ResponseOrchestratorService(IOrchestrator):

    model: str = "gpt-4-turbo" 
    instructions: str = "" # (Mantido vazio, pois o system_prompt é usado)

    # (O system_prompt gigante permanece o mesmo)
    system_prompt: dict = {
        "role": "system",
        "content": """#1. Identidade... (etc)...""" 
    }
    tools: list = [] 

    def __init__(
        self,
        agent_container: AgentContainer,
        ai_client: IAI, 
        message_generation_service: MessageGenerationService
    ) -> None:
        self.agent_container = agent_container
        self.ai = ai_client
        self.message_generation_service = message_generation_service
        logger.info("ResponseOrchestratorService inicializado.")


    def _insert_system_input(self, input_list: list) -> list:
        # (Função permanece a mesma)
        if not any(msg.get("role") == "system" for msg in input_list):
            input_list.insert(0, self.system_prompt)
        return input_list

    def _extract_text_from_completion(self, response: ChatCompletion) -> str:
        # (Função permanece a mesma)
        try:
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except (AttributeError, IndexError, TypeError):
            logger.warning("Não foi possível extrair conteúdo da resposta da IA.")
            return ""

    async def _handle_agent(
        self, phone: str, context: list, agent_id: str
    ) -> list[dict]:
        # (Função permanece a mesma, apenas recebe o contexto limpo)
        agent = self.agent_container.get(agent_id)
        if not agent:
            logger.error(f"Agente '{agent_id}' não encontrado no container.")
            return [{"role": "assistant", "content": "Desculpe, ocorreu um erro interno (agente não encontrado)."}]
        
        logger.info(f"[Orchestrator] Acionando agente: {agent_id}")
        try:
            # O 'agent.exec' agora recebe o contexto original
            # e ele mesmo (via BaseAgent) inserirá seu próprio system_prompt
            agent_output_list = await agent.exec(context=context, phone=phone)
            return agent_output_list
        except Exception as e:
            logger.error(f"Erro ao executar agente '{agent_id}': {e}", exc_info=True)
            return [{"role": "assistant", "content": f"Desculpe, o {agent_id} encontrou um problema."}]


    async def execute(self, context: list, phone: str) -> list[dict]:
        # --- INÍCIO DA MUDANÇA ---
        
        # 1. Salva o contexto original e limpo
        original_context = context.copy()

        # 2. Prepara o contexto para o ROTEAMENTO (com o prompt do Orquestrador)
        routing_context = self._insert_system_input(original_context)
        
        # --- FIM DA MUDANÇA ---

        response_completion: ChatCompletion = await self.ai.create_model_response(
            model=self.model,
            input_messages=routing_context, # Usa o contexto de roteamento
            tools=self.tools,
            instructions=None 
        )

        logger.info(f"[Orchestrator] Resposta de roteamento da IA: {(response_completion)}")
        
        agent_id_to_call = self._extract_text_from_completion(response_completion)
        agent_id_to_call = re.sub(r"[^a-zA-Z0-9_]", "", agent_id_to_call)
        logger.info(f"[Orchestrator] Agente decidido pela IA: '{agent_id_to_call}'")

        full_output: list[dict] = []
        
        # Define o agente a ser usado (com fallback)
        if agent_id_to_call and self.agent_container.get(agent_id_to_call):
            chosen_agent_id = agent_id_to_call
        else:
            logger.warning(f"Roteamento falhou ou agente '{agent_id_to_call}' não existe. Usando 'agent_mentor' como fallback.")
            chosen_agent_id = "agent_mentor"

        # --- INÍCIO DA MUDANÇA ---

        # 3. Chama o agente passando o CONTEXTO ORIGINAL (limpo)
        agent_outputs: list[dict] = await self._handle_agent(
            phone=phone,
            context=context, # <--- MUDANÇA AQUI
            agent_id=chosen_agent_id,
        )
        full_output.extend(agent_outputs)
        
        # --- FIM DA MUDANÇA ---

        # (Restante da lógica de enviar mensagem permanece a mesma)
        final_response_message = next(
            (msg["content"] for msg in reversed(full_output) if msg["role"] == "assistant" and msg.get("content")),
            None
        )

        if final_response_message:
            await self.message_generation_service.send_message(phone, final_response_message)
            logger.info(f"[ResponseOrchetrator] Resposta enviada: {final_response_message[:50]}...")
        else:
            logger.error("[Orchestrator] Nenhuma resposta final gerada para o usuário.")

        return full_output