
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IQueue(ABC):

    @abstractmethod
    def add_message(self, key: str, payload: Dict[str, Any]) -> None: ...

    @abstractmethod
    def get_pending_messages(self, key: str) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_messages_batches(self) -> List[str]: ...

    @abstractmethod
    def delete(self, key: bytes | str) -> int: ...