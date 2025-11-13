from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IDB(ABC):
    
    @abstractmethod
    async def find_one(self, collection_key: str, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def insert_one(self, collection_key: str, data: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def update_one(self, collection_key: str, filter: Dict[str, Any], data: Dict[str, Any], upsert: bool = False) -> Any:
        ...