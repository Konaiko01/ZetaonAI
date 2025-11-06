from abc import ABC, abstractmethod

class IAI(ABC):
    
    @abstractmethod
    def transcribe_audio(self, audio_bytes: str) -> str: ...

    @abstractmethod
    def create_model_response(
        self,
        model: str,
        input: str | list,
        tools: list = [],
        instructions: str | None = None,
    ): ...

    @abstractmethod
    def function_call_output(
        function_call_id: str,
        call_id: str,
        call_name: str,
        output: str,
        arguments: dict,
        model: str,
    ): ...