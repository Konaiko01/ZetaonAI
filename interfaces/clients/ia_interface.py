from abc import ABC, abstractmethod

class IAI(ABC):
    
    @abstractmethod
    def transcribe_audio(self, audio_bytes: str) -> str: ...

    @abstractmethod
    async def create_model_response(
        self,
        model: str,
        context: list[dict],
        tools: list[dict] | None = None
    ) -> dict: ...

    '''@abstractmethod
    def function_call_output(
        function_call_id: str,
        call_id: str,
        call_name: str,
        output: str,
        arguments: dict,
        model: str,
    ): ...'''