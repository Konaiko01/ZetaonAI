import re
from utils.logger import logger
from container.agents import AgentContainer
from interfaces.clients.ia_interface import IAI
from interfaces.clients.chat_interface import IChat
from interfaces.agent.orchestrator_interface import IOrchestrator 
#from interfaces.repositories.message_repository_interface import IMessageRepository # 
from services.message_generation_service import MessageGenerationService 
from openai.types.chat import ChatCompletion

class ResponseOrchestratorService(IOrchestrator):

    model: str = "gpt-4-turbo" 
    instructions: str = "" 

    system_prompt: dict = {
        "role": "system",
        "content": """#1. Identidade
-**Nome**: Agente Organizador (Agent Manager)
-**Função**: Orquestrador de Agentes IA do projeto InsiderCluster.
-**Expertise**: Análise de Intenção, Classificação de Mensagens, Roteamento de Tarefas.
-**Estilo de Saída**: Apenas o NOME da função/agente a ser acionada. Sem explicações, sem saudações.

2. Contexto do Sistema

-**Missão**: Você é o "cérebro" central do "Container de Agentes".
-**Entrada**: Você receberá a mensagem mais recente do usuário e o histórico da conversa.
-**Tarefa**: Sua única tarefa é analisar a intenção da entrada e decidir qual agente especialista deve processá-la. Você NUNCA deve responder ao usuário diretamente.

3. Objetivo: Análise Inicial e Roteamento

-Seu objetivo é classificar a mensagem do usuário e determinar qual agente especialista é o mais adequado.

3.1 Agentes Especialistas (Destinos)

-agent_marketing: Especialista em marketing, vendas, growth, tráfego pago, prospecção e acesso a ferramentas externas (Full access).
-agent_conteudo: Especialista em criação de conteúdo, pesquisa, redação e acesso a ferramentas de busca (Web access).
-agent_agendamento: Especialista em gerenciamento de agenda, eventos, Google Calendar, marcação e consulta de reuniões (Calendar access).
-agent_mentor: Especialista em responder perguntas gerais, dar conselhos, mentorias e conversas que não exigem ferramentas externas (No external access).

3.2 Lógica de Decisão (Padrão de Análise)

-Analise a Intenção: Leia a mensagem do usuário.
-Verifique Agendamento: Se a mensagem for sobre "agenda", "calendário", "marcar", "reunião", "evento", "disponibilidade", acione: agent_agendamento.
-Verifique Conteúdo/Web: Se a mensagem for sobre "escreva", "pesquise", "crie um post", "me explique sobre [tópico]", "busque na web", acione: agent_conteudo.
-Verifique Marketing/Vendas: Se a mensagem for sobre "vendas", "anúncios", "Facebook Ads", "SDR", "BDR", "growth", "prospectar", acione: agent_marketing.
-Padrão (Mentor): Se a mensagem for uma pergunta geral, um pedido de conselho, uma saudação ("Oi", "Tudo bem?") ou qualquer coisa que não se encaixe claramente nas categorias acima, acione o agente padrão: agent_mentor.

4. Formato de Saída OBRIGATÓRIO

-Sua saída deve ser APENAS o nome do agente a ser acionado.
-Não inclua < ou >.
-Não inclua "A resposta é:".
-Não inclua nenhuma palavra além do nome do agente.

Exemplo 1:
Usuário: "Preciso marcar uma reunião com você para a próxima terça."
Sua Saída: agent_agendamento

Exemplo 2:
Usuário: "Me ajude a criar 5 ideias de post para o Instagram sobre IA."
Sua Saída: agent_conteudo

Exemplo 3:
Usuário: "Qual a melhor estratégia para prospectar clientes B2B?"
Sua Saída: agent_marketing

Exemplo 4:
Usuário: "Qual a sua opinião sobre o mercado de IA no Brasil?"
Sua Saída: agent_mentor""",
    }
    tools: list = [] 

    def __init__(
        self,
        agent_container: AgentContainer,
        #message_repository: IMessageRepository,
        ai_client: IAI, 
        message_generation_service: MessageGenerationService
    ) -> None:
        self.agent_container = agent_container
        #self.message_repository = message_repository
        self.ai = ai_client
        self.message_generation_service = message_generation_service
        logger.info("ResponseOrchestratorService inicializado.")


    def _insert_system_input(self, input_list: list) -> list:
        if not any(msg.get("role") == "system" for msg in input_list):
            input_list.insert(0, self.system_prompt)
        return input_list

    def _extract_text_from_completion(self, response: ChatCompletion) -> str:
        try:
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except (AttributeError, IndexError, TypeError):
            logger.warning("Não foi possível extrair conteúdo da resposta da IA.")
            return ""

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


    async def execute(self, context: list, phone: str) -> list[dict]:
        context = self._insert_system_input(context)

        response_completion: ChatCompletion = await self.ai.create_model_response(
            model=self.model,
            input_messages=context,
            tools=self.tools,
            instructions=None 
        )

        logger.info(f"[Orchestrator] Resposta de roteamento da IA: {(response_completion)}")
        
        agent_id_to_call = self._extract_text_from_completion(response_completion)
        agent_id_to_call = re.sub(r"[^a-zA-Z0-9_]", "", agent_id_to_call)
        logger.info(f"[Orchestrator] Agente decidido pela IA: '{agent_id_to_call}'")

        full_output: list[dict] = []

        if agent_id_to_call and self.agent_container.get(agent_id_to_call):
            agent_outputs: list[dict] = await self._handle_agent(
                phone=phone,
                context=context,
                agent_id=agent_id_to_call,
            )
            full_output.extend(agent_outputs)
        else:
            logger.warning(f"Roteamento falhou ou agente '{agent_id_to_call}' não existe. Usando 'agent_mentor' como fallback.")
            agent_outputs: list[dict] = await self._handle_agent(
                phone=phone,
                context=context,
                agent_id="agent_mentor", 
            )
            full_output.extend(agent_outputs)
        final_response_message = next(
            (msg["content"] for msg in reversed(full_output) if msg["role"] == "assistant" and msg.get("content")),
            None
        )

        if final_response_message:
            await self.message_generation_service.send_message(phone, final_response_message)
            logger.info(f"[ResponseOrchetrator]{final_response_message}")
        else:
            logger.error("[Orchestrator] Nenhuma resposta final gerada para o usuário.")

        return full_output