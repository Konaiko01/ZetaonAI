from abc import ABC, abstractmethod
from typing import Any, Optional


class ICalendar(ABC):
    
    @abstractmethod
    async def create_event(self, summary: str, start_time: str, end_time: str, attendees: list[str]) -> Optional[dict[str, Any]]:
        ...
    
    @abstractmethod
    async def get_events(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def get_event_by_id(self, id: str) -> Optional[dict[str, Any]]: 
        ...

    @abstractmethod
    async def update_event(self) -> bool: 
        ...

    @abstractmethod
    async def delete_events(self) -> bool: 
        ...