from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IAgent(ABC): 

    @property
    @abstractmethod
    def id(self)-> str: ...
    
    @property
    @abstractmethod
    def description(self)-> str: ...

    @property
    @abstractmethod
    def model(self)-> str:...

    @property
    @abstractmethod
    def instructions(self)-> str:...

    @abstractmethod
    def tools(self)-> Optional[List[Dict[str, Any]]]: ...

    @abstractmethod
    async def exec(self, context: List[Dict[str, Any]], phone: str) -> List[Dict[str, Any]]: ...