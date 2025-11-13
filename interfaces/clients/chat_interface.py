#Imports
from abc import ABC, abstractmethod


class IChat(ABC):

    @abstractmethod
    async def get_chat_id()-> str: ...

    @abstractmethod
    async def get_phone_number()-> str: ...

    @abstractmethod
    async def get_message()-> str: ...

    @abstractmethod
    async def is_valid()-> bool: ...

    @abstractmethod
    async def send_message()->bool: ...