from abc import ABC, abstractmethod
from typing import Any

class IOrchestrator(ABC):
    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def tools(self) -> list: ...

    @property
    @abstractmethod
    def system_prompt(self) -> dict: ...

    @abstractmethod
    async def execute(self, context: list[dict[str, Any]], phone: str) -> list[dict[str, Any]]: ...