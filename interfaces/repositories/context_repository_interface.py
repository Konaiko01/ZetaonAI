from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IContextRepository(ABC):
    @abstractmethod
    async def get_context(self, phone: str) -> Optional[Dict[str, Any]]: ...
    
    @abstractmethod
    async def save_context(self, phone: str, context: Dict[str, Any]): ...