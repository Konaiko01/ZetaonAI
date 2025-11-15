from abc import ABC, abstractmethod
from typing import Any

class IWebSearch(ABC):
    
    @abstractmethod
    async def search(self, query: str) -> str:...