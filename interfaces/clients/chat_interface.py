from abc import ABC, abstractmethod


class IChat(ABC):

    @abstractmethod
    def get_message(self, data) -> str: ...

    @abstractmethod
    def is_valid(self, message_data) -> bool: ...

    @abstractmethod
    def send_message(self, phone: str, output: str) -> bool: ...