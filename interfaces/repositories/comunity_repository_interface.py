from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ICommunityRepository(ABC):
    @abstractmethod
    async def get_member(self, phone: str) -> Optional[Dict[str, Any]]: ...
    
    @abstractmethod
    async def add_member(self, member_data: Dict[str, Any]): ...