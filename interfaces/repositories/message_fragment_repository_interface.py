from abc import ABC, abstractmethod
from typing import List, Any

class IMessageFragmentRepository(ABC):
    @abstractmethod
    async def add_fragment(self, key: str, fragment: Any): ...
    
    @abstractmethod
    async def get_and_clear_fragments(self, key: str) -> List[str]: ...

    async def delete_queue(self, key: str): ...