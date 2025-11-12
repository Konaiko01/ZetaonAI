from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IOrchestrator(ABC):
    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def instructions(self) -> str: ...

    @property
    @abstractmethod
    def tools(self) -> list: ...

    @property
    @abstractmethod
    def system_prompt(self) -> dict: ...

    @abstractmethod
    async def execute(self, context: List[Dict[str, Any]], phone: str) -> List[Dict[str, Any]]: ...