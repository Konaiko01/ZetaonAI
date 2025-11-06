#Imports
from abc import ABC, abstractmethod


class IChat(ABC):

    @abstractmethod
    def get_chat_id()-> str: ...

    @abstractmethod
    def get_phone_number()-> str: ...

    @abstractmethod
    def get_message()-> str: ...

    @abstractmethod
    def is_valid()-> bool: ...

    @abstractmethod
    def send_message()->bool: ...