from abc import ABC, abstractmethod
from typing import List, Any, Optional

class IQueue(ABC):

    @abstractmethod
    async def push_to_queue(self, queue_key: str, message: Any) -> None:
        ...

    @abstractmethod
    async def pop_from_queue(self, queue_key: str) -> Optional[str]:
        ...

    @abstractmethod
    async def get_queue_fragments(self, queue_key: str) -> List[str]:
        ...

    @abstractmethod
    async def delete_queue(self, queue_key: str) -> None:
        ...
    
    @abstractmethod
    async def close(self) -> None:
        ...